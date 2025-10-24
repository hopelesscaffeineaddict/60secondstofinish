import subprocess
import format

class Fuzzer():
    def __init__(self, binary, input_file) -> None:
        self.binary = binary
        self.example_input = input_file

    # Runs the binary with the provided input
    def run(self, input) -> subprocess.CompletedProcess:
        return subprocess.run(self.binary, input=input)

    # Finds the corresponding format for the binary
    # TODO: potentially return/set a fuzzer object relating to the format type
    def find_format(self) -> int:
        with open(self.example_input, "rb") as input_file:
            input = input_file.read()

        return format.format_type(input)

