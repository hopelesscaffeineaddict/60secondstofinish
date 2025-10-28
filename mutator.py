import time
import threading
import random
import queue
import os

class Mutator(threading.Thread):
    known_ints = {
        "CHAR_MAX": 255,
        "INT_MAX": 2147483647,
        "UINT_MAX": 4294967295,
        "LLONG_MAX": 9223372036854775807
    }

    def __init__(self, example_input, input_queue, stop_event, max_queue_size=200):
        super().__init__(daemon=True)
        self.input = example_input
        self.input_queue = input_queue
        self.stop_event = stop_event
        self.max_queue_size = max_queue_size

    def run(self):
        mutations_done = 0

        # generate new mutated input
        while not self.stop_event.is_set():
            if self.input_queue.qsize() < self.max_queue_size:
                mutated_input = self.mutate()
                # add input to queue
                try:
                    self.input_queue.put(mutated_input, timeout=0.5)
                    mutations_done += 1
                except queue.Full:
                    pass
            else:
                # small sleep to allow queue to make space
                time.sleep(0.01)

    def mutate(self):
        strategy = random.choice(['delete_rand_char',
                                'insert_rand_char',
                                'bit_flip_not',
                                'bit_flip_rand',
                                'splice_bits'])

        if strategy == 'delete_rand_char':
            mutated_str = self.delete_rand_char(self.input)
        elif strategy == 'insert_rand_char':
            mutated_str = self.insert_rand_char(self.input)
        elif strategy == 'bit_flip_not':
            mutated_str = self.bit_flip_not(self.input)
        elif strategy == 'bit_flip_rand':
            mutated_str = self.bit_flip_rand(self.input)
        elif strategy == 'splice_bits':
            mutated_str = self.splice_bits(self.input)

        return mutated_str

    """Delete a random character from input"""
    def delete_rand_char(self, input: bytes) -> bytes:
        if not input:
            return input
        pos = random.randrange(len(input))
        return input[:pos] + input[pos + 1:]

    """Insert a random character into input"""
    def insert_rand_char(self, input: bytes) -> bytes:
        pos = random.randrange(len(input) + 1)
        random_byte = os.urandom(1)
        return input[:pos] + random_byte + input[pos:]

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
