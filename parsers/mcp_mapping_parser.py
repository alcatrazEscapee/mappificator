
from mapping import Mapping

import csv


class McpMappingParser:

    def __init__(self, text: str):
        self.mappings: Mapping.Simple = {}

        for row in csv.reader(text.split('\n')[1:]):
            if row:
                self.mappings[row[0]] = row[1]
