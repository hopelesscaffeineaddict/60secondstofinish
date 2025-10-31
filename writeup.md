# Fuzzer Design and Functionality

The **60secondstofinish** fuzzer is designed to discover vulnerabilities in binary executables through randomised input mutation and controlled execution. 

Given a directory containing multiple binaries, the system spawns a new fuzzing process for each binary. Each of these binary processes run **three main threads**:
* Mutator thread
* Runner thread
* Crash handler thread

These threads operate concurrently to maximise efficiency and ensure input generation, execution, and crash analysis proceed in parallel.

## Mutator:
The mutator thread is responsible for generating test inputs.

This is done by randomly applying a diverse set of mutation strategies on a valid example input for the target binary. Once generated, these test inputs are enqueued into a shared “input queue”, which is then used by the runner thread.

The fuzzer's mutation framework is built around an abstract BaseMutator class, and subclass (ie. CSVMutator, JSONMutator, GenericMutator) defines its own mutation strategies while reusing the threading and logging logic from the base.

Mutations are chainable, and each mutate() call can apply multiply mutations sequentially on the current input state.

Below outlines some of our currently implemented mutation strategies:
**Generic Strategies**
- Bit flips, splicing and random byte insertion/deletion on raw input data. Acts as a fallback or when structured parsing in other format specific mutators fail

**Format Specific Strategies**
CSVMutator: It contains two mutation layers, namely field level and row level, which is randomly chosen
- Field level mutations: A random choice of random character insertion/content duplication
- Row level mutations: A random choice of row insertion/deletion/duplication

JSONMutator: Strategies include mutating numeric/boolean values, type substitution, adding/removing key value pairs, as well as modifying array structures or inserting nested JSON objects.

## Runner:
The runner thread serves as the main execution harness for the target binary.

It repeatedly fetches mutated inputs from the queue and executes the binary using these inputs.

During execution, the runner detects any non-expected termination signals or hanging program states, to detect if a binary has crashed. In the case of a crash, the runner captures the respective crash data and queues it in a shared “crash queue”.

This harness thread isolation ensures each execution of the binary is sandboxed and recoverable. If the target binary hangs or crashes, the runner can terminate and restart cleanly without affecting the rest of our fuzzer processes.

## Crash Handler
The crash handler thread dequeues entries from the crashes queue.

It is responsible for persisting the crash data into a binary crash output file (which can be used for later analysis). In particular, two crash files are written:

1. **/fuzzer_output/bad_{binary_name}.txt**\
    This file saves the input that was used to crash the binary
2. **/fuzzer_output/{binary_name}_crashreport.txt**\
    This saves the execution state of the program upon the crash (execution time, returned status code, stdout, stderr, crash type, etc.)

This thread runs independently to ensure that writing results to files does not block or bottleneck ongoing fuzzing processing.

