import os
import re
import threading
import subprocess
import queue
import time
import signal
from models import ExecutionResult, CrashType

class Runner(threading.Thread):
    def __init__(self, binary_path, input_queue, crash_handler, stop_event, mutator, coverage, timeout=2.0):
        super().__init__(daemon=True)
        self.binary_path = binary_path
        self.input_queue = input_queue
        self.crash_handler = crash_handler
        self.stop_event = stop_event
        self.timeout = timeout
        self.stats = {"total_executions": 0}
        self.mutator = mutator
        self.coverage = coverage
        self.total_coverage = set()

    def run(self):
        while not self.stop_event.is_set():
            # attempt to retrieve a new mutated input from the shared input queue
            try:
                input_data = self.input_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if self.coverage:
                result = self.execute_input_with_coverage(input_data)
            else:
                result = self.execute_input(input_data)
            self.stats["total_executions"] += 1

            if result.crashed:
                # add the new crash results to the crash handler queue
                with self.crash_handler.condition:
                    self.crash_handler.crashes.append({"result": result, "input": input_data})
                    self.crash_handler.condition.notify()

    def execute_input_with_coverage(self, input_data: bytes) -> ExecutionResult:
        start_time = time.time()
        harness = './harness'

        try:
            # create subprocess for the c harness to run and detect coverage
            proc = subprocess.Popen(
                [harness, str(self.timeout), self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # give the harness extra time to run (as ptrace is quite slow)
            try:
                stdout, stderr = proc.communicate(input=input_data, timeout=self.timeout + 1)
            except subprocess.TimeoutExpired:
                # c harness timeout (something went wrong in harness not binary)
                proc.kill()
                return ExecutionResult(
                    return_code = -2,
                    stdout = stdout,
                    stderr = stderr,
                    execution_time = time.time() - start_time,
                    crashed = False,
                    crash_type = CrashType.HARNESS_ERR,
                    signal = None,
                )

            execution_time = time.time() - start_time
            return_code = proc.returncode
            return self.parse_harness_results(return_code, stdout, stderr, execution_time)
        except Exception as e:
            return ExecutionResult(
                return_code = -2,
                stdout = stdout,
                stderr = stderr,
                execution_time = time.time() - start_time,
                crashed = False,
                crash_type = CrashType.HARNESS_ERR,
                signal = None,
            )

    def parse_harness_results(self, return_code: int, stdout: bytes, stderr: bytes, execution_time: float):
        # check if there was an error with the actual harness
        if return_code != 0:
            return ExecutionResult(
                return_code, '', '', execution_time, False, None, None, None
            )

        # extract the binary output as returned by the c harness
        binary_output = stdout.decode("utf-8", errors="ignore")
        if '|STDERR:' in binary_output:
            parts = binary_output.split('|STDERR:')
            stdout_str = parts[0]
            stderr_str = parts[1]
        else:
            stdout_str = binary_output
            stderr_str = ''

        results_data = stderr.decode("utf-8", errors="ignore").strip() if stderr else ''
        harness_result = {}

        if results_data:
            try:
                # parse all the binary run details from the harness
                for result in results_data.split('|'):
                    key, value = result.split(':', 1)
                    if key.strip() in harness_result:
                        harness_result[key.strip()] += value.strip()
                    else:
                        harness_result[key.strip()] = value.strip()

            except ValueError:
                return ExecutionResult(
                    signal, stdout_str, stderr_str,
                    execution_time, False, None, None, coverage
                )

            crashed = False
            crash_type = harness_result.get('CRASH_TYPE', '')
            signal = int(harness_result.get('SIGNAL', 0))

            coverage_str = harness_result.get("COVERAGE", '')
            coverage = {hex((int(c, 16) << 4)) for c in coverage_str.split(',') if c} if coverage_str else None
            if coverage:
                new_symbols = coverage - self.total_coverage
                if new_symbols:
                    print(f'[{os.path.basename(self.binary_path)}] New coverage found! {len(new_symbols)} new symbols explored.')
                    print(f'[+] new offsets = {new_symbols}')
                    self.total_coverage.update(new_symbols)

            found_crash_type = None
            if crash_type == 'none':
                return ExecutionResult(
                    signal, stdout_str, stderr_str,
                    execution_time, False, None, None, coverage
                )
            elif crash_type == 'timeout':
                crashed = True
                found_crash_type = CrashType.TIMEOUT
            elif crash_type == 'crash':
                crashed = True
                found_crash_type = self.analyse_crash(signal, stderr)

            return ExecutionResult(
                    signal, stdout_str, stderr_str,
                    execution_time, crashed, found_crash_type,
                    self.extract_signal_from_stderr(stderr), coverage
                )

    def execute_input(self, input_data: bytes) -> ExecutionResult:
        start_time = time.time()
        try:
            # create subprocess for binary to run
            proc = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # so we can kill process group on timeout
            )

            try:
                stdout, stderr = proc.communicate(input=input_data, timeout=self.timeout)
                execution_time = time.time() - start_time
                return_code = proc.returncode
                crash_info = self.analyse_crash(return_code, stderr)
                return ExecutionResult(
                    return_code = return_code,
                    stdout = stdout,
                    stderr = stderr,
                    execution_time = execution_time,
                    crashed = crash_info is not None,
                    crash_type = crash_info if crash_info else None,
                    signal = self.extract_signal_from_stderr(stderr),
                )
            # error handling for timeout
            except subprocess.TimeoutExpired:
                # kill process group
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
                proc.wait()
                return ExecutionResult(
                    return_code = -1,
                    stdout = b"",
                    stderr = b"Timeout",
                    execution_time = time.time() - start_time,
                    crashed = True,
                    crash_type = CrashType.TIMEOUT,
                    signal = None,
                )
        except Exception as e:
            return ExecutionResult(
                return_code = -2,
                stdout = b"",
                stderr = str(e).encode(),
                execution_time = time.time() - start_time,
                crashed = False,
                crash_type = None,
                signal = None,
            )

    # analyse execution results to determine if a crash occurred
    def analyse_crash(self, return_code: int, stderr: bytes):
        # check for known patterns to detect type of crash
        stderr_str = stderr.decode("utf-8", errors="ignore").lower()
        crash_patterns = {
            "stack smashing": CrashType.STACKSMASH,
            "segmentation fault": CrashType.SEGFAULT,
            "segfault": CrashType.SEGFAULT,
            "abort": CrashType.ABORT,
            "assertion": CrashType.ABORT,
            "buffer overflow": CrashType.BUFFER_OVERFLOW,
            "stack overflow": CrashType.BUFFER_OVERFLOW,
            "heap overflow": CrashType.BUFFER_OVERFLOW,
            "use after free": CrashType.USE_AFTER_FREE,
            "double free": CrashType.DOUBLE_FREE,
            "invalid read": CrashType.INVALID_READ,
            "invalid write": CrashType.INVALID_WRITE
        }
        for pattern, crash_type in crash_patterns.items():
            if pattern in stderr_str:
                return crash_type

        # signal based crash detection
        signal_num = abs(return_code)
        crash_type = self.signal_to_crash_type(signal_num)
        if crash_type:
            return crash_type

        return None

    # convert signal no. to crash type
    def signal_to_crash_type(self, signal_num: int):
        signal_map = {
            signal.SIGSEGV: CrashType.SEGFAULT,
            signal.SIGABRT: CrashType.ABORT,
            signal.SIGBUS: CrashType.INVALID_READ,
            signal.SIGFPE: CrashType.INVALID_READ,
        }
        return signal_map.get(signal_num)

    # extract signal number from stderr output
    def extract_signal_from_stderr(self, stderr: bytes):
        if not stderr:
            return None

        stderr_str = stderr.decode("utf-8", errors="ignore")
        signal_match = re.search(r"signal \w+ \((\d+)\)", stderr_str)
        if signal_match:
            return int(signal_match.group(1))
        return None
