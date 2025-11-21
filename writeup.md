# Fuzzer Design and Functionality
60secondstofinish is a black box coverage guided fuzzer targeting binaries that accept both structured and semi-structured formats, namely CSV, JSON, ELF, JPEG, XML and plaintext. The system mutates example inputs and executes the target binary to detect crashes, hangs, and unexpected behaviour.

Given a directory containing multiple binaries, the system spawns a new fuzzing process for each binary. Each of these binary processes run **three main threads**:
* Mutator thread
* Runner thread
* Crash handler thread

These threads operate concurrently to maximise efficiency and ensure input generation, execution, and crash analysis proceed in parallel.

## Runner:
The runner thread serves as the main execution harness for the target binary.

It repeatedly fetches mutated inputs from the queue and executes the binary using these inputs.

During execution, the runner detects any non-expected termination signals or hanging program states, to detect if a binary has crashed. In the case of a crash, the runner captures the respective crash data and queues it in a shared “crash queue”.

This harness thread isolation ensures each execution of the binary is sandboxed and recoverable. If the target binary hangs or crashes, the runner can terminate and restart cleanly without affecting the rest of our fuzzer processes.

## Crash Handler
The crash handler thread dequeues entries from the crashes queue.

It is responsible for persisting the crash data into a binary crash output file (which can be used for later analysis). In particular:
1. **/fuzzer_output/bad_{binary_name}.txt**\
    This file saves the input that was used to crash the binary

This thread runs independently to ensure that writing results to files does not block or bottleneck ongoing fuzzing processing.

## Mutation Framework
The mutator thread is responsible for generating test inputs.

This is done by randomly applying a diverse set of mutation strategies on a valid example input for the target binary. Once generated, these test inputs are enqueued into a shared “input queue”, which is then used by the runner thread.

All format-specific mutators inherit from `BaseMutator`, which manages mutation logging, handles stderr/stdout collection, stores the evolving input state , and supports chainable mutations, where each mutation builds on the previous one.

**CSV Mutation Strategies**
1. Field-level mutations: Insertion/deletion of random printable characters into fields to test for lack of bounds checking
2. Row-level structural mutations: Insert/duplicate/delete rows 
3. Header Handling: Avoids modifying the header row if header protection is detected

**JSON Mutation Strategies**
1. Value Mutations: Changes scalar fields by inserting characters/flipping vallues/modifying numbers, and substitues values with known edge case integers (eg. -1, 32 bit boundaries)
2. Type Substitution: Replaces values with a different JSON type (eg. int to string, null, list, nested object)
3. Structural Mutations: Inserts/deletes/duplicates key-value pairs, and modifies arrays by inserting/removing/duplicating elements 
4. Nested Structure Mutations: Injects nested JSON objects/dictionaries into existing structures 
5. Boundary Value Mutations: Overwrites fields that likely contain sizes/counts with extreme/boundary integers 

**Plaintext Mutation Strategy**
Mutations may apply globally to the full input, or per-line when the input is newline-separated. Supports sequential chaining of mutation rounds to build cumulative corruption

1. Byte-Level Mutations: Random bit flips (single bit/full byte NOT), replacement with random byte values, insertion of special bytes (NULL/newline/UTF-8 BOM, control bytes)
2. Structural Mutations: Random character/byte deletion, splicing (extraction of a random byte range and reinsertion elsewhere), byte swapping.
3. Insertion Mutations: Insertion of large byte blobs, integer edge values, random ASCII strings, and boundary value blobs

**XML Mutation Strategies**
1. Structural mutations:
    - Adding a random number of child nodes to the main root node
    - Recursively adding children nodes from a starting node
    - Deleting a random node from the tree
2. href mutations
    - Changing link contents to be a random choice of special string inputs
3. Content mutations
    - Changing the contents of a node to be a random choice of special string inputs

**JPEG Mutation Strategies**
1. SOI (Start of Image) Mutations
   * Modify the `FF D8` signature to break initial JPEG parsing
   * Relocate the SOI marker to a different offset in the file
2. **APP0 (JFIF) Mutations
   * Corrupt segment length to trigger size misinterpretation
   * Modify identifier, version, or density fields with boundary or random values
3. DQT (Quantization Table) Mutations
   * Change declared segment length to mismatch the encoded data size
   * Modify precision or quantization entries to disrupt decoder assumptions
