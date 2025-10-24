import os

OUTPUT_DIR = "fuzzer_output"

# worker thread class that processes new crashes generated from its corresponding runner
class CrashHandler():
    def __init__(self, binary, condition):
        self.binary = binary
        self.condition = condition
        self.running = False
        self.crashes = []

    def start(self):
        out_file = os.path.join(OUTPUT_DIR, f"bad_{self.binary}.txt")
        self.running = True

        while self.running:
            with self.condition:
                # if there is no available crash to analyse, sleep
                while not self.crashes and self.running:
                    self.condition.wait()

                # if program has shut down, break out of loop
                if not self.running:
                    break

                new_crash = self.crashes.pop(0)

            # TODO: process crash
            print(new_crash)
