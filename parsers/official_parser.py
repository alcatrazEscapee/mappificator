from parsers.abstract_parser import AbstractParser


class OfficialParser(AbstractParser):

    def __init__(self, text: str):
        super().__init__(text)

        self.classes = {}
        self.methods = {}
        self.fields = {}

        # Skip comment lines (license text)
        while self.try_scan('#'):
            self.scan_until('\n')

        while not self.eof():
            # Class
            mojmap_class = self.scan_identifier()
            self.scan(' -> ')
            notch_class = self.scan_identifier()
            self.scan(':\n')

            self.classes[notch_class] = mojmap_class

            # Class members
            while self.try_scan('    '):
                if self.next() in AbstractParser.NUMERIC_CHARS:
                    # Method
                    # Skip two line number (?) identifiers
                    self.scan_until(':')
                    self.scan_until(':')
                    return_type = self.scan_identifier()
                    self.scan(' ')
                    mojmap_method = self.scan_until('(')[:-1]  # ignore the included '('
                    params = self.scan_until(')')[:-1].split(',')  # ignore the included ')', and split into a list of params
                    self.scan(' -> ')
                    notch_method = self.scan_identifier()
                    self.scan('\n')
                    return_desc = AbstractParser.convert_type_to_descriptor(return_type)
                    params_desc = [AbstractParser.convert_type_to_descriptor(p) for p in params]
                    method_desc = '(' + ''.join(params_desc) + ')' + return_desc
                    self.methods[(notch_class, notch_method, method_desc)] = mojmap_method
                else:
                    # Field
                    field_type = self.scan_identifier()
                    self.scan(' ')
                    mojmap_field = self.scan_identifier()
                    self.scan(' -> ')
                    notch_field = self.scan_identifier()
                    self.scan('\n')
                    self.fields[(notch_class, notch_field)] = mojmap_field
