import time
import threading
import random
import queue
import os

from format import format_type, FormatType
from .base import BaseMutator

# Generic mutation strategies 
class GenericMutator(threading.Thread):
    known_ints = {
        "CHAR_MAX": 255,
        "INT_MAX": 2147483647,
        "UINT_MAX": 4294967295,
        "INT_MAX_+1": 2147483648,
        "LLONG_MAX": 9223372036854775807,
        "UINT_MAX_+1": 429496726
    }

    def __init__(self, format_type, input, input_queue, stop_event, binary_name, max_queue_size=200):
        super().__init__(daemon=True)
        self.max_queue_size = max_queue_size
        self.input_queue = input_queue
        self.stop_event = stop_event
        self.max_queue_size = max_queue_size

    def mutate(self):
        strategy = random.choice(['delete_rand_char',
                                'insert_rand_char',
                                # 'insert_rand_large_char',
                                'insert_known_int',
                                'bit_flip_not',
                                'bit_flip_rand',
                                'splice_bits'])

        if strategy == 'delete_rand_char':
            mutated_str = self.delete_rand_char(self.input)
        elif strategy == 'insert_rand_char':
            mutated_str = self.insert_rand_char(self.input)
        # elif strategy == 'insert_rand_large_char':
        #     mutated_str = self.insert_rand_large_char(self.input)
        elif strategy == 'insert_known_int':
            mutated_str = self.insert_known_int(self.input)
        elif strategy == 'bit_flip_not':
            mutated_str = self.bit_flip_not(self.input)
        elif strategy == 'bit_flip_rand':
            mutated_str = self.bit_flip_rand(self.input)
        elif strategy == 'splice_bits':
            mutated_str = self.splice_bits(self.input)

        return mutated_str

    """Delete a random characters from input"""
    def delete_rand_char(self, input: bytes) -> bytes:
        if not input:
            return input
        pos = random.randrange(len(input) - 1)
        end = random.randrange(pos + 1, len(input))
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
        num_bytes = num.to_bytes(4, 'big')
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
