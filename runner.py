import os
import re
import threading
import subprocess
import queue
import time
import signal
from models import ExecutionResult, CrashType

# Password check stuff
password_keywords = [
    r'password', r'Password', r'Password required', r'Invalid password', r'Incorrect password', 
    r'Login', r'login', r'enter password', r'Enter password', r'authentication', r'Auth', r'auth'
]

password_pattern = re.compile('|'.join(password_keywords), re.IGNORECASE)

# Checks if program has a password check by matching stdout to list of password keywords
def check_if_password_prompt(stdout: str):
    if not stdout:
        return False

    if password_pattern.search(stdout):
        # print(f'[DEBUG] Password prompt detected: {password_pattern.search(stdout)}')
        return True 

    return False 

class Runner(threading.Thread):
    def __init__(self, binary_path, input_queue, crash_handler, stop_event, mutator, timeout=2.0):
        super().__init__(daemon=True)
        self.binary_path = binary_path
        self.input_queue = input_queue
        self.crash_handler = crash_handler
        self.stop_event = stop_event
        self.timeout = timeout
        self.stats = {"total_executions": 0}
        self.mutator = mutator
        self.password_detected = False 

    def run(self):
        # Run binary to detect password prompts and update mutator flag if password prompt detected 
        self.detect_password_prompt()

        if hasattr(self.mutator, 'set_password_protection'):
            self.mutator.set_password_protection(self.password_detected)

        while not self.stop_event.is_set():
            # attempt to retrieve a new mutated input from the shared input queue
            try:
                input_data = self.input_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self.stats["total_executions"] += 1
            result = self.execute_input(input_data)

            # log execution results
            self.mutator.log_execution(input_data, result)

            if result.crashed:
                # add the new crash results to the crash handler queue
                with self.crash_handler.condition:
                    self.crash_handler.crashes.append({"result": result, "input": input_data})
                    self.crash_handler.condition.notify()

    # run binary with OG input to detect password prompt
    def detect_password_prompt(self):
        try: 
            original_input = self.mutator.original_input

            proc = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            stdout, stderr = proc.communicate(input=original_input, timeout=self.timeout)
            stdout_str = stdout.decode('utf-8', errors='ignore')
            
            # Check for password keywords in stdout
            self.password_detected = check_if_password_prompt(stdout_str)
            
        except Exception as e:
            print(f"[DEBUG] Error detecting password prompt: {e}")

    def execute_input(self, input_data: bytes) -> ExecutionResult:
        start_time = time.time()
        try:
            # create subprocess for binary to run
            # tbh don't know if this is the correct args or not
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
                crash_info = self.analyse_crash(return_code, stderr, execution_time)

                stdout_str = stdout.decode("utf-8", errors="ignore")
                password_prompt = check_if_password_prompt(stdout_str)

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
    def analyse_crash(self, return_code: int, stderr: bytes, execution_time: float):
        # signal based crash detection
        if return_code < 0:
            signal_num = abs(return_code)
            crash_type = self.signal_to_crash_type(signal_num)
            if crash_type:
                return crash_type

        # better crash analysis w pattern matching from models.py
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
        stderr_str = stderr.decode("utf-8", errors="ignore")
        signal_match = re.search(r"signal \w+ \((\d+)\)", stderr_str)
        if signal_match:
            return int(signal_match.group(1))
        return None
