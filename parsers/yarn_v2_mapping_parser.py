from parsers.abstract_parser import AbstractParser


class YarnV2MappingParser(AbstractParser):

    def __init__(self, text: str):
        super().__init__(text)

        self.methods = {}
        self.fields = {}
        self.classes = {}
        self.params = {}

        # skip the header line
        self.scan_until('\n')
        while not self.eof():
            if self.try_scan('c'):
                self.scan('\t')
                intermediary_clazz = self.scan_identifier()
                self.scan('\t')
                named_clazz = self.scan_identifier()
                self.scan('\n')
                self.classes[intermediary_clazz] = named_clazz
                while not self.eof():
                    if self.try_scan('\tm\t'):
                        params, intermediary_method, named_method = self.parse_mapping()
                        self.methods[intermediary_method] = named_method
                    elif self.try_scan('\tf\t'):
                        params, intermediary_field, named_field = self.parse_mapping()
                        self.fields[intermediary_field] = named_field
                    elif self.try_scan('\t\tp\t'):
                        index, named_param = self.parse_param()
                        self.params[intermediary_method + '_' + str(index)] = named_param
                    elif self.try_scan('\tc') or self.try_scan('\t\tc') or self.try_scan('\t\t\tc'):
                        self.scan_until('\n')
                    else:
                        break
            else:
                self.error('unknown')

    def parse_class(self):
        self.scan('\t')
        notch_class = self.scan_identifier()
        self.scan('\t')
        intermediary = self.scan_identifier()
        if self.try_scan('\t'):
            name = self.scan_identifier()
        else:
            name = intermediary
        self.scan('\n')
        return notch_class, intermediary, name

    def parse_mapping(self):
        params = self.scan_identifier()
        self.scan('\t')
        intermediary = self.scan_identifier()
        self.scan('\t')
        named = self.scan_identifier()
        self.scan('\n')
        return params, intermediary, named

    def parse_param(self):
        index = self.scan_identifier()
        self.scan('\t\t')
        named = self.scan_identifier()
        self.scan('\n')
        return index, named
