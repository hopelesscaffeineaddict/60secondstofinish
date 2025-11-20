import random
import os
from .base import BaseMutator

class JPGMutator(BaseMutator):
    def __init__(self, input_file, input_queue, stop_event, binary_name, max_queue_size):
        super().__init__(input_file, input_queue, stop_event, binary_name, max_queue_size)

        self.magic_1byte = [b'\\x00', b'\\x7F', b'\\xFF']

        self.magic_2bytes = [b'\\x00\\x00', b'\\x7F\\xFF', b'\\xFF\\xFF']

        self.magic_4bytes = [b'\\x00\\x00\\x00\\x00', b'\\x40\\x00\\x00\\x00', b'\\x7F\\xFF\\xFF\\xFF', b'\\x80\\x00\\x00\\x00', b'\\xFF\\xFF\\xFF\\xFF']

        self.segments = {
            'SOI': b'\\xFF\\xD8',
            'APP0': b'\\xFF\\xE0',
            'DQT': b'\\xFF\\xDB',
            'SOF': b'\\xFF\\xC0',
            'DHT': b'\\xFF\\xC4',
            'EOI': b'\\xFF\\xD9',
        }

        self.SOF_fields_length = {
            # value = (offset_from_marker, field length)
            'length': (0x2, 2),
            'height': (0x5, 2),
            'width': (0x7, 2),
            'components': (0x9, 1),
        }

        self.APP0_fields_length = {

            'length': (0x2, 2),
            'identifier': (0x4, 5),
            'version': (0x9, 2),
            'density': (0xB, 1),
        }

        self.DQT_fields_length = {
            'length': (0x2, 2),
            'precision': (0x4, 1),
            'first_element': (0x5, 1),
        }

        self.DHT_fields_length = {
            'length': (0x2, 2),
            'class': (0x4, 1),
            # only changing first byte of huffman code length/values
            'code_length': (0x5, 1),
            'code_values': (0x15, 1),
        }

    def mutate(self):
        # if not byte string, use empty input
        if isinstance(self.input, bytes):
            data = self.input
        else:
            data = b''
        
        strategy = random.choice([
            self.modify_SOI,
            self.modify_APP0,
            self.modify_DQT,
            self.modify_SOF,
            self.modify_DHT,
            self.modify_EOI,
        ])
    
        try:
            mutated_data = strategy(data)
            return mutated_data
        except Exception:
            print(f'[ERROR] mutation failed')
            return data
        
# SOI - Start of image
    def modify_SOI(self, data):
        """Modify Start of Image marker or change its location"""
        choice = random.choice(['modify', 'move'])
        if choice == 'modify':
            bytes = random.choice(self.magic_2bytes)
            new = bytes + data[2:]
            return new
        else:
            pos = random.randrange(len(data) + 1)
            return data[2:pos] + b'\\xFF\\xD8' + data[pos:]
    
# APP0 - Application Markers
    def modify_APP0(self, data):
        """Change fields in the JFIF APP0 marker segment"""
        field = random.choice(['length', 'identifier', 'version', 'density'])
        field_values = self.APP0_fields_length[field]
        offset = 0x2 + field_values[0]
        if field_values[1] == 2:
            bytes = random.choice(self.magic_2bytes)
        elif field_values[1] == 1:
            bytes = random.choice(self.magic_1byte)
        else:
            bytes = os.urandom(field_values[1])

        return data[:offset] + bytes + data[offset + field_values[1]:]


# DQT - Quantization Tables
    def modify_DQT(self, data):
        """Modify fields in the DQT"""
        index = data.find(self.segments['DQT'])
        field = random.choice(['length', 'precision', 'first_element'])
        field_values = self.DQT_fields_length[field]
        offset = index + field_values[0]
        if field_values[1] == 2:
            bytes = random.choice(self.magic_2bytes)
        else:
            bytes = random.choice(self.magic_1byte)

        return data[:offset] + bytes + data[offset + field_values[1]:]

# SOF - Start of frame
    def modify_SOF(self, data):
        """Modify fields in the SOF segment"""
        index = data.find(self.segments['SOF'])
        field = random.choice(['length', 'height', 'width', 'components'])
        field_values = self.SOF_fields_length[field]
        offset = index + field_values[0]
        if field_values[1] == 2:
            bytes = random.choice(self.magic_2bytes)
        else:
            bytes = random.choice(self.magic_1byte)

        return data[:offset] + bytes + data[offset + field_values[1]:]

# DHT - Huffman Tables
    def modify_DHT(self, data):
        """Modify fields in the DHT segment"""
        index = data.find(self.segments['DHT'])
        field = random.choice(['length', 'class', 'code_length', 'code_values'])
        field_values = self.DHT_fields_length[field]
        offset = index + field_values[0]
        if field_values[1] == 2:
            bytes = random.choice(self.magic_2bytes)
        else:
            bytes = random.choice(self.magic_1byte)

        return data[:offset] + bytes + data[offset + field_values[1]:]
    
# EOI - End of image
    def modify_EOI(self, data):
        """Modify End of Image marker or change its location"""
        choice = random.choice(['modify', 'move'])
        if choice == 'modify':
            bytes = random.choice(self.magic_2bytes)
            return bytes + data[2:]
        else:
            pos = random.randrange(len(data) + 1)
            return data[:pos] + b'\\xFF\\xD9' + data[pos:2]