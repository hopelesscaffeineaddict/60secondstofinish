import time
import threading
import random
import queue
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
        "UINT_MAX_+1": 429496726
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

        # flags 
        self.protect_first_line = False 
        self.is_numeric = False 

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

        self.set_password_protection(False)  
        self.current_input = self.original_input
        self.check_if_numeric()

        print(f'[DEBUG] Password Protection for {self.binary_name}: {self.protect_first_line}')

    # Set password protection flag from runner
    def set_password_protection(self, protect_first_line):
        self.protect_first_line = protect_first_line
        print(f'[DEBUG3]: Protect first line for {self.binary_name}: {self.protect_first_line}')
        if protect_first_line:
            try:
                self.first_line_end = self.original_input.index(b'\n')
                print(f'[DEBUG] Password protection for {self.binary_name} enabled, first line ends at position {self.first_line_end}')
                self.protect_first_line = True 
                print(f'[DEBUG2] Password Protection for {self.binary_name}: {self.protect_first_line}')
            except ValueError:
                # No newline found, treat entire input as first line
                self.first_line_end = len(self.original_input)
                print('[DEBUG] No newline found, treating entire input as first line')

    # Check whether non protected input contains numeric content
    def check_if_numeric(self):
        try:
            # Try to decode as UTF-8 to check for numeric content
            content = self.original_input.decode('utf-8')
            
            # Split by lines and check if most content is numeric
            lines = content.split('\n')
            numeric_lines = 0
            total_lines = 0
            
            for i, line in enumerate(lines):
                # Skip the first line if it's protected (password)
                if self.protect_first_line and i == 0:
                    continue
                    
                if line.strip():
                    total_lines += 1
                    if re.match(r'^-?\d+$', line.strip()):
                        numeric_lines += 1
            
            # If more than 70% of non-empty lines are numeric, consider it numeric
            if total_lines > 0 and (numeric_lines / total_lines) > 0.7:
                self.is_numeric = True
                print('[DEBUG] Input detected as primarily numeric')
        except UnicodeDecodeError:
            pass

    # chainable mutation function that applies n_mutations sequentially, building on the current state
    def mutate(self, n_mutations=10):
        # print(f'[DEBUG] Password Protection for {self.binary_name}: {self.protect_first_line}')
        current_data = self.current_input
        # print(current_data)

        # If we have password protection, only mutate after the first line
        if self.protect_first_line:
            # print(f'DEBUG: Password protected, skipping mutation of first line')
            # Split into first line and rest
            parts = current_data.split(b'\n', 1)
            password = parts[0] + b'\n'
            remainder = parts[1] if len(parts) > 1 else b''
            
            for _ in range(n_mutations):
                # Only mutate the remainder
                mutation_type = self.random.choice(["byte_mutation", "structure_mutation", "insertion_mutation"])
                
                if mutation_type == "byte_mutation":
                    remainder = self.mutate_bytes(remainder)
                elif mutation_type == "structure_mutation":
                    remainder = self.mutate_structure(remainder)
                elif mutation_type == "insertion_mutation":
                    remainder = self.mutate_insertion(remainder)
            
            # Reassemble with original first line
            # try:
            #     pw_str = password.decode('utf-8', errors='replace')
            #     rem_str = remainder.decode('utf-8', errors='replace')
            #     print(f"[DEBUG] Checking password: {pw_str!r}")
            #     print(f"[DEBUG] Checking remainder: {rem_str!r}")
            # except Exception as e:
            #     print(f'[DEBUG] EXCEPTION')
            #     print(f"[DEBUG] Decode error during print: {e}")
            #     print(f"[DEBUG] Raw password bytes: {password[:100]!r}")
            #     print(f"[DEBUG] Raw remainder bytes: {remainder[:100]!r}")
            
            current_data = password + remainder
        # If input is numeric, use numeric mutations
        elif self.is_numeric:
            for _ in range(n_mutations):
                current_data = self.mutate_numeric(current_data)
        # Otherwise, use all mutation types
        else:
            for _ in range(n_mutations):
                mutation_category = self.random.choice(["byte_mutation", "structure_mutation", "insertion_mutation"])
                
                if mutation_category == "byte_mutation":
                    current_data = self.mutate_bytes(current_data)
                elif mutation_category == "structure_mutation":
                    current_data = self.mutate_structure(current_data)
                elif mutation_category == "insertion_mutation":
                    current_data = self.mutate_insertion(current_data)

        self.current_input = current_data
        return current_data

    # mutations for numeric data
    def mutate_numeric(self, data):
        """Apply mutations specific to numeric data"""
        strategy = self.random.choice([
            'insert_known_int',
            'bit_flip_numeric',
            'insert_boundary_values',
            'arithmetic_mutation',
        ])
        
        if strategy == 'insert_known_int':
            return self.insert_known_int(data)
        elif strategy == 'bit_flip_numeric':
            return self.bit_flip_numeric(data)
        elif strategy == 'insert_boundary_values':
            return self.insert_boundary_values(data)
        elif strategy == 'arithmetic_mutation':
            return self.arithmetic_mutation(data)
        
        return data

    # arithmetic mutations 
    def arithmetic_mutation(self, data):
        try:
            # decode as utf 8 to work w text
            content = data.decode('utf-8')
            lines = content.split('\n')
            
            # pick random line to mutate, skip first line if protected
            start_idx = 0
            if self.protect_first_line:
                start_idx = 1

            if lines[start_idx:]:
                line_idx = self.random.randint(start_idx, len(lines) - 1)
                line = lines[line_idx].strip()
                
                # Check if the line is numeric
                if re.match(r'^-?\d+$', line):
                    try:
                        num = int(line)
                        # Apply a simple arithmetic operation
                        op = self.random.choice([50, -50, 100, -100, 1000, -1000, 2000, -2000])
                        new_num = num + op
                        
                        lines[line_idx] = str(new_num)
                        
                        # Re-encode and return
                        return '\n'.join(lines).encode('utf-8')
                    except (ValueError, ZeroDivisionError):
                        pass
        except UnicodeDecodeError:
            pass
        
        # Fallback to regular mutations if numeric parsing fails
        return self.insert_known_int(data)

    # Simplified bit flip mutation for numeric data
    def bit_flip_numeric(self, data):
        """Apply bit flips to numeric values in the input"""
        try:
            # Try to decode as UTF-8 to work with text
            content = data.decode('utf-8')
            lines = content.split('\n')
            
            # Pick a random line to mutate (skip first line if protected)
            start_idx = 1 if self.protect_first_line else 0
            if lines[start_idx:]:
                line_idx = self.random.randint(start_idx, len(lines) - 1)
                line = lines[line_idx].strip()
                
                # Check if the line is numeric
                if re.match(r'^-?\d+$', line):
                    try:
                        num = int(line)
                        # Apply a random bit flip
                        bit_pos = self.random.randint(0, 31)  # Assume 32-bit integers
                        new_num = num ^ (1 << bit_pos)
                        lines[line_idx] = str(new_num)
                        
                        # Re-encode and return
                        return '\n'.join(lines).encode('utf-8')
                    except ValueError:
                        pass
        except UnicodeDecodeError:
            pass
        
        # Fallback to regular bit flip if numeric parsing fails
        return self.bit_flip_rand(data)

    # byte lvl mutations
    def mutate_bytes(self, data):
        strategy = self.random.choice([
            'bit_flip_rand',
            'bit_flip_not',
            'insert_special_bytes'
        ])
        
        if strategy == 'bit_flip_rand':
            return self.bit_flip_rand(data)
        elif strategy == 'bit_flip_not':
            return self.bit_flip_not(data)
        elif strategy == 'insert_special_bytes':
            return self.insert_special_bytes(data)
        
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
        known_ints = {
            "CHAR_MAX": 255,
            "INT_MAX": 2147483647,
            "UINT_MAX": 4294967295,
            "INT_MAX_+1": 2147483648,
            "LLONG_MAX": 9223372036854775807,
            "UINT_MAX_+1": 429496726
        }

        num = random.choice([
            255, 2147483647, 4294967295, 2147483648, 9223372036854775807, 429496726
            -1, -2, -255, -1024, -32768, -2147483648,   
        ])

        pos = random.randrange(len(input) + 1)

        # Determine byte width
        if abs(num) <= 0xFF:
            byte_length = 1
        elif abs(num) <= 0xFFFF:
            byte_length = 2
        elif abs(num) <= 0xFFFFFFFF:
            byte_length = 4
        else:
            byte_length = 8

        try:
            # Encode with signed=True so negatives are supported
            num_bytes = num.to_bytes(byte_length, 'big', signed=True)
            return input[:pos] + num_bytes + input[pos:]
        except OverflowError:
            fallback_num = -0x7FFFFFFF  # min 32-bit signed int
            num_bytes = fallback_num.to_bytes(4, 'big', signed=True)
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
        pos = random.randrange(len(input_data) + 1)
        special_byte = random.choice(self.special_bytes)
        return input_data[:pos] + special_byte + input_data[pos:]   

    # STRUCTURAL MUTATIONS
    # randomly swap two bytes
    def swap_bytes(self, input_data: bytes) -> bytes:
        if len(input_data) < 2:
            return input_data
        
        pos1 = random.randrange(len(input_data))
        pos2 = random.randrange(len(input_data))
        
        data = bytearray(input_data)
        data[pos1], data[pos2] = data[pos2], data[pos1]
        
        return bytes(data)

    # STRING INSERTION STRATEGIES
    # inserts random ASCII string
    def insert_random_string(self, input_data):
        rand_length = random.randrange(len(input_data) + 1)
        length = random.randint(5, 50)
        random_string = ''.join(random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?', k=length))
        return input_data[:rand_length] + random_string.encode('ascii') + input_data[rand_length:]   

    # insert boundary values
    def insert_boundary_values(self, input_data):
        pos = random.randrange(len(input_data) + 1)
        boundary_values = [
            b'\x00\x00\x00\x00',  # null bytes
            b'\xFF\xFF\xFF\xFF',  # max bytes
            b'\x7F\xFF\xFF\xFF',  # max 32bit signed int
            b'\x80\x00\x00\x00',  # min 32bit signed int
            b'\xFF\xFE',          # utf 16
            b'\xC0\x80',          # UTF-8 encoding
        ]
        boundary_value = random.choice(boundary_values)
        return input_data[:pos] + boundary_value + input_data[pos:]