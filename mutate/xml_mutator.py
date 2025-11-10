import xml.etree.ElementTree as ET
import io
import random
import queue
import time

from .base import BaseMutator
from format import FormatType

class XMLMutator(BaseMutator):
    def __init__(self, input_file, input_queue, stop_event, binary_name, max_queue_size):
        super().__init__(input_file, input_queue, stop_event, binary_name, max_queue_size)

    def mutate(self):
        # handle xml inputs
        try:
            if isinstance(self.input, bytes):
                root = ET.fromstring(self.input.decode('utf-8'))
            else:
                root = ET.fromstring(self.input)
        except (ET.ParseError, UnicodeDecodeError):
            # if input not valid XML, log error
            print(f'[ERROR] input is not valid XML')
            return
        
        strategy = random.choice([
            # add mutations here
        ])

        try:
            mutated_root = strategy(root)
            # always return bytes 
            return ET.tostring(mutated_root, encoding='unicode')
        except Exception:
            # fallback to base mutation if mutation fails
            print(f'[ERROR] mutation failed')
        
    # def 

    # Structural mutations
    # - add _ sibling nodes
    # - add _ child nodes
    # - delete leaf node

    # URL/href/anchor tag mutations
    # - edit url
    #   - format string payload
    #   - xxs payload

    # Content mutations
    #   - add content
    #       - null bytes
    #       - control chars (\n, \t, etc)
    #       - payloads (xxs scripts, etc)
