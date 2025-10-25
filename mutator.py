import threading
import random

class Mutator():
    known_ints = {
        "CHAR_MAX": 255,
        "INT_MAX": 2147483647,
        "UINT_MAX": 4294967295,
        "LLONG_MAX": 9223372036854775807
    }


    def __init__(self):
        self.input_queue = []
        self.condition = threading.Condition()

    # TODO: in the mutator function, when an input is added to the input_queue, notify the condition
    def start(self):
        print("TODO")

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

