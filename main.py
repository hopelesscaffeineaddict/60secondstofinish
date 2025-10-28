import os
import sys
import subprocess
import threading
import multiprocessing as mp
import time
from format import format_type, FormatType
from mutator import Mutator
from runner import Runner
from inputs import parse_arguments, validate_arguments, match_binaries_to_inputs
from crashes import CrashHandler 

## GLOBALS ##
BINARIES_DIR = "binaries"
INPUTS_DIR = "example_inputs"
OUTPUT_DIR = "fuzzer_output"

runners = []

def main():
    global runners

    print("Welcome to the 60secondstofinish Fuzzer!")
    try:
        args = parse_arguments()

        if not validate_arguments(args):
            sys.exit(1)

        matches = match_binaries_to_inputs(args.binary, args.input)

        ctx = mp.get_context("forkserver")


        # delete later???? idk
        # gonna create basic mutator w sample input just to test first
        sample_input = b"test input"
        format = format_type(sample_input)
        max_mutations = args.mutations
        mutator = Mutator(sample_input, ctx, format)

        # iterate over all binaries in the binary folder
        for binary, input in matches:
            print(f"Starting fuzzing for {binary}")

            format = format_type(input)
            if format == FormatType.JSON:
                # TODO: create a JSON mutator
                print("JSON")
            elif format == FormatType.CSV:
                # TODO: create a CSV mutator
                print("CSV")
            else:
                print(f"Invalid format, skipping {binary}")
                continue

            # TODO: once mutators have been implemented, pass it in to this class instantiation
            new_runner = Runner(binary, None, ctx)
            new_runner.start()

            runners.append(new_runner)

        # stop each runner (finish all processes/threads)
        for runner in runners:
            runner.stop()

            # NOTE: if there's multiple threads/binary, similar to note in Runner, 
            # we might have to add some kinda feature that groups threads together based on binary
            # and outputs aggregate/avg stats for each group of threads.

            # get execution stats from Runner
            runner_stats = runner.stats
            total_executions = runner_stats['total_executions']

            # get crash stats and timing from CrashHandler 
            crash_stats = runner.crash_handler.get_statistics()
            total_time = crash_stats['total_time']

            # calculate executions per second to assess program speed
            executions_per_second = 0
            if total_time == 0:
                executions_per_second = total_executions / total_time
            
            # per-binary fuzzer statistics in terminal
            print(f"[*] Finished fuzzing for {os.path.basename(binary_path)}!")
            print(f"Total executions: {total_executions}")
            print(f"Crashes found: {crash_stats['crashes_found']}")
            print(f"Timeouts found: {crash_stats['timeouts_found']}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Executions per second: {executions_per_second:.2f}")

    except KeyboardInterrupt:
        print("\nFuzzing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error during fuzzing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
