#!usr/bin/env python3

import sys
import os
import argparse
import subprocess
import signal
import random
from pathlib import Path


# TODO: Complete function using argparse library 
"""
Reads in arguments from the stdin stream in the format:
python main.py 
"""
def parse_arguments(arguments: str):
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
def validate_arguments(arguments: str):
    


"""
Finds all files in the specified directory and returns it as a list of files
"""
def find_files(directory: str) -> list[str]:
    files = []
    dir_path = Path(directory)

    for file_path in dir_path:
        if file_path.is_file():
            files.append(str(file_path))

    return sorted(files)

"""
TODO: Add function which iterates over the files in binary_directory and example_input_directory 
and matches them, returning it in a dict (?) (eg. csv1 -> csv1.txt)
"""
def match_binaries_to_inputs():
    return 


def main():
    try:
        input_data = parse_arguments()

    except KeyboardInterrupt:
        print("\nFuzzing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error during fuzzing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()