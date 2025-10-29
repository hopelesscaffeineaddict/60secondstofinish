import time
import threading
import random
import queue
import os
import json

class BaseMutator(threading.Thread):
    known_ints = {
        "CHAR_MAX": 255,
        "INT_MAX": 2147483647,
        "UINT_MAX": 4294967295,
        "LLONG_MAX": 9223372036854775807
    }

    def __init__(self, example_input, input_queue, stop_event, binary_name, max_queue_size=200):
        super().__init__(daemon=True)
        self.input = example_input
        self.input_queue = input_queue
        self.stop_event = stop_event
        self.max_queue_size = max_queue_size

        # create mutated input dir if it doesn't exist
        curr_dir = os.getcwd()
        mutated_dir = f"{curr_dir}/mutated_inputs"
        os.makedirs(mutated_dir, exist_ok=True)

        logfile_path = f"{mutated_dir}/mutated_{binary_name}.txt"
        self.log_file = open(logfile_path, "ab")
        self.log_file.write(f"example_input: {example_input}".encode())

    def run(self):
        mutations_done = 0

        # generate new mutated input
        while not self.stop_event.is_set():
            if self.input_queue.qsize() < self.max_queue_size:
                mutated_input = self.mutate()
                # add input to queue
                try:
                    self.input_queue.put(mutated_input, timeout=0.01)
                    mutations_done += 1

                    # log mutation
                    self.log_file.write(f"{mutations_done}: ".encode() + b' '+ mutated_input + b'\n')
                    self.log_file.flush()

                except queue.Full:
                    pass
            else:
                # small sleep to allow queue to make space
                time.sleep(0.01)
            
        self.log_file.close()

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

class JSONMutator(BaseMutator):
    
    def __init__(self, example_input, input_queue, stop_event, binary_name, max_queue_size=200):
        super().__init__(example_input, input_queue, stop_event, binary_name, max_queue_size)

    def mutate(self):

        try:
            content = json.loads(self.input.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Input is not valid JSON, fall back to base (dumb) mutator
            return super().mutate()

        strategy = random.choice([
            self._mutate_value,
            self._change_type,
            self._add_key_value,
            self._remove_key_value,
            self._mutate_array_structure,
            self._add_nested_json,
        ])

        try:
            mutated_content = strategy(content)
            # Use separators=(',', ':') for compact output without extra whitespace
            return json.dumps(mutated_content, separators=(',', ':')).encode('utf-8')
        except Exception:
            # If a mutation fails unexpectedly, fall back to a base mutation
            return super().mutate()
        
    def _mutate_value(self, data):
        """Recursively traverses a JSON object to mutate a single value."""
        if isinstance(data, dict) and data:
            key = random.choice(list(data.keys()))
            data[key] = self._mutate_value(data[key])
        elif isinstance(data, list) and data:
            idx = random.randrange(len(data))
            data[idx] = self._mutate_value(data[idx])
        elif isinstance(data, str):
            return self.bit_flip_rand(data.encode('utf-8')).decode('utf-8', errors='ignore')
        elif isinstance(data, (int, float)):
            choice = random.random()
            if choice < 0.5:
                return random.choice(list(self.known_ints.values()))
            else:
                return data + random.choice([-10, -1, 1, 10, 100])
        elif isinstance(data, bool):
            return not data
        return data
    
    def _change_type(self, data):
        """Changes the type of a randomly selected value."""
        if isinstance(data, dict) and data:
            key = random.choice(list(data.keys()))
            original_value = data[key]
            
            new_types = [123, "string", True, None, {}, [original_value]]
            # Avoid changing to the same type
            if isinstance(original_value, int): new_types.remove(123)
            if isinstance(original_value, str): new_types.remove("string")
            
            data[key] = random.choice(new_types)
        return data
    
    def _add_key_value(self, data):
        """Adds a new key-value pair to a dictionary."""
        if isinstance(data, dict):
            new_key = "fuzzer_key_" + str(random.randint(1000, 9999))
            new_value = random.choice([
                "new_value", 42, True, None, {"nested": 1}, [1,2,3]
            ])
            data[new_key] = new_value
        return data
    
    def _remove_key_value(self, data):
        """Removes a key-value pair from a dictionary."""
        if isinstance(data, dict) and data:
            key_to_remove = random.choice(list(data.keys()))
            del data[key_to_remove]
        return data

    def _mutate_array_structure(self, data):
        """Mutates an array by removing, duplicating, or adding an element."""
        if isinstance(data, list) and data:
            choice = random.random()
            if choice < 0.33 and len(data) > 0:
                data.pop(random.randrange(len(data)))
            elif choice < 0.66 and len(data) > 0: 
                idx = random.randrange(len(data))
                data.insert(idx, data[idx])
            else: 
                new_element = random.choice(["new_string", 999, False, {}])
                data.append(new_element)
        return data
    
    def _add_nested_json(self, data):
        """Adds a new, nested JSON object into a dictionary or a list."""
        if not isinstance(data, (dict, list)):
            return data

        nested_obj = {
            "fuzzer_nested_key": ''.join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(8)),
            "fuzzer_nested_val": random.choice(list(self.known_ints.values())),
            "fuzzer_nested_list": [None, True, 1337]
        }

        if isinstance(data, dict):
            new_key = "fuzzer_nested_obj_" + str(random.randint(1000, 9999))
            data[new_key] = nested_obj
        elif isinstance(data, list):
            data.append(nested_obj)
            
        return data