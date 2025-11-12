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

        self.str_payloads = {
            "format_str": "%100c%100$n",
            "xss": "javascript:alert(1)",
            "large_str": "A" * 2000,
            # control chars
            "null": "\0",
            "backspace": "\b",
            "tab": "\t",
            "new_line": "\n",
            "carriage_ret": "\r",
        }

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
            self.add_node,
            self.add_children,
            self.delete_node,
            self.edit_url,
            self.edit_content
        ])

        try:
            mutated_root = strategy(root)
            # new_mutation = ET.dump(mutated_root)
            new_mutation = ET.tostring(mutated_root, encoding='utf-8')
            # print(type(new_mutation))
            return new_mutation
        except Exception:
            print(f'[ERROR] mutation failed')
            return ET.tostring(root, encoding='utf-8')
        
    # Structural mutations
    # - add _ sibling nodes
    # - add _ child nodes
    # - delete random node

    def add_node(self, root):
        """Adds a random number of nodes to root"""
        if isinstance(root, ET.Element):
            num = random.randint(1, 1000)
            for i in range(1, num):
                ET.SubElement(root, 'p')
        return root

    def add_children(self, root, max_depth=random.randint(1, 500)):
        """Recursively adds a random number of child elements to root"""
        if not isinstance(root, ET.Element) or max_depth <= 0:
            return
        
        child = ET.SubElement(root, 'p')
        self.add_children(child, max_depth - 1)
        return root
    
    def delete_node(self, root):
        """Deletes a random node from the tree"""
        if isinstance(root, ET.Element):
            # get all nodes and delete root from the children list
            children = list(root.iter())
            children.remove(root)
            if not children:
                return root
            
            delete_child = random.choice(children)
            for subtree in root.iter():
                if delete_child in subtree:
                    subtree.remove(delete_child)
        return root

    # URL/href/anchor tag mutations
    # - edit url
    #   - format string payload
    #   - xxs payload

    def edit_url(self, root):
        """Edits the URL within an anchor tag"""
        if isinstance(root, ET.Element):
            payloads = list(self.str_payloads.values())

            for node in root.iter():
                for anchor in node.findall('a'):
                    if anchor.get('href'):
                        payload = random.choice(payloads)
                        anchor.set('href', payload)
        return root

    # Content mutations
    #   - add content
    #       - null bytes
    #       - control chars (\n, \t, etc)
    #       - payloads (xxs scripts, etc)

    def edit_content(self, root):
        """Edits the content of a random node"""
        if isinstance(root, ET.Element):
            elements = list(root.iter())
            element = random.choice(elements)
            payloads = list(self.str_payloads.values())
            element.text = random.choice(payloads)
        return root
