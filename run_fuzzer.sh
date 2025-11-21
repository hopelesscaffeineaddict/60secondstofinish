#!/bin/bash

# Ensure the binaries folder exists.
if [ ! -d "binaries" ]; then
    echo "Error: No folder named binaries exists in CWD."
    exit 1
fi
# Ensure the example_inputs folder exists.
if [ ! -d "example_inputs" ]; then
    echo "Error: No folder named example_inputs exists in CWD."
    exit 1
fi

# Make a folder for fuzzer_output
if [ ! -d "fuzzer_output" ]; then
    echo "Creating fuzzer_output folder"
    mkdir fuzzer_output
fi

# Ensure the harness exists
if [ ! -f "harness.c" ]; then
    echo "Error: No file names harness.c exists in CWD."
    exit 1
fi

# Compile the c harness
echo "Compiling harness.c."
gcc harness.c -o harness
if [ $? -ne 0 ]; then
    echo "Error: Failed to compile harness.c"
    exit 1
fi

coverage=0
for arg in "$@"; do
    case "$arg" in
        -c|--coverage)
            coverage=1
            ;;
    esac
done

echo "Deleting old fuzzer output files."
rm 'fuzzer_output/*' 2>/dev/null

echo "Docker container building..."
docker build -t fuzzer-image .
if [ $? -ne 0 ]; then
    echo "Error: Failed to build docker container"
    exit 1
fi
echo "Docker container built successfully"

# Run the image, mounting /binaries as read-only and /fuzzer_output
echo "Running Fuzzer"
docker run \
    -v "$(pwd)":/app \
    -w /app \
    fuzzer-image \
    $( [ $coverage -eq 1 ] && echo "--coverage" )
