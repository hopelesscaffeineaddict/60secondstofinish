# 60secondstofinish
COMP6447 Fuzzer

### Order of implementation
To prioritise for midpoint (ie. the bare minimum):
1. Core engine/stuffies in main.py (basic argument parsic, binary/input matching), read file
2. harness.py: Harness class w a execute method? Execute binary, pipe input to stdin, enforce timeout, return exit code
3. 


### Possible Project Directory Structure 
fuzzer_project/
├── Dockerfile                 # Required for submission
├── requirements.txt           # Python dependencies (if any)
├── main.py                    # Entry point of the fuzzer
├── README.md                  # (Optional) Project documentation
│
├── src/                       # Core fuzzer logic
│   ├── __init__.py
│   ├── input_parser.py        # Argument parsing and validation
│   ├── binary_detector.py     # Detects input format (JSON, XML, etc.)
│   ├── harness.py             # Executes target and detects crashes
│   ├── mutator.py             # The mutation engine
│   ├── stats_collector.py     # Tracks and reports statistics
│   └── fuzzer.py              # Main Fuzzer class that orchestrates everything
│
├── format_handlers/           # Format-specific mutation logic
│   ├── __init__.py
│   ├── base_handler.py        # Abstract base class for handlers
│   ├── json_handler.py        # Mutations for JSON files
│   ├── xml_handler.py         # Mutations for XML files
│   ├── csv_handler.py         # Mutations for CSV files
│   ├── jpeg_handler.py        # Mutations for JPEG files
│   ├── elf_handler.py         # Mutations for ELF files
│   ├── pdf_handler.py         # Mutations for PDF files
│   └── plaintext_handler.py   # Mutations for generic text
│
└── binaries/                     # Binaries
│
└── input_files/                  # Provided example input   

### Architecture Diagram
┌─────────────────────────────────────────────────────────────────────┐
│                           Main Controller                          │
│  - Orchestrates the entire fuzzing process                         │
│  - Manages time limits and resource allocation                     │
│  - Coordinates between all other components                        │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Input Parser                               │
│  - Parses command-line arguments                                    │
│  - Validates input directories and files                           │
│  - Matches binaries to their corresponding input files             │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Binary Detector                              │
│  - Detects the input format (JSON, XML, CSV, etc.)                │
│  - Determines appropriate mutation strategies                      │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Mutation Engine                               │
│  - Implements various mutation strategies                          │
│  - Generates new inputs based on the detected format               │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Test Harness                                │
│  - Executes the target binary with mutated inputs                  │
│  - Detects crashes, hangs, and other abnormal behavior            │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Statistics Collector                            │
│  - Tracks execution statistics                                     │
│  - Reports crashes found and other metrics                        │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Format Handlers                               │
│  - Specialized handlers for different input formats                │
│  - Implements format-specific mutation strategies                  │
└─────────────────────────────────────────────────────────────────────┘