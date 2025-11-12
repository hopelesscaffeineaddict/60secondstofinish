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
        # self.format_type = format_type 
        self.stop_event = stop_event
        self.max_queue_size = 200

        # create mutated input dir if it doesn't exist
        base_dir = os.path.abspath(os.getcwd())
        mutated_dir = os.path.join(base_dir, "mutated_inputs")
        print(f'[DEBUG]: mutated dir: {mutated_dir}')
        os.makedirs(mutated_dir, exist_ok=True)

        # create output dir for execution logs 
        output_dir = os.path.join(base_dir, "fuzzer_output")
        print(f'[DEBUG]: fuzzer output dir: {output_dir}')
        os.makedirs(output_dir, exist_ok=True)

        # setup mutation log file 
        logfile_path = os.path.join(mutated_dir, f"mutated_{binary_name}.txt")
        print(f'[DEBUG]: mutation log path: {logfile_path}')
        self.log_file = open(logfile_path, "wb")
        # self.log_file.write(f"example_input: {input}".encode())
        self.log_file.write(f"Mutation log for {binary_name}\n".encode('utf-8'))
        self.log_file.write(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n".encode('utf-8'))


        # setup execution log file 
        output_path = os.path.join(output_dir, f"{binary_name}_execution_log.txt")
        print(f'[DEBUG]: exec log path: {output_path}')
        self.exec_log_file = open(output_path, "w")
        self.exec_log_file.write(f"Execution log for {binary_name}\n")
        self.exec_log_file.write(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

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
                    self.log_mutation(self.mutations_done, mutated_input)

                except queue.Full:
                    pass
            else:
                # small sleep to allow queue to make space
                time.sleep(0.01)
            
        if self.log_file:
            self.log_file.close()
        if self.exec_log_file:
            self.exec_log_file.close()

    # this is a subclass thing
    def mutate(self):
        raise NotImplementedError("Subclasses to implement respective mutation methods")

    # log mutations for diff input types
    def log_mutation(self, mutations_done, mutated_input):
        if isinstance(mutated_input, bytes):
            # hex for binary data
            log_content = f"{mutations_done}: {mutated_input.hex()}\n"
        elif isinstance(mutated_input, str):
            #  directly log string inputs
            log_content = f"{mutations_done}: {mutated_input}\n"
        else:
            # anyth else: conv to strings
            log_content = f"{mutations_done}: {str(mutated_input)}\n"

        self.log_file.write(log_content.encode('utf-8'))
        self.log_file.flush()

    
    # log stderr/stdout output
    def log_execution(self, input_data, result):
        if self.exec_log_file and not self.exec_log_file.closed:
                self.executions_done += 1
                self.exec_log_file.write(f"Execution #{self.executions_done}\n")
                
                # diff input types for logging
                if isinstance(input_data, bytes):
                    input_repr = input_data.hex()
                elif isinstance(input_data, str):
                    input_repr = input_data
                else:
                    input_repr = str(input_data)
                
                if len(input_repr) > 100:
                    input_repr = input_repr[:100] + '...'
                
                self.exec_log_file.write(f"Input: {input_repr}\n")
                self.exec_log_file.write(f"Return Code: {result.return_code}\n")

                if result.crashed:
                    self.exec_log_file.write(f"Crash Type: {result.crash_type.value if result.crash_type else 'Unknown'}\n")
                
                self.exec_log_file.write("\n--- STDOUT ---\n")
                stdout_text = result.stdout.decode('utf-8', errors='ignore')
                self.exec_log_file.write(stdout_text)
                
                self.exec_log_file.write("\n--- STDERR ---\n")
                stderr_text = result.stderr.decode('utf-8', errors='ignore')
                self.exec_log_file.write(stderr_text)
                
                self.exec_log_file.write("\n" + "="*50 + "\n\n")
                self.exec_log_file.flush()