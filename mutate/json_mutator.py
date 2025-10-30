import json
import io
import queue
import time
import random

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
        }

    def mutate(self):
        try:
            # handle both string and bytes input
            if isinstance(self.input, bytes):
                content = json.loads(self.input.decode('utf-8'))
            else:
                content = json.loads(self.input)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # if input not valid JSON, fallback to base mutator (ie. simple string mutation)
            return self._fallback_mutation()

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
            # always return bytes 
            return json.dumps(mutated_content, separators=(',', ':')).encode('utf-8')
        except Exception:
            # fallback to base mutation if mutation fails
            return self._fallback_mutation()
    
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
        # elif isinstance(data, str):
        #     return self.bit_flip_rand(data.encode('utf-8')).decode('utf-8', errors='ignore')
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