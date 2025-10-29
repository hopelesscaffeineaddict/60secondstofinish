import os
import argparse
from pathlib import Path

# TODO: Maybe this could be improved by adding other options (eg. either take in a directory or a file)

"""
Reads in arguments from the stdin stream in the format:
python main.py
"""
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="60secondstofinish: Black Box Fuzzer project for COMP6447"
    )

    parser.add_argument(
        "--binary", "-b", type=str, help = "Path to target directory containing binaries to fuzz"
    )

    parser.add_argument(
        "--input", "-i", type=str, help = "Path to target directory containing example inputs for binaries"
    )

    parser.add_argument(
        "--output", "-o", type=str, default="./fuzzer_output", help = "Path to output directory containing fuzzer results (default: /fuzzer_output)"
    )

    parser.add_argument(
        "--mutations", "-m", type=int, default=5000, help="Maximum number of mutations per binary (default: 5000)"
    )

    parser.add_argument(
        "--timeout", "-t", type=int, default=5, help="Timeout (seconds) for each execution (default: 5)"
    )

    parser.add_argument(
        "--threads", "-s", type=int, default=8, help="Number of parallel threads per binary (default: 8)"
    )

    return parser.parse_args()

# TODO: Complete function for validating CLI arguments (eg. check whether directory paths exist, check
# whether directory is empty, mismatched number of binaries to inputs, etc.)
""" Validate CLI arguments"""
def validate_arguments(args: argparse.Namespace) -> bool:
    # Check if binary directory exists
    if not os.path.isdir(args.binary):
        print(f"Error: Binary directory '{args.binary}' does not exist")
        return False

    # Check if input directory exists
    if not os.path.isdir(args.input):
        print(f"Error: Input directory '{args.input}' does not exist")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    # Check if binary directory is empty
    binary_files = find_files(args.binary)
    if not binary_files:
        print(f"Error: Binary directory '{args.binary}' is empty")
        return False

    # Check if input directory is empty
    input_files = find_files(args.input)
    if not input_files:
        print(f"Error: Input directory '{args.input}' is empty")
        return False

    # Check if mutations count is positive
    if args.mutations <= 0:
        print(f"Error: Number of mutations must be positive, got {args.mutations}")
        return False

    # Check if timeout is positive
    if args.timeout <= 0:
        print(f"Error: Timeout must be positive, got {args.timeout}")
        return False

    # Check if thread count is positive
    if args.threads <= 0:
        print(f"Error: Number of threads must be positive, got {args.threads}")
        return False

    return True

# Finds all files in the specified directory and returns it as a list of files
def find_files(directory: str) -> list[str]:
    files = []
    dir_path = Path(directory)

    for file_path in dir_path.iterdir():
        if file_path.is_file():
            files.append(str(file_path))

    return sorted(files)

"""
TODO: Add function which iterates over the files in binary_directory and example_input_directory
and matches them, returning it in a dict (?) (eg. csv1 -> csv1.txt)
"""
def match_binaries_to_inputs(binary_directory: str, input_directory:str) -> dict:
    binary_files = find_files(binary_directory)

    input_files = find_files(input_directory)

    matches = {}
    for binary_file in binary_files:
        binary_name = os.path.basename(binary_file)
        matching_input = None

        # check if binary is executable. if not, make it executable
        if not os.access(binary_name, os.X_OK):
            try:
                st = os.stat(binary)
                os.chmod(binary, st.st_mode | 0o111)
                print(f'Success: Made binary {binary_name} executable.')
            except Exception as e:
                print(f'Error: Failed to make binary {binary_name} executable: {e}. Skipping.')
                continue

        # Try exact match (eg. csv1 -> csv1.txt)
        for input_file in input_files:
            input_name = os.path.basename(input_file)

            if input_name == f"{binary_name}.txt" or input_name == binary_name:
                matching_input = input_file
                break

        # No exact match: attempt to find input file that begins with binary name
        if not matching_input:
            for input_file in input_files:
                input_name = os.path.basename(input_file)

                if input_name.startswith(binary_name):
                    matching_input = input_file
                    break

        if matching_input:
            matches[binary_file] = matching_input
        else:
            print(f"Error: No matching input file found for binary '{binary_name}'")

    return matches
