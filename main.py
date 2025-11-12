import os
import threading
import sys
import multiprocessing as mp
import queue
import time
from format import get_format_from_bytes, FormatType
from inputs import parse_arguments, validate_arguments, match_binaries_to_inputs

from mutate.base import BaseMutator
from mutate.json_mutator import JSONMutator
from mutate.csv_mutator import CSVMutator
from mutate.xml_mutator import XMLMutator
from mutate.mutator import GenericMutator

from runner import Runner
from crashes import CrashHandler

## GLOBALS ##
BINARIES_DIR = "/binaries"
INPUTS_DIR = "/example_inputs"
OUTPUT_DIR = "/fuzzer_output"

runners = []

def binary_process(binary_path, input_path, fuzz_time = 60):
    # event to signal runner process to stop
    stop_event = threading.Event()
    # condition the crash handler waits on (when waiting for a crash to analayse)
    crash_condition = threading.Condition()
    # queue shared by mutator and runner to queue sample mutated inputs
    input_queue = queue.Queue(maxsize=500)

    # create mutator, crash handler and runner threads
    binary_name = os.path.basename(binary_path)
    crash_handler = CrashHandler(binary_path, crash_condition, stop_event)
    input_format = get_format_from_bytes(input_path)

    mutator = None
    max_queue_size = 200

    # if isinstance(mutator, CSVMutator):
    #     mutator.parse_csv_structure()

    if input_format == FormatType.JSON:
        print(f"[{binary_name}] Detected JSON format. Using JSONMutator.")
        mutator = JSONMutator(input_path, input_queue, stop_event, binary_name, max_queue_size)
    elif input_format == FormatType.CSV:
        print(f"[{binary_name}] Detected CSV format. Using CSVMutator.")
        mutator = CSVMutator(input_path, input_queue, stop_event, binary_name, max_queue_size)
    elif input_format == FormatType.XML:
        print(f"[{binary_name}] Detected XML format. Using XMLMutator.")
        mutator = XMLMutator(input_path, input_queue, stop_event, binary_name, max_queue_size)
    else:
        # fallback to generic mutator
        print(f"[{binary_name}] Using generic BaseMutator for format: {input_format.name}")
        mutator = BaseMutator(input_path, input_queue, stop_event, binary_name, max_queue_size)

    runner = Runner(binary_path, input_queue, crash_handler, stop_event, mutator)

    print(f"Starting fuzzing for {binary_path}")
    crash_handler.start()
    mutator.start()
    runner.start()

    start_time = time.time()
    try:
        # check for timeout or crash detection 
        while time.time() - start_time < fuzz_time and not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"Fuzzing interrupted by user for {binary_path}")
    finally:
        # clean up threads
        stop_event.set()
        print(f"Stopping fuzzing for {binary_path} after {fuzz_time}s")

    # clean up threads
    stop_event.set()

    runner.join(timeout=1)
    mutator.join(timeout=1)
    crash_handler.join(timeout=1)
    print(f"Finished fuzzing {binary_path}")

    # get execution stats from Runner
    runner_stats = runner.stats
    total_executions = runner_stats['total_executions']

    # get crash stats and timing from CrashHandler
    crash_stats = runner.crash_handler.get_statistics()
    total_time = crash_stats['total_time']

    # calculate executions per second to assess program speed
    executions_per_second = 0
    if total_time > 0:
        executions_per_second = total_executions / total_time

    # per-binary fuzzer statistics in terminal
    print(f"Total executions: {total_executions}")
    print(f"Crashes found: {crash_stats['crashes_found']}")
    print(f"Timeouts found: {crash_stats['timeouts_found']}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Executions per second: {executions_per_second:.2f}")

def main():
    global runners

    print("Welcome to the 60secondstofinish Fuzzer!")
    try:
        args = parse_arguments()

        if not validate_arguments(args):
            sys.exit(1)

        matches = match_binaries_to_inputs(args.binary, args.input)
        if not matches:
            print("No binary-to-input matches found. Exiting.")
            sys.exit(1)
            
        ctx = mp.get_context("spawn")

        # iterate over all binaries in the binary folder
        for binary, input in matches.items():
            # TODO: eventually create child classes of the parent Mutator and use that to distinguish
            # between format types

            with open(input, "rb") as input_file:
                input_data = input_file.read()

            # create new binary process
            proc = ctx.Process(target=binary_process, args=(binary, input_data, 60))
            proc.start()

            # UNCOMMENT: if you want to run binaries sequentially
            # runners.append(proc)

        # stop each runner (wait for processes/threads to complete safely)
        for runner in runners:
            runner.join()

            # # NOTE: if there's multiple threads/binary, similar to note in Runner,
            # # we might have to add some kinda feature that groups threads together based on binary
            # # and outputs aggregate/avg stats for each group of threads.
    except Exception as e:
        print(f"Error during fuzzing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