4. SOF (Start of Frame) Mutations
   * Overwrite height, width, or length fields with extreme integers
   * Modify component counts (e.g., 3 → `FF`) to trigger excessive allocation or read overflow
5. DHT (Huffman Table) Mutations
   * Corrupt segment length, class identifiers, symbol lengths, or value fields
   * Introduce malformed Huffman metadata to break decoding logic
6. EOI (End of Image) Mutations
   * Move the `FF D9` marker earlier to force early termination
   * Remove or corrupt EOI to cause out‑of‑bounds or unterminated parsing

**ELF Mutation Strategies**
1. Header mutations
    - Modify e_phoff, e_phnum, e_ehsize, phentsize, shentsize
    - Random values or extreme values (e.g., 0, 0xFFFFFFFF, 0x8000000000000000)
2. Magic byte mutations
    - Randomly corrupt any of the first four ELF identifier bytes
3. Block mutations
    - Delete a random block from the file body while preserving the first 0x40 bytes
4. Byte-level mutations
    - Bit flips, random byte substitutions, or zeroing arbitrary bytes across the file


### How Harness Works 
Our optional harness executes the target binary under `ptrace`, injects breakpoints at every discovered function symbol, and monitors execution to collect real-time coverage. All functions are automatically found via `nm`. At runtime, these offsets are rebased to support PIE and injects `int3` traps, which allows the harness to record every function reached during execution, thus implementing coverage. 

Each trap logs the function offset into a bitmap, producing function level coverage data that can be used for corpus ranking and prioritisation. This coverage effectively enables the fuzzer to detect new paths and focus mutations on inputs that expand reachable code regions.

I/O is fully piped, so the harness controls stdin, and  fully captures stdout and stderr. 

Output streams are captured into buffers for later analysis. A timeout handler uses alarm and forcefully kills the child if it hangs, allowing the system to detect infinite loops. Final results report whether the run crashed, timed out, or completed normally, along with the collected coverage map and captured program output.

## Bugs we could find 
- Out of bounds read/write typically trigerred by missing validation and underlying assumptions that buffer/array indices are assumed to be within bounds (eg. plaintext2/3)
- Buffer overflows
- Format string vulnerabilities 

## Fuzzer Improvements
**Process Resource Monitoring**
We could implement continuous tracking of peak RSS memory, as well as total CPU time, thread count, and file descriptors and handles open/used so as to detect memory leaks, CPU spikes or infinite loops/hangs, as well as resource exhaustion.

This would be implemented by integrating `psutil` for resource snapshots. These snapshots can be used both for detecting resource-based crashes and for guiding input prioritisation.

**More advanced ELF Mutation Strategies**
Currently, our ELF mutation strategies comprise random insertion/deletion of a block of bytes in the ELF body. This does not utilise ELF loader logic. As such, future ELF mutation strategies could be aware of the ELF file format, including direct manipulation of the program header table (PHT) and section header table (SHT), relocations and symbol table corruption, as well as mutating alignment and padding rules.

**PDF Mutation Strategies**
Introducing format specific mutation strategies for PDF inputs, which would entail:
1. Structural parsing of PDF objects via `xref`, `obj`, streams, and dictionary keys 
2. Mutation targets include broken `xref` offsets, oversized object lengths, malformed dictionaries, as well as uncompressed and compressed stream corruption
This would require partial parsing to enable structurally aware mutations instead of random byte edits to ensure the input remains valid.

**Enhanced Crash Statistics**
We could extend the crash handler to capture the register dump, the specific instruction pointer that has segfaulted using `ptrace`, as well as the address sanitiser and undefined behaviour sanitiser logs.

**Coverage Harness Precision**
We could further utilise the `ptrace` functionalities to detect hangs and infinite loops more accurately by monitoring register changes (e.g. repeating RIP address) rather than relying on a timeout handler to assume a hang/infinite loop event has occurred

However, our current breakpoint mechanism limits our register detection to only be at function boundaries, meanining implementing the above would only detect stalls at function calls and not within internal loops/function logic.

To make this more efficient, we would need an instruction-by-instruction stepping mechanism, which would also enable a more accurate coverage detection (for determining better path distinctions). However, this instruction stepping alternative is computationally impractical due to significant `ptrace` overheads. 
