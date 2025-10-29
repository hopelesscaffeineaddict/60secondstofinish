import json
import io
import random
import threading 

from models import FormatType

# abstract base class which can be used as a template for other format-specific mutators (eg. csv, json, xml)
class BaseMutator(threading.Thread):
    def __init__(self, format_type, input, input_queue, stop_event, binary_name):
        super().__init__(daemon=True):
        self.input = input_filename
        self.input_queue = input_queue
        self.format_type = format_type 
        self.max_queue_size = 200

        # create mutated input dir if it doesn't exist
        curr_dir = os.getcwd()
        mutated_dir = f"../{curr_dir}/mutated_inputs"
        os.makedirs(mutated_dir, exist_ok=True)

        logfile_path = f"{mutated_dir}/mutated_{binary_name}.txt"
        self.log_file = open(logfile_path, "ab")
        self.log_file.write(f"example_input: {example_input}".encode())

        
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

                    # log mutation
                    self.log_file.write(f"{mutations_done}: ".encode() + b' '+ mutated_input + b'\n')
                    self.log_file.flush()

                except queue.Full:
                    pass
            else:
                # small sleep to allow queue to make space
                time.sleep(0.01)
            
        self.log_file.close()

    # this is a subclass thing
    def mutate(self):
        raise NotImplementedError("Subclasses to implement respective mutation methods")

    # log mutations
    def log_mutation(self, mutations_done, mutated_input)                    
        self.log_file.write(f"{mutations_done}: ".encode() + b' '+ mutated_input + b'\n')
        self.log_file.flush()