import os
import time

from models import ExecutionResult, CrashType
from typing import Optional

OUTPUT_DIR = "fuzzer_output"

# worker thread class that processes new crashes generated from its corresponding runner
class CrashHandler():
    def __init__(self, binary, condition):
        self.binary = binary
        self.condition = condition
        self.running = False
        self.crashes = []

        # For tracking statistics
        self.stats = {
            'crashes_found': 0,
            'timeouts_found': 0,
            'crash_types': {},
            'start_time': 0,
            'end_time': 0
        }

    def start(self):
        out_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary}.txt")
        self.running = True
        self.stats['start_time'] = time.time()

        while self.running:
            with self.condition:
                # if there is no available crash to analyse, sleep
                while not self.crashes and self.running:
                    self.condition.wait()

                # if program has shut down, break out of loop
                if not self.running:
                    break

                new_crash = self.crashes.pop(0)

            # process crash
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

            # signal runner to stop after saving first crash
            break

    # save crash output
    def save_crash(self, result: ExecutionResult, crash_input: bytes):
        out_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary_name}.txt")
        
        # save crashing input to file
        with open(out_file, "wb") as f:
            f.write(crash_input)
        
        #  generate crash report
        report_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary_name}.report")
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