import os
import random
import struct
from .base import BaseMutator

class ELFMutator(BaseMutator):
    # ELF constants
    ELF_MAGIC = b'\x7fELF'
    
    # ELF header fields
    EI_NIDENT = 16
    EI_CLASS = 4
    EI_DATA = 5
    EI_VERSION = 6
    EI_OSABI = 7
    EI_ABIVERSION = 8
    
    ELFCLASS32 = 1
    ELFCLASS64 = 2
    
    ELFDATA2LSB = 1
    ELFDATA2MSB = 2
    
    # Known extreme values for header fields
    EXTREME_VALUES = [
        0x0, 0x1, 0xFF, 0xFFFF, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF,
        0x7FFFFFFF, 0x80000000, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000
    ]
    
    def __init__(self, example_input, input_queue, stop_event, binary_name, max_queue_size):
        super().__init__(example_input, input_queue, stop_event, binary_name, max_queue_size)
        
        self.ith_mutation = 0
        self.original_input = None
        self.current_input = None
        self.is_64bit = False
        self.parse_input()
    
    def parse_input(self):
        if isinstance(self.input, str):
            print(f'[DEBUG] ELF input is a file path')
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
        
        # Check if it's a valid ELF and determine if 32 or 64 bit
        if len(self.original_input) >= self.EI_NIDENT:
            if self.original_input[:4] == self.ELF_MAGIC:
                self.is_64bit = (self.original_input[self.EI_CLASS] == self.ELFCLASS64)
    
    def mutate(self):
        if (self.ith_mutation == 10):
            current_data = self.original_input
            self.ith_mutation = 0
        else:
            current_data = self.current_input
        
        # Apply mutations
        mutated_data = self.apply_elf_mutations(current_data)
        
        self.current_input = mutated_data
        self.ith_mutation += 1
        return mutated_data
    
    def apply_elf_mutations(self, data):
        # Choose a mutation strategy
        mutation_strategy = random.choice([
            'magic_bytes',
            'header_flags',
            'header_extreme_values',
            'header_sizes',
            'block_deletion',
            'byte_corruption'
        ])
        
        if mutation_strategy == 'magic_bytes':
            return self.mutate_magic_bytes(data)
        elif mutation_strategy == 'header_flags':
            return self.mutate_header_flags(data)
        elif mutation_strategy == 'header_extreme_values':
            return self.mutate_header_extreme_values(data)
        elif mutation_strategy == 'header_sizes':
            return self.mutate_header_sizes(data)
        elif mutation_strategy == 'block_deletion':
            return self.delete_random_block(data)
        elif mutation_strategy == 'byte_corruption':
            return self.corrupt_random_bytes(data)
        
        return data
    
    def mutate_magic_bytes(self, data):
        if len(data) < 4:
            return data
        
        # Corrupt the ELF magic bytes
        mutated = bytearray(data)
        for i in range(4):
            if random.random() < 0.5:  # 50% chance to corrupt each byte
                mutated[i] = random.randint(0, 255)
        
        return bytes(mutated)
    
    def mutate_header_flags(self, data):
        if len(data) < 0x40:  # Minimum ELF header size
            return data
        
        mutated = bytearray(data)
        
        # Mutate e_phoff (program header offset)
        if self.is_64bit:
            # 64-bit ELF
            e_phoff_offset = 0x20
            e_phnum_offset = 0x38
            e_ehsize_offset = 0x34
        else:
            # 32-bit ELF
            e_phoff_offset = 0x1C
            e_phnum_offset = 0x2C
            e_ehsize_offset = 0x28
        
        # Randomly choose which field to mutate
        field_to_mutate = random.choice(['e_phoff', 'e_phnum', 'e_ehsize'])
        
        if field_to_mutate == 'e_phoff':
            # Mutate program header offset
            if self.is_64bit:
                # 64-bit: 8 bytes
                new_value = random.randint(0, 0xFFFFFFFFFFFFFFFF)
                mutated[e_phoff_offset:e_phoff_offset+8] = struct.pack('<Q', new_value)
            else:
                # 32-bit: 4 bytes
                new_value = random.randint(0, 0xFFFFFFFF)
                mutated[e_phoff_offset:e_phoff_offset+4] = struct.pack('<I', new_value)
        
        elif field_to_mutate == 'e_phnum':
            # Mutate program header number
            new_value = random.randint(0, 0xFFFF)
            mutated[e_phnum_offset:e_phnum_offset+2] = struct.pack('<H', new_value)
        
        elif field_to_mutate == 'e_ehsize':
            # Mutate ELF header size
            new_value = random.randint(0, 0xFFFF)
            mutated[e_ehsize_offset:e_ehsize_offset+2] = struct.pack('<H', new_value)
        
        return bytes(mutated)
    
    def mutate_header_extreme_values(self, data):
        if len(data) < 0x40:  # min ELF header size
            return data
        
        mutated = bytearray(data)
        
        # Determine offsets based on ELF class
        if self.is_64bit:
            # 64-bit ELF
            e_phoff_offset = 0x20
            e_phnum_offset = 0x38
            e_ehsize_offset = 0x34
            phentsize_offset = 0x36
        else:
            # 32-bit ELF
            e_phoff_offset = 0x1C
            e_phnum_offset = 0x2C
            e_ehsize_offset = 0x28
            phentsize_offset = 0x2A
        
        # Randomly choose which field to mutate with extreme values
        field_to_mutate = random.choice(['e_phoff', 'e_phnum', 'e_ehsize', 'phentsize'])
        
        if field_to_mutate == 'e_phoff':
            # Set program header offset to extreme value
            extreme_value = random.choice(self.EXTREME_VALUES)
            if self.is_64bit:
                # 64-bit: 8 bytes
                mutated[e_phoff_offset:e_phoff_offset+8] = struct.pack('<Q', extreme_value & 0xFFFFFFFFFFFFFFFF)
            else:
                # 32-bit: 4 bytes
                mutated[e_phoff_offset:e_phoff_offset+4] = struct.pack('<I', extreme_value & 0xFFFFFFFF)
        
        elif field_to_mutate == 'e_phnum':
            # Set program header number to extreme value
            extreme_value = random.choice(self.EXTREME_VALUES) & 0xFFFF
            mutated[e_phnum_offset:e_phnum_offset+2] = struct.pack('<H', extreme_value)
        
        elif field_to_mutate == 'e_ehsize':
            # Set ELF header size to extreme value
            extreme_value = random.choice(self.EXTREME_VALUES) & 0xFFFF
            mutated[e_ehsize_offset:e_ehsize_offset+2] = struct.pack('<H', extreme_value)
        
        elif field_to_mutate == 'phentsize':
            # Set program header entry size to extreme value
            extreme_value = random.choice(self.EXTREME_VALUES) & 0xFFFF
            mutated[phentsize_offset:phentsize_offset+2] = struct.pack('<H', extreme_value)
        
        return bytes(mutated)
    
    def mutate_header_sizes(self, data):
        if len(data) < 0x40:  # Minimum ELF header size
            return data
        
        mutated = bytearray(data)
        
        # Determine offsets based on ELF class
        if self.is_64bit:
            # 64-bit ELF
            e_ehsize_offset = 0x34
            phentsize_offset = 0x36
            shentsize_offset = 0x3A
        else:
            # 32-bit ELF
            e_ehsize_offset = 0x28
            phentsize_offset = 0x2A
            shentsize_offset = 0x2E
        
        # Randomly choose which size field to mutate
        field_to_mutate = random.choice(['e_ehsize', 'phentsize', 'shentsize'])
        
        if field_to_mutate == 'e_ehsize':
            # Mutate ELF header size
            new_value = random.randint(0, 0xFFFF)
            mutated[e_ehsize_offset:e_ehsize_offset+2] = struct.pack('<H', new_value)
        
        elif field_to_mutate == 'phentsize':
            # Mutate program header entry size
            new_value = random.randint(0, 0xFFFF)
            mutated[phentsize_offset:phentsize_offset+2] = struct.pack('<H', new_value)
        
        elif field_to_mutate == 'shentsize':
            # Mutate section header entry size
            new_value = random.randint(0, 0xFFFF)
            mutated[shentsize_offset:shentsize_offset+2] = struct.pack('<H', new_value)
        
        return bytes(mutated)
    
    def delete_random_block(self, data):
        if len(data) <= 0x40:  # Need at least header size
            return data
        
        # Preserve the first 0x40 bytes (header)
        header = data[:0x40]
        body = data[0x40:]
        
        if len(body) < 2:
            return data
        
        # Randomly select a block to delete
        start = random.randint(0, len(body) - 1)
        end = random.randint(start + 1, len(body))
        
        # Delete the block
        new_body = body[:start] + body[end:]
        
        return header + new_body
    
    # Randomly selects bytes to corrupt 
    def corrupt_random_bytes(self, data):
        if len(data) < 5:   
            return data
        
        mutated = bytearray(data)

        num_bytes = random.randint(1, min(10, len(data) // 2))
        indices = random.sample(range(len(data)), num_bytes)
        
        for i in indices:
            corruption_type = random.choice(['bit_flip', 'random_byte', 'zero_byte'])
            
            if corruption_type == 'bit_flip':
                # Flip a random bit
                bit_pos = random.randint(0, 7)
                mutated[i] ^= (1 << bit_pos)
            elif corruption_type == 'random_byte':
                # Replace with a random byte
                mutated[i] = random.randint(0, 255)
            elif corruption_type == 'zero_byte':
                # Set to zero
                mutated[i] = 0
        
        return bytes(mutated)



