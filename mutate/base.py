import json
import io
import random
import queue
import time
import threading
import os

from format import FormatType

# abstract base class which can be used as a template for other format-specific mutators (eg. csv, json, xml)
class BaseMutator(threading.Thread):
    def __init__(self, input, input_queue, stop_event, binary_name, max_queue_size):
        super().__init__(daemon=True)
        self.input = input
        self.input_queue = input_queue
        self.random = random.Random()
        self.binary_name = binary_name
        self.mutations_done = 0
        self.executions_done = 0
        self.stop_event = stop_event
        self.max_queue_size = 200

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

                except queue.Full:
                    pass
            else:
                # small sleep to allow queue to make space
                time.sleep(0.01)

    # this is a subclass thing
    def mutate(self):
        raise NotImplementedError("Subclasses to implement respective mutation methods")
