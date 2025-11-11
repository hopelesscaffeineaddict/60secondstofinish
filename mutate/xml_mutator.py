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
            # ET.dump(mutated_root)
            return ET.tostring(mutated_root, encoding='unicode')
        except Exception:
            print(f'[ERROR] mutation failed')
        
    # Structural mutations
    # - add _ sibling nodes
    # - add _ child nodes
    # - delete random node

    def add_siblings(self, root):
        """Adds a random number of sibling elements into the tree"""
        if isinstance(root, ET.Element):
            num = random.randint(1, 1000)
            for i in range(1, num):
                ET.SubElement(root, 'p')
        return root

    def add_children(self, root):
        """Adds a random number of child elements into the tree"""
        if isinstance(root, ET.Element):
            node = root
            num = random.randint(1, 1000)
            for i in range(1, num):
                child = ET.SubElement(node, 'p')
                node = child
        return root
    
    def delete_node(self, root):
        """Deletes a random node from the tree"""
        if isinstance(root, ET.Element):
            children = list(root)
            delete_child = random.choice(children)
            root.remove(delete_child)
        return root

    # URL/href/anchor tag mutations
    # - edit url
    #   - format string payload
    #   - xxs payload

    

    # Content mutations
    #   - add content
    #       - null bytes
    #       - control chars (\n, \t, etc)
    #       - payloads (xxs scripts, etc)
