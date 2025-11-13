import random
import os
import re

from format import format_type, FormatType
from .base import BaseMutator

# Generic mutation strategies
class GenericMutator(BaseMutator):
    known_ints = {
        "CHAR_MAX": 255,
        "INT_MAX": 2147483647,
        "UINT_MAX": 4294967295,
        "INT_MAX_+1": 2147483648,
        "LLONG_MAX": 9223372036854775807,
        "UINT_MAX_+1": 429496726,
        "INT_MIN": -2147483647,
        "INT_MIN-1": -2147483648,
    }

    # special byte values
    special_bytes = [
        b'\x00',  # nullbyte
        b'\x0A',  # newline
        b'\x0D',  # carriage return
        b'\x09',  # tab
        b'\x20',  # space
        b'\xFF',  # high byte
        b'\x7F',  # delete
        b'\x8B',  # UTF-8 start byte
        b'\xEF\xBB\xBF',  # UTF-8 BOM
    ]


    def __init__(self, example_input, input_queue, stop_event, binary_name, max_queue_size):
        super().__init__(example_input, input_queue, stop_event, binary_name, max_queue_size)
        print(example_input)

        self.original_input = None
        self.current_input = None
        self.parse_input()

    def parse_input(self):
        if isinstance(self.input, str):
            print(f'[DEBUG] plaintext input is a file path')
            try:
                with open(self.input, "rb") as f:
                    self.original_input = f.read()
            except Exception as e:
                print(f'[ERROR] error reading file: {e}')
                self.original_input = b''
        elif isinstance(self.input, bytes):
            self.original_input = self.input
        else:
            self.original_input = b''

        self.current_input = self.original_input

    # chainable mutation function that applies n_mutations sequentially, building on the current state
    def mutate(self, n_mutations=10):
        current_data = self.current_input
        # current_data = self.original_input

        lines = current_data.split(b'\n')
        num_lines = len(lines)

        full_mutation = random.choice([True, False])
        if num_lines <= 1 or full_mutation:
            # apply mutation on entire data
            mutated_data = self.apply_mutations(self.current_input)
        else:
            # apply mutations line-by-line
            nlines_to_mutate = random.randint(0, num_lines - 1)
            indices_to_mutate = self.random.sample(range(num_lines), k=nlines_to_mutate)
            for i in indices_to_mutate:
                lines[i] = self.apply_mutations(lines[i])

            mutated_data = b'\n'.join(lines)

        return mutated_data

    def apply_mutations(self, data, n_mutations=10):
        current_data = data
        # sequentially apply mutations in diff categories
        for _ in range(n_mutations):
            mutation_category = self.random.choice(["byte_mutation", "structure_mutation", "insertion_mutation"])

            if mutation_category == "byte_mutation":
                current_data = self.mutate_bytes(current_data)
            elif mutation_category == "structure_mutation":
                current_data = self.mutate_structure(current_data)
            elif mutation_category == "insertion_mutation":
                current_data = self.mutate_insertion(current_data)

            if isinstance(current_data, str):
                current_data = current_data.encode("latin-1", errors="ignore")

        self.current_input = current_data
        return current_data

    # byte lvl mutations
    def mutate_bytes(self, data):
        strategy = self.random.choice([
            'bit_flip_rand',
            'bit_flip_not',
            'insert_special_bytes',
            'replace_known_int',
            'replace_rand_bytes',
            'add_subtract_byte'
        ])

        if strategy == 'bit_flip_rand':
            return self.bit_flip_rand(data)
        # elif strategy == 'bit_flip_not':
        #     return self.bit_flip_not(data)
        # elif strategy == 'insert_special_bytes':
        #     return self.insert_special_bytes(data)
        elif strategy == 'replace_known_int':
            return self.replace_known_int(data)
        elif strategy == 'replace_rand_byte':
            return self.replace_rand_bytes(data)
        elif strategy == 'add_subtract_byte':
            return self.add_subtract_byte(data)

        return data

    # randomly apply structural mutations
    def mutate_structure(self, data):
        strategy = self.random.choice([
            'delete_rand_char',
            'splice_bits',
            'swap_bytes',
            # 'reverse_segment'
        ])

        if strategy == 'delete_rand_char':
            return self.delete_rand_char(data)
        elif strategy == 'splice_bits':
            return self.splice_bits(data)
        elif strategy == 'swap_bytes':
            return self.swap_bytes(data)
        # elif strategy == 'reverse_segment':
        #     return self.reverse_segment(data)

        return data

    # randomly apply insertion mutations
    def mutate_insertion(self, data):
        strategy = self.random.choice([
            'insert_rand_char',
            # 'insert_rand_large_char',
            'insert_known_int',
            'insert_random_string',
            'insert_boundary_values'
        ])

        if strategy == 'insert_rand_char':
            return self.insert_rand_char(data)
        # elif strategy == 'insert_rand_large_char':
        #     return self.insert_rand_large_char(data)
        elif strategy == 'insert_known_int':
            return self.insert_known_int(data)
        elif strategy == 'insert_random_string':
            return self.insert_random_string(data)
        elif strategy == 'insert_boundary_values':
            return self.insert_boundary_values(data)

        return data

    """Delete a random characters from input"""
    def delete_rand_char(self, input: bytes) -> bytes:
        if not input or len(input) <= 1:
            return input
        pos = random.randrange(len(input))
        end = random.randrange(pos + 1, len(input) + 1)
        return input[:pos] + input[end:]

    """Insert a random characters into input"""
    def insert_rand_char(self, input: bytes) -> bytes:
        pos = random.randrange(len(input) + 1)
        random_byte = os.urandom(1)
        return input[:pos] + random_byte + input[pos:]

    """Insert large number of characters into input"""
    def insert_rand_large_char(self, input: bytes) -> bytes:
        pos = random.randrange(len(input) + 1)
        random_byte = os.urandom(10000)
        return input[:pos] + random_byte + input[pos:]

    """Insert a known int into input"""
    def insert_known_int(self, input: bytes) -> bytes:
        num = random.choice(list(self.known_ints.values()))
        pos = random.randrange(len(input) + 1)

        # check n_bytes needed based on value
        if num <= 0xFF:
            byte_length = 1
        elif num <= 0xFFFF:
            byte_length = 2
        elif num <= 0xFFFFFFFF:
            byte_length = 4
        else:
            byte_length = 8

        try:
            num_bytes = num.to_bytes(byte_length, 'big')
            return input[:pos] + num_bytes + input[pos:]
        except OverflowError:
            # fallback to a smaller value if conversion fails
            fallback_num = 0xFFFFFFFF
            num_bytes = fallback_num.to_bytes(4, 'big')
            return input[:pos] + num_bytes + input[pos:]

    """Twos complement bit flip of input"""
    def bit_flip_not(self, input: bytes) -> bytes:
        if not input:
            return input
        pos = random.randrange(len(input))
        new_byte = (~input[pos]) & 0xFF
        return input[:pos] + bytes([new_byte]) + input[pos + 1:]

    """Bit flip of input"""
    def bit_flip_rand(self, input: bytes) -> bytes:
        if not input:
            return input
        pos = random.randrange(len(input))
        bit_pos = random.randrange(8)
        new_byte = input[pos] ^ (1 << bit_pos)
        return input[:pos] + bytes([new_byte]) + input[pos + 1:]

    """Splice random size of bytes from input at a random position"""
    def splice_bits(self, input: bytes) -> bytes:
        if len(input) < 2:
            return input

        start = random.randrange(len(input) - 1)
        end = random.randrange(start + 1, len(input))
        segment = input[start:end]

        insert_at = random.randrange(len(input) + 1)
        return input[:insert_at] + segment + input[insert_at:]

    # insert special bytes randomly
    def insert_special_bytes(self, input_data: bytes):
        if not input_data:
            return input_data
        pos = self.random.randrange(len(input_data) + 1)
        special_byte = self.random.choice(self.special_bytes)
        return input_data[:pos] + special_byte + input_data[pos:]

    # STRUCTURAL MUTATIONS
    # randomly swap two bytes
    def swap_bytes(self, input_data: bytes) -> bytes:
        if len(input_data) < 2:
            return input_data

        pos1 = self.random.randrange(len(input_data))
        pos2 = self.random.randrange(len(input_data))

        data = bytearray(input_data)
        data[pos1], data[pos2] = data[pos2], data[pos1]

        return bytes(data)

    # STRING INSERTION STRATEGIES
    # inserts random ASCII string
    def insert_random_string(self, input_data):
        rand_length = self.random.randrange(len(input_data) + 1)
        length = self.random.randint(5, 50)
        random_string = ''.join(self.random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?', k=length))
        return input_data[:rand_length] + random_string.encode('ascii') + input_data[rand_length:]

    # insert boundary values
    def insert_boundary_values(self, input_data):
        pos = self.random.randrange(len(input_data) + 1)
        boundary_values = [
            b'\x00\x00\x00\x00',  # null bytes
            b'\xFF\xFF\xFF\xFF',  # max bytes
            b'\x7F\xFF\xFF\xFF',  # max 32bit signed int
            b'\x80\x00\x00\x00',  # min 32bit signed int
            b'\xFF\xFE',          # utf 16
            b'\xC0\x80',          # UTF-8 encoding
        ]
        boundary_value = self.random.choice(boundary_values)
        return input_data[:pos] + boundary_value + input_data[pos:]

    def replace_known_int(self, input_data):
        mutated = input_data.decode('latin-1')
        matches = list(re.finditer(r'\d+', mutated))
        if not matches:
            return mutated

        m = self.random.choice(matches)
        start, end = m.start(), m.end()
        new_int = str(self.random.choice(list(self.known_ints.values())))
        mutated = mutated[:start] + new_int + mutated[end:]

        return mutated.encode('latin-1')

    # replace a random number of bytes
    def replace_rand_bytes(self, input_data):
        mutated = bytearray(input_data)
        input_len = len(mutated)
        nbytes_to_replace = self.random.randrange(input_len)
        for i in range(nbytes_to_replace):
            i = self.random.randrange(input_len)
            new_byte = self.random.randint(0, 255)
            mutated[i] = new_byte

        return bytes(mutated)

   # Add or subtract a small random value.
    def add_subtract_byte(self, input_data):
        mutated = bytearray(self.original_input)
        i = random.randint(0, len(mutated) - 1)
        increment = random.randint(1, 32)
        if random.choice([True, False]):
            mutated[i] = (mutated[i] + increment) % 256
        else:
            mutated[i] = (mutated[i] - increment) % 256

        return bytes(mutated)
