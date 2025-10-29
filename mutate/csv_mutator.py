import csv
import io
import random

from .base import BaseMutator
from models import FormatType

class CSVMutator(BaseMutator):
    def __init__(self, input_file, input_queue, stop_event, binary_name, max_queue_size):
        super().__init__(input_file, input_queue, stop_event, binary_name, max_queue_size)

        self.parsed_csv = []
        self.data_rows = []
        self.header = None
        self.protected_header = False
        self.delimiter = ','
        self.quote_char = '"'
        self.original_content = None

    # chainable mutation function that applies n_mutations sequentially, building on the current state
    # each mutation is able to affect all rows/fields 
    def mutate(self, n_mutations=10):
        current_csv = self.parsed_csv.copy()
        for _ in range(n_mutations):
            mutation_type = self.random.choice(["field_mutation", "row_mutation"])
            if mutation_type == "field_mutation":
                current_csv = self._mutate_all_fields(current_csv)
            elif mutation_type == "row_mutation":
                current_csv = self._mutate_all_rows(current_csv)
        return self._serialize_csv(current_csv)

    # TODO: add a check for whether csv data is numeric and update __init__ accordingly
    # parse CSV structure and detect the delimiter, quotechar, header and header protection
    def parse_csv_structure(self):
        try:
            with open(self.input_file, "r", encoding="utf-8") as csv_file:
                self.original_content = csv_file.read()
            dialect = csv.Sniffer().sniff(self.original_content.split("\n")[0])
            self.delimiter = dialect.delimiter
            self.quote_char = dialect.quotechar
        except Exception:
            self.delimiter = ','
            self.quote_char = '"'

        # parse rows
        reader = csv.reader(self.original_content.splitlines(), delimiter=self.delimiter, quotechar=self.quote_char)
        self.parsed_csv = list(reader)

        # check if there's a header and if header is protected
        if self.parsed_csv:
            has_header = csv.Sniffer.has_header(parsed_csv)

            if has_header:
                self.header = self.parsed_csv[0]
                self.data_rows = self.parsed_csv[1:]

                if "keep" in self.header or "intact" in self.header:
                    self.protected_header = True 
            else:
                self.data_rows = self.parsed_csv

    # converts mutated input back into a CSV string
    def serialise_csv(self, csv_data):
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter, quotechar=self.quote_char)
        writer.writerows(csv_data)
        return output.getvalue()

    def mutate_all_fields(self, csv_data):
        mutated = []
        for row in csv_data:
            mutated_row = []
            for field in row:
                # Insert random number of chars for each field
                n_chars = self.random.randint(1, 5)
                mutated_field = field + ''.join(self.random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=n_chars))
                mutated_row.append(mutated_field)
            mutated.append(mutated_row)
        return mutated

    def mutate_all_rows(self, csv_data):
        mutated = []
        for row in csv_data:
            # Optionally duplicate, delete, or leave row
            action = self.random.choice(["duplicate", "keep", "delete"])
            if action == "duplicate":
                mutated.append(row)
            if action != "delete":
                mutated.append(row)
        return mutated

    # randomly mutates rows (insert/delete/duplicate)
    def mutate_rows(self):
        row_mutation_strategies = self.random.choice(
            ["insert_row",
            "duplicate_row", 
            "delete_row"]
        )

        if strategy == 'insert_row':
            return self.insert_row()
        elif strategy == 'duplicate_row':
            return self.duplicate_row()
        elif strategy == 'delete_row':
            return self.delete_row()

    # randomly mutates fields (insert_character/)
    def mutate_field_value(self):


    # insert a random number of (safe) characters into a field 
    def insert_character_in_field(self, field_value):
        n_insert = self.random.randint(10, 200)
        extra_chars = ''.join(self.random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=n_insert))
        return field_value + extra_chars

    # TODO: finish function that replaces field value with a random combination of escape sequence/encodings
    # def insert_special_characters_in_field(self, field_value)

    # TODO: finish function that replaces field value with a random numeric edge case from a set of edge cases
    # def insert_numeric_edge_cases(self, field_value):

    # TODO: need i say more lol
    # def duplicate_field_value(self, field_value):

    # TODO: inject whitespaces/tabs into field (start/end/both)
    # def inject_whitespaces_in_field(self, field_value):

    # insert a random row 
    def insert_row(self):
        if not self.data_rows:
            return self.original_content
        
        # count n_fields 
        n_fields = 0
        if len(self.data_rows[0]) > 0:
            n_fields = len(self.data_rows[0])
        
        # generate a new row with random values
        new_row = []
        for _ in range(n_fields):
            value_length = self.random.randint(5, 20)
            random_value = ''.join(self.random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=value_length))
            new_row.append(random_value)

        # insert new row in a random position
        mutated_rows = self.data_rows.copy()
        insert_position = self.random.randint(0, len(mutated_rows))
        mutated_rows.insert(insert_position, new_row)
        
        # reconstruct full CSV 
        if self.header:
            full_csv = [self.header] + mutated_rows
        else:
            full_csv = mutated_rows
            
        return self.serialize_csv(full_csv)

    # duplicate a random row 
    def duplicate_row(self):
        row_to_dupe = self.random.choice(self.data_rows)
        mutated_rows = self.data_rows.copy()

        # insert duplicate at a random position
        insert_position = self.random.randint(0, len(mutated_rows))
        mutated_rows.insert(insert_position, row_to_dupe)

        # reconstruct full CSV
        if self.header:
            full_csv = [self.header] + mutated_rows
        else:
            full_csv = mutated_rows
        
        return self.serialise_csv(full_csv)

    # delete a random row from CSV
    def delete_row(self):
        # make sure there's at least 1 row before continuing 
        if len(self.data_rows) <= 1:
            return self.original_content
            
        # select a random row
        row_to_delete = self.random.randint(0, len(self.data_rows) - 1)
        
        # create copy of data rows and remove the selected row
        mutated_rows = self.data_rows.copy()
        del mutated_rows[row_to_delete]
        
        # reconstruct full CSV
        if self.header:
            full_csv = [self.header] + mutated_rows
        else:
            full_csv = mutated_rows
            
        return self.serialize_csv(full_csv)

        


