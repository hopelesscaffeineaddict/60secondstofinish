    # # randomly mutates fields (insert/duplicate/delete/replace content)
    # def mutate_field_value(self):
    #     if not self.data_rows:
    #         return self.original_content
            
    #     # Select a random row and column
    #     row_index = self.random.randint(0, len(self.data_rows) - 1)
    #     col_index = self.random.randint(0, len(self.data_rows[row_index]) - 1)
        
    #     # Choose a mutation strategy
    #     strategy = self.random.choice([
    #         "insert_character",
    #         "duplicate_content",
    #         # "delete_character",
    #         # "replace_character_with_special",
    #         # "insert_numeric_edge_cases",
    #         # "inject_whitespaces_in_field"
    #     ])
        
    #     # Get the original field value
    #     original_value = self.data_rows[row_index][col_index]
        
    #     # Apply the selected mutation strategy
    #     if strategy == 'insert_character':
    #         mutated_value = self.insert_characters(original_value)
    #     elif strategy == 'duplicate_content':
    #         mutated_value = self.duplicate_content(original_value)
    #     # elif strategy == 'delete_character':
    #     #     mutated_value = self.delete_character_from_field(original_value)
    #     # elif strategy == 'replace_character_with_special':
    #     #     mutated_value = self.replace_character_with_special(original_value)
    #     # elif strategy == 'insert_numeric_edge_cases':
    #     #     mutated_value = self.insert_numeric_edge_cases(original_value)
    #     # elif strategy == 'inject_whitespaces_in_field':
    #     #     mutated_value = self.inject_whitespaces_in_field(original_value)

    #     # Create a copy of the data rows and update the selected field
    #     mutated_rows = self.data_rows.copy()
    #     mutated_rows[row_index] = mutated_rows[row_index].copy()
    #     mutated_rows[row_index][col_index] = mutated_value
        
    #     # Reconstruct the full CSV
    #     if self.header:
    #         full_csv = [self.header] + mutated_rows
    #     else:
    #         full_csv = mutated_rows
            
    #     return self.serialise_csv(full_csv)