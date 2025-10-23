import subprocess
import format

INPUTS_DIR = "example_inputs"

class Fuzzer():

    def __init__(self, binary) -> None:
        self.binary = binary

    def run(self, input) -> subprocess.CompletedProcess:
        return subprocess.run(self.binary, input=input)

    def find_format(self) -> int:
        with open(f'{INPUTS_DIR}/{self.binary}.txt', "rb") as input_file:
            input = input_file.read()

        return format.format_type(input)

