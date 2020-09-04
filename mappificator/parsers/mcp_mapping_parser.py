import csv


class McpMappingParser:
    """ A parser for a single entry of an mcpbot export, one of fields.csv, methods.csv or params.csv """

    @staticmethod
    def write_mcp_mappings():
        pass

    def __init__(self, text: str):
        self.mappings = {}
        self.comments = {}

        for row in csv.reader(text.split('\n')[1:]):
            if row:
                self.mappings[row[0]] = row[1]
                if len(row) >= 4 and row[3] != '':
                    self.comments[row[0]] = row[3]
