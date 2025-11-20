# Fuzzer Design and Functionality
60secondstofinish is a black box coverage guided fuzzer targeting binaries that accept both structured and semi-structured formats, namely CSV, JSON, ELF, JPEG, XML and plaintext. The system mutates example inputs and executes the target binary to detect crashes, hangs, and unexpected behaviour.

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

## Mutation Framework
All format-specific mutators inherit from `BaseMutator`, which manages mutation logging, handles stderr/stdout collection, stores the evolving input state , and supports chainable mutations, where each mutation builds on the previous one.

**CSV Mutation Strategies**
CSV and JSON input are treated as structured data with rows/fields and keys/arrays respectively. Mutations attempt to preserve protected header fields (if any), and break assumptions inside parsing logic. 

CSV input is treated as delimited structured text comprising rows and fields, and the fuzzer preserves 
1. Field Level Mutations 
	- Byte Insertion: Inserts random printable characters into existing fields to test bounds handling and find potential buffer overflow vulnerabilities
2. Row-Level Structural Mutations
	- Row Duplication/Insertion/Deletion: 

**JSON Mutation Strategies**
Relatively similar to CSV, just for key/array
**Plaintext Mutation Strategy**
1. Byte Mutations
2. Structural Mutations
3. Insertion Mutations 


- CSV
- ELF
- Plaintext
- XML
	- Structural mutations:
		- Adding a random number of child nodes to the main root node
		- Recursively adding children nodes from a starting node
		- Deleting a random node from the tree
	- href mutations
		- Changing link contents to be a random choice of special string inputs
	- Content mutations
		- Changing the contents of a node to be a random choice of special string inputs
- JPEG (eugenia/arhaan)
- ELF:
	- Header mutations (structural). Mutates fields inside the ELF header like e_phoff, e_phnum, e_ehsize, and e_phentsize.
	- Byte mutations:
		- replace random bytes with boundary values
		- flip bits/nibbles randomly
	- block mutations.
		- insert/delete a block of bytes of random size anywhere in the elf body, preserving the first 0x40 bytes (elf header + safezone)

### How Harness Works (sara)

## Bugs we could find 
- Out of bounds read/write (eg. plaintext2)
- Format string vulnerabilities (eg. xml1/2? unsure.)
- Buffer overflows (eg. json1/csv1)
- plaintext3?? 
- 

## Fuzzer Improvements
**Process Resource Monitoring**
We could implement continuous tracking of peak RSS memory, as well as total CPU time, thread count, and file descriptors and handles open/used so as to detect memory leaks, CPU spikes or infinite loops/hangs, as well as resource exhaustion.

This would be implemented using 

**More advanced ELF Mutation Strategies**
Currently, our ELF mutation strategies comprise random insertion/deletion of a block of bytes in the ELF body. This does not utilise ELF loader logic. As such, future ELF mutation strategies could be aware of the ELF file format, including the program header table (PHT) 

**PDF Mutation Strategies**
Introducing format specific mutation strategies for PDF inputs, which would entail:
1. Structural parsing of PDF objects via `xref`, `obj`, streams, and dictionary keys 
2. Mutation targets include broken `xref` offsets, oversized object lengths, malformed dictionaries, as well as uncompressed and compressed stream corruption
This would require partial parsing to enable structurally aware mutations instead of random byte edits to ensure the input remains valid.

**Smarter Mutations based off of coverage feedback** (please confirm)
- implemented coverage 
