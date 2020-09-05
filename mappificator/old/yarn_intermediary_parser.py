# todo: rewrite

import csv


class YarnIntermediaryParser:

    @staticmethod
    def count_params_from_method_signature(text: str) -> int:
        if text[0] != '(':
            raise ValueError('Invalid method signature: %s' % (repr(text)))
        pointer = 1
        params = 0
        while text[pointer] != ')':
            while text[pointer] == '[':  # array types
                pointer += 1
            if text[pointer] == 'L':  # object types
                while text[pointer] != ';':
                    pointer += 1
            pointer += 1
            params += 1
        if text[pointer] != ')':
            raise ValueError('Invalid method signature: %s at %d' % (repr(text), pointer))
        return params

    def __init__(self, text: str):

        self.methods = {}
        self.fields = {}
        self.classes = {}
        self.params = {}

        for row in csv.reader(text.split('\n')[1:], delimiter='\t'):
            if not row:  # skip empty lines
                continue
            if row[0] == 'CLASS':
                # notch name -> intermediary name
                self.classes[row[1]] = row[2]
            elif row[0] == 'FIELD':
                # notch class, notch field -> intermediary field
                self.fields[(row[1], row[3])] = row[4]
            elif row[0] == 'METHOD':
                # notch class, notch method, params -> intermediary method
                self.methods[(row[1], row[3], row[2])] = row[4]
                for i in range(self.count_params_from_method_signature(row[2])):
                    self.params[(row[1], row[3], row[2], i)] = row[4] + '_' + str(i)
