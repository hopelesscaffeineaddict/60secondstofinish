import threading

class Mutator():
    def __init__(self):
        self.input_queue = []
        self.condition = threading.Condition()

    # TODO: in the mutator function, when an input is added to the input_queue, notify the condition
    def start(self):
        print("TODO")