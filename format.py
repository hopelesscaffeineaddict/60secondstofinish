import json
import csv

JSON = 0
CSV = 1

# Determines the format type corresponding to the provided input
def format_type(example_input_file):
    with open(example_input_file, "rb") as input_file:
        input = input_file.read()

    if is_json(input):
        return JSON
    elif is_csv(input):
        return CSV

    return -1

# Checks if the provided input is a JSON format
def is_json(input):
    try:
        json.loads(input.decode('utf-8'))
        return True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False

# Checks if the provided input is a CSV format
def is_csv(input):
    try:
        input = input.decode('utf-8')
        return csv.Sniffer().has_header(input)
    except UnicodeDecodeError:
        return False

# TODO: extend whenever adding new format types
