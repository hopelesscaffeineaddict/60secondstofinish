# 60secondstofinish
COMP6447 Fuzzer


### Project Directory Structure 
fuzzer_project/
├── Dockerfile                 # Required for submission
├── requirements.txt           # Python dependencies (if any)
├── main.py                    # Entry point of the fuzzer
├── README.md                  # Project documentation
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

