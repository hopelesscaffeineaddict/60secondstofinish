import os
import threading
from fuzzer import Fuzzer

## GLOBALS ##
BINARIES_DIR = "binaries"
INPUTS_DIR = "example_inputs"
OUTPUT_DIR = "fuzzer_output"


# shared condition to wakeup crash_worker when new crash is detected
condition = threading.Condition()
crashes = []
running = True

worker_threads = []

# worker thread that processes new crashes generated from the runner threads
def crash_worker(binary):
    global crashes, running

    out_file = os.path.join(OUTPUT_DIR, f"bad_{binary}.txt")

    while running:
        with condition:
            # if there is no available crash to analyse, sleep
            while not crashes and running:
                condition.wait()

            # if program has shut down, break out of loop
            if not running:
                break

            new_crash = crashes.pop(0)

        # TODO: process crash
        print(new_crash)

def fuzz(binary, example_input):
    crash_worker = threading.Thread(target=crash_worker, args=binary)
    crash_worker.start()

    worker_threads.append(crash_worker)

def main():
    global running

    print("Welcome to the 60secondstofinish Fuzzer!")

    # iterate over all binaries in the binary folder
    for binary in os.listdir(BINARIES_DIR):
        print(f"Starting fuzzing for {binary}")
        binary_path = os.path.join(BINARIES_DIR, binary)
        example_input = os.path.join(INPUTS_DIR, f"{binary}.txt")

        Fuzzer(binary_path, example_input)

    # TODO: just putting stub here to clean up nicely
    running = False
    with condition:
        condition.notify()

    # wait till all threads cleanup and return
    for thread in worker_threads:
        thread.join()

    print("Finished Fuzzing!")

if __name__ == '__main__':
    main()
