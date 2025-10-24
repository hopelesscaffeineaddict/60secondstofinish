import os
import subprocess
import threading
import multiprocessing as mp
from format import format_type, JSON, CSV
from runner import Runner

## GLOBALS ##
BINARIES_DIR = "binaries"
INPUTS_DIR = "example_inputs"
OUTPUT_DIR = "fuzzer_output"

# shared condition to wakeup crash_worker when new crash is detected
runners = []

def main():
    global runners

    print("Welcome to the 60secondstofinish Fuzzer!")

    ctx = mp.get_context("forkserver")

    # iterate over all binaries in the binary folder
    for binary in os.listdir(BINARIES_DIR):
        print(f"Starting fuzzing for {binary}")
        binary_path = os.path.join(BINARIES_DIR, binary)
        example_input = os.path.join(INPUTS_DIR, f"{binary}.txt")

        format = format_type(example_input)
        if format == JSON:
            # TODO: create a JSON mutator
            print("JSON")
        elif format == CSV:
            # TODO: create a CSV mutator
            print("CSV")
        else:
            print(f"Invalid format, skipping {binary}")
            continue

        # TODO: once mutators have been implemented, pass it in to this class instantiation
        new_runner = Runner(binary_path, None, ctx)
        new_runner.start()

        runners.append(new_runner)

    # stop each runner (finish all processes/threads)
    for runner in runners:
        runner.stop()

    print("Finished Fuzzing!")

if __name__ == '__main__':
    main()
