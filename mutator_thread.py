import time
import threading
import random
import queue

class MutatorThread(threading.Thread):
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
                print(f"MUTATOR INPUT: {mutated_input}")
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
    def delete_rand_char(self, input):
        if input == "":
            return input

        pos = random.randint(0, len(input) - 1)
        # print("Inserting", repr(random_character), "at", pos)
        return input[:pos] + input[pos + 1:]

    """Insert a random character into input"""
    def insert_rand_char(self, input):

        pos = random.randint(0, len(input))
        random_character = chr(random.randrange(32, 127))
        # print("Inserting", repr(random_character), "at", pos)
        return input[:pos] + random_character + input[pos:]

    """Twos complement bit flip of input"""
    def bit_flip_not(self, input):
        return ~input

    # def byte_flips(input):

    """Bit flip of input"""
    def bit_flip_rand(self, input):
        if input == "":
            return input

        pos = random.randint(0, len(input) - 1)
        size = random.randint(1, len(input) - pos)
        c = input[pos]
        bit = 1 << size
        new_c = chr(ord(c) ^ bit)
        # print("Flipping", bit, "in", repr(c) + ", giving", repr(new_c))
        return input[:pos] + new_c + input[pos + 1:]

    """Splice random size of bytes from input at a random position"""
    def splice_bits(self, input):
        start_pos = random.randint(0, len(input) - 2)
        # end_pos = random.randint(start_pos + 1, len(input) - 1)
        size = random.randint(1, len(input) - start_pos)
        mask = (1 << size) - 1
        shift = input >> start_pos
        splice = shift & mask

        return splice
