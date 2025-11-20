## How 60secondstofinish works 
### Overview 
60secondstofinish is a black box coverage guided fuzzer targeting binaries that accept both structured and semi-structured formats, namely CSV, JSON, ELF, JPEG, XML and plaintext. The system mutates example inputs and executes the target binary to detect crashes, hangs, and unexpected behaviour.
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
- XML (eugenia/arhaan)
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


**PDF Mutation Strategies**
Introducing format specific mutation strategies for PDF inputs, which would entail:
1. Structural parsing of PDF objects via `xref`, `obj`, streams, and dictionary keys 
2. Mutation targets include broken `xref` offsets, oversized object lengths, malformed dictionaries, as well as uncompressed and compressed stream corruption
This would require partial parsing to enable structurally aware mutations instead of random byte edits to ensure the input remains valid.

