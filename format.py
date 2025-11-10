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

def format_type(example_input_file: str) -> FormatType:
    try:
        with open(example_input_file, "rb") as input_file:
            input_bytes = input_file.read(2048)
    except IOError as e:
        print(f"[!] Error reading file {example_input_file}: {e}")
        return FormatType.UNKNOWN

    return get_format_from_bytes(input_bytes)

# Determines the format type from a byte string
def get_format_from_bytes(input_data: bytes) -> FormatType:
    
    input_slice = input_data[:2048]

    if is_json(input_slice):
        return FormatType.JSON
    elif is_csv(input_slice):
        return FormatType.CSV
    elif is_xml(input_slice):
        return FormatType.XML
    elif is_jpeg(input_slice):
        return FormatType.JPEG
    elif is_pdf(input_slice):
        return FormatType.PDF
    elif is_elf(input_slice):
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
def is_csv(input_bytes: bytes) -> bool:
    try:
        input_str = input_bytes.decode('utf-8', errors='ignore').strip()
        if not input_str:
            return False

        # must contain at least one comma
        if ',' not in input_str:
            return False

        # split into lines and ignore empty lines
        lines = [line for line in input_str.splitlines() if line.strip()]
        if len(lines) < 1:
            return False

        # require at least one line with multiple comma-delimited fields
        has_multiple_fields = any(len(line.split(',')) > 1 for line in lines)
        if not has_multiple_fields:
            return False

        return True

    except UnicodeDecodeError:
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

