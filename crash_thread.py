import os
import threading
import time
from pathlib import Path

OUTPUT_DIR = "fuzzer_output"

class CrashHandlerThread(threading.Thread):
    def __init__(self, binary, condition, stop_event):
        super().__init__(daemon=True)
        self.binary = Path(binary).name
        self.condition = condition
        self.stop_event = stop_event
        self.running = False
        self.crashes = []

        self.stats = {
            'crashes_found': 0,
            'timeouts_found': 0,
            'crash_types': {},
            'start_time': 0,
            'end_time': 0
        }

    def run(self):
        self.running = True
        self.stats['start_time'] = time.time()

        while self.running and not self.stop_event.is_set():
            with self.condition:
                # check to see if there is a new crash to analyse
                while not self.crashes and self.running:
                    # wait until a crash is queued (to avoid spin locking)
                    self.condition.wait(timeout=0.5)
                    if self.stop_event.is_set():
                        return

                if not self.running:
                    break

                new_crash = self.crashes.pop(0)

            # process new crash
            print(new_crash)
            result = new_crash["result"]
            crash_input = new_crash["input"]

            # track crash types
            if result.crashed:
                self.stats['crashes_found'] += 1

                crash_type_str = "unknown"

                if result.crash_type:
                    crash_type_str = result.crash_type.value

                if crash_type_str not in self.stats['crash_types']:
                    self.stats['crash_types'][crash_type_str] = 0
                self.stats['crash_types'][crash_type_str] += 1

            # save crash
            self.save_crash(result, crash_input)

            # For testing: stop after first crash
            self.running = False
            break

    def save_crash(self, result, crash_input):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary}.txt")
        with open(out_file, "ab") as f:
            f.write(crash_input)

        #  generate crash report
        report_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary_name}_report.txt")
        with open(report_file, "w") as f:
            f.write(f"Crash Report for {self.binary_name}\n")
            f.write(f"Crash Type: {result.crash_type.value if result.crash_type else 'Unknown'}\n")
            f.write(f"Return Code: {result.return_code}\n")
            f.write(f"Signal: {result.signal}\n")
            f.write(f"Execution Time: {result.execution_time:.4f} seconds\n\n")

            f.write("stderr output:\n")
            f.write(result.stderr.decode('utf-8', errors='ignore'))

            f.write("stdout output:\n")
            f.write(result.stdout.decode('utf-8', errors='ignore'))

            f.write("input data:\n")
            f.write(repr(crash_input[:1024]))
            if len(crash_input) > 1024:
                f.write(f"\n... ({len(crash_input) - 1024} more bytes)")

        print(f"Crash found for {self.binary_name}! Type: {result.crash_type.value if result.crash_type else 'Unknown'}")
        print(f"Saved crashing input to {out_file}")
        print(f"Detailed report saved to {report_file}")

        stderr_preview = result.stderr.decode('utf-8', errors='ignore')[:200]
        if stderr_preview:
            print(f"[+] stderr preview: {stderr_preview}...")

    # return current stats
    def get_statistics(self):
        self.stats['end_time'] = time.time()
        self.stats['total_time'] = self.stats['end_time'] - self.stats['start_time']

        return self.stats

