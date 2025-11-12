#!/bin/bash

# Usage: ./run_fuzzer.sh <binary_dir> <input_dir>

echo "Deleting old files in fuzzer_output..."
rm -rf ~/60secondstofinish/fuzzer_output/*

echo "Deleting old mutation logs in mutated_inputs..."
rm -rf ~/60secondstofinish/mutated_inputs/*

echo "Running fuzzer using binary directory '$1' and example inputs directory '$2'..."
python3 main.py --binary="$1" --input="$2"
