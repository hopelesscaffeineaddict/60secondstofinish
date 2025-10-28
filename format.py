import json
import csv
import xml.etree.ElementTree as ET
from enum import Enum

# Enum for supported input formats
class FormatType(Enum):
    JSON = 0
    CSV = 1 
    XML = 2
    JPEG = 3
    PDF = 4
    ELF = 5
    PLAINTEXT = 6
    UNKNOWN = -1

# Enum for magic bytes
class MagicBytes:
    JPEG = b"\xFF\xD8\xFF"
    ELF = b"\x7FELF"
    PDF = b"%PDF"

# Determines the format type corresponding to the provided input (first 2kb of file)
def format_type(example_input_file: str) -> FormatType:
    try:
        with open(example_input_file, "rb") as input_file:
            input = input_file.read(2048)
    except IOError as e:
        print(f"[!] Error reading file {example_input_file}: {e}")
        return FormatType.UNKNOWN

    if is_json(input):
        return FormatType.JSON
    elif is_csv(input):
        return FormatType.CSV
    elif is_xml(input):
        return FormatType.XML
    elif is_jpeg(input):
        return FormatType.JPEG
    elif is_pdf(input):
        return FormatType.PDF
    elif is_elf(input):
        return FormatType.ELF
    
    return FormatType.PLAINTEXT

# Checks if the provided byte input is a JSON format
def is_json(input: bytes) -> bool:
    try:
        json.loads(input.decode('utf-8'))
        return True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False

# Checks if the provided byte input is a CSV format
def is_csv(input: bytes) -> bool:
    try:
        input = input.decode('utf-8')

        if not input.strip():
            return False
        # Check if it resembles CSV file
        csv.Sniffer().sniff(decoded_input)
        return True
    except (csv.Error, UnicodeDecodeError):
        return False

# Checks if the provided byte input is a XML format
def is_xml(input: bytes) -> bool:
    try:
        ET.fromstring(input.decode('utf-8'))
        return True
    except ET.ParseError:
        return False 

# Checks if provided byte input is jpeg using magic bytes
def is_jpeg(input: bytes) -> bool:
    return input.startswith(MagicBytes.JPEG)

# Checks if provided byte input is pdf using magic bytes
def is_pdf(input: bytes) -> bool:
    return input.startswith(MagicBytes.PDF)

# Checks if provided byte input is elf using magic bytes 
def is_elf(input: bytes) -> bool:
    return input.startswith(MagicBytes.ELF)

