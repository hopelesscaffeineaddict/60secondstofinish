import os
import threading
import time
from pathlib import Path

OUTPUT_DIR = "./fuzzer_output"

class CrashHandler(threading.Thread):
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

            # stop fuzzing after first crash
            self.stop_event.set()
            self.running = False
            break

    def save_crash(self, result, crash_input):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary}.txt")
        with open(out_file, "ab") as f:
            f.write(crash_input)

        # print crash report
        print(f"\n[SUCCESS] Crash found for {self.binary}!")
        print(f'    * Crash Type: {result.crash_type.value if result.crash_type else "Unknown"}')
        print(f'    * Return Code: {result.return_code}')
        print(f'    * Execution Time: {result.execution_time:.4f} seconds')
        print(f'    * Coverage Offsets: {result.coverage}')
        print(f'    * Stdout: {result.stdout}')
        print(f'    * Stderr: {result.stderr}')
        print(f"[CRASH INPUT SAVED] Saved crashing input to {out_file}\n")

    # return current stats
    def get_statistics(self):
        self.stats['end_time'] = time.time()
        self.stats['total_time'] = self.stats['end_time'] - self.stats['start_time']

        return self.stats

