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

## JPEG

JPEG file is a sequence of segments and each segment begins with a marker that is always 2 bytes starting with 0xFF. The second byte identifies the type of marker. A JPEG has the following sections:
1. Start of Image            (FF D8)
2. APP0 (Application specfic)(FF E0)
3. Define Quantization Table (FF DB)
4. Start of Frame            (FF C0)
5. Define Huffman Table      (FF C4)
6. Start of Scan (Image Data)(FF DA)
7. End of Image              (FF D9)

The most important ones are the start of image. 
Ways to potentially exploit:

1. Remove start marker or add another (the FF D8 marker)
2. APP0: Change length to FF FF or 00 02 (might cause reading past buffer)
3. DQT: mismatch the length with the actual data size. Like make length 00 20 but still provide 64 bytes of data
4. SOF0 (MOST IMPORTANT ONE): corrupt the length/width. Change it to FF FF or 00 00 and cause a malloc issue. Change component from 03 to FF (malloc would be 65535 x 65535 x 3) or something. 
5. DFT: change the length
6. SOS: Change the components to mismatch and be different than SOF0. 
7. EOI: Put FF D9 in the middle of it instead of end or Remove it. Might cause reading past buffer

