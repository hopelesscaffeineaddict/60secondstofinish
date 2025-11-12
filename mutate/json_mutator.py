import json
import io
import queue
import time
import random
import copy

from .base import BaseMutator
from format import FormatType

# json-specific mutator strategies
class JSONMutator(BaseMutator):
    
    def __init__(self, example_input, input_queue, stop_event, binary_name, max_queue_size=200):
        super().__init__(example_input, input_queue, stop_event, binary_name, max_queue_size)
        
        # known ints dict
        self.known_ints = {
            "zero": 0,
            "one": 1,
            "negative_one": -1,
            "small_positive": 42,
            "small_negative": -42,
            "large_positive": 2147483647,
            "large_negative": -2147483648,
            "max_int": 2**31 - 1,
            "min_int": -2**31,
            "boundary_values": [0, 1, 2, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 100, 1000, 10000, 100000]
        }

        self.original_json = None
        self.current_json = None
        self.parse_json()
    
    # parse JSON input
    def parse_json(self):
        try:
            if isinstance(self.input, bytes):
                print('[DEBUG] decoding bytes to json')
                self.original_json = json.loads(self.input.decode('utf-8'))
            else:
                self.original_json = json.loads(self.input)
        
            # create a copy of original for mutate()
            self.current_json = copy.deepcopy(self.original_json)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f'[DEBUG] Error parsing JSON: {e}')
            self.original_json = {}
            self.current_json = {}
        
    # chainable mutation function that applies n_mutations sequentially, building on the current state
    def mutate(self, n_mutations=1):  # Reduced from 10 to 1 for speed
        current_data = copy.deepcopy(self.current_json)
        
        for _ in range(n_mutations):
            mutation_category = self.random.choice(["value_mutation", "structure_mutation", "content_mutation", "boundary_mutation"])
            if mutation_category == "value_mutation":
                current_data = self.mutate_values(current_data)
            elif mutation_category == "structure_mutation":
                current_data = self.mutate_structure(current_data)
            elif mutation_category == "content_mutation":
                current_data = self.mutate_content(current_data)
            elif mutation_category == "boundary_mutation":
                current_data = self.mutate_boundary_values(current_data)
        
        self.current_json = current_data
        
        # serialise and return as bytes
        try:
            return json.dumps(current_data, separators=(',', ':')).encode('utf-8')
        except (TypeError, ValueError):
            return self._fallback_mutation()

    # value type mutations
    def mutate_values(self, data):
        strategy = self.random.choice([
            'mutate_value',
            'change_type',
        ])

        if strategy == 'mutate_value':
            return self._mutate_value(data)
        elif strategy == 'change_type':
            return self._change_type(data)
        
        return data

    # structural mutations
    def mutate_structure(self, data):
        strategy = self.random.choice([
            'add_key_value',
            'remove_key_value',
            'duplicate_key_value',
            'mutate_array_structure',
        ])
        
        if strategy == 'add_key_value':
            return self._add_key_value(data)
        elif strategy == 'remove_key_value':
            return self._remove_key_value(data)
        elif strategy == 'duplicate_key_value':
            return self._duplicate_key_value(data)
        elif strategy == 'mutate_array_structure':
            return self._mutate_array_structure(data)
        
        return data

    # content mutations
    def mutate_content(self, data):
        strategy = self.random.choice([
            'add_nested_json',
            'duplicate_json',
        ])
        
        if strategy == 'add_nested_json':
            return self._add_nested_json(data)
        elif strategy == 'duplicate_json':
            return self._duplicate_json(data)
        
        return data 

    # boundary value mutations - targeting fields that might represent lengths/sizes
    def mutate_boundary_values(self, data):
        """Specifically target numeric fields that might represent lengths or sizes"""
        if isinstance(data, dict):
            for key in data:
                # Look for keys that might represent lengths or sizes
                if any(keyword in key.lower() for keyword in ["len", "length", "size", "count", "num"]):
                    if isinstance(data[key], (int, float)):
                        # Replace with a boundary value
                        data[key] = self.random.choice(self.known_ints["boundary_values"])
                else:
                    # Recursively check nested objects
                    data[key] = self.mutate_boundary_values(data[key])
        elif isinstance(data, list) and data:
            # Randomly pick an element to mutate
            idx = self.random.randrange(len(data))
            data[idx] = self.mutate_boundary_values(data[idx])
        
        return data

    # fallback mutation 
    def _fallback_mutation(self):
        """Simple fallback mutation when JSON parsing fails"""
        if isinstance(self.input, bytes):
            input_str = self.input.decode('utf-8', errors='ignore')
        else:
            input_str = str(self.input)
        
        # Add random characters
        n_insert = random.randint(10, 200)
        extra_chars = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=n_insert))
        return input_str + extra_chars
    
    def _mutate_value(self, data):
        """Recursively traverses a JSON object to mutate a single value."""
        if isinstance(data, dict) and data:
            key = random.choice(list(data.keys()))
            data[key] = self._mutate_value(data[key])
        elif isinstance(data, list) and data:
            idx = random.randrange(len(data))
            data[idx] = self._mutate_value(data[idx])
        elif isinstance(data, str):
            # Mutate string by adding characters
            n_insert = random.randint(1, 10)
            extra_chars = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=n_insert))
            return data + extra_chars
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
        """Changes type of a randomly selected value."""
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
            new_key = "fuzzer_key_" + str(random.randint(1, 1000))
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
    
    # duplicate a key value pair
    def _duplicate_key_value(self, data):
        if isinstance(data, dict) and data:
            key_to_duplicate = random.choice(list(data.keys()))
            value_to_duplicate = data[key_to_duplicate]
            new_key = key_to_duplicate + "duplicate"
            data[new_key] = value_to_duplicate
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
            new_key = "fuzzer_nested_obj_" + str(random.randint(1, 1000))
            data[new_key] = nested_obj
        elif isinstance(data, list):
            data.append(nested_obj)
            
        return data
    
    # duplicates JSON object
    def _duplicate_json(self, data):
        if isinstance(data, dict):
            num_copies = random.randint(2, 5) 
            result = []
            for i in range(num_copies):
                result.append(copy.deepcopy(data))
            return result
        
        # duplicate list
        elif isinstance(data, list):
            return data + copy.deepcopy(data)
        else:
            return data