import threading
import random

class Mutator():
    known_ints = {
        "CHAR_MAX": 255,
        "INT_MAX": 2147483647,
        "UINT_MAX": 4294967295,
        "LLONG_MAX": 9223372036854775807
    }


    def __init__(self, input: bytes, ctx, format_type, max_mutations: int):
        self.input = input
        self.ctx = ctx
        self.format_type = format_type
        self.max_mutations = max_mutations

        self.input_queue = []
        self.mutator_condition = threading.Condition()
        self.stop_event = ctx.Event()
        self.mutator_thread = threading.Thread(target=self.mutator_loop)

    def mutator_loop(self):
        mutations_done = 0

        # generate new mutated input
        while not self.stop_event.is_set():
            mutated_input = self.mutate(self.input)
        
            # add input to queue
            with self.mutator_condition:
                self.input_queue.append(mutated_input)

                # notify runner thread that new input is available 
                self.mutator_condition.notify()

                mutations_done += 1

    # TODO: in the mutator function, when an input is added to the input_queue, notify the condition
    def start(self):
        self.mutator_thread.start()

    # terminate mutator thread
    def stop(self):
        self.stop_event.set()
        self.mutator_thread.join()

    # uses one of the below mutation strategies randomly
    def mutate(self, data: bytes):
        strategy = random.choice(['delete_rand_char', 
                                'insert_rand_char', 
                                'bit_flip_not', 
                                'bit_flip_rand', 
                                'splice_bits'])

        if strategy == 'delete_rand_char':
            mutated_str = self.delete_rand_char(input)
        elif strategy == 'insert_rand_char':
            mutated_str = self.insert_rand_char(input)
        elif strategy == 'bit_flip_not':
            mutated_str = self.bit_flip_not(input)
        elif strategy == 'bit_flip_rand':
            mutated_str = self.bit_flip_rand(input)
        elif strategy == 'splice_bits':
            mutated_str = self.splice_bits(input)

    """Delete a random character from input"""
    def delete_rand_char(input: str):

        if input == "":
            return input

        pos = random.randint(0, len(input) - 1)
        # print("Inserting", repr(random_character), "at", pos)
        return input[:pos] + input[pos + 1:]
    
    """Insert a random character into input"""
    def insert_rand_char(input: str):
        
        pos = random.randint(0, len(input))
        random_character = chr(random.randrange(32, 127))
        # print("Inserting", repr(random_character), "at", pos)
        return input[:pos] + random_character + input[pos:]

    """Twos complement bit flip of input"""
    def bit_flip_not(input: str):
        return ~input
    
    # def byte_flips(input):
    
    """Bit flip of input"""
    def bit_flip_rand(input: str):
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
    def splice_bits(input: str):
        start_pos = random.randint(0, len(input) - 2)
        # end_pos = random.randint(start_pos + 1, len(input) - 1)
        size = random.randint(1, len(input) - start_pos)
        mask = (1 << size) - 1
        shift = input >> start_pos
        splice = shift & mask

        return splice
        
    # """Overwrite data with known ints"""
    # def known_ints():
    #     if input == "":
    #         return input  

    #     pos = random.randint(0, len(input) - 1)
    #     pos 
    #     return input[:pos] + random_character + input[pos + 2:]

