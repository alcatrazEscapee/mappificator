from parsers.abstract_parser import AbstractParser
from mapping import Mapping


class McpSrgParser(AbstractParser):

    def __init__(self, text: str):
        super().__init__(text)

        self.methods: Mapping.Method = {}
        self.fields: Mapping.Field = {}
        self.params: Mapping.Param = {}

        while not self.eof():
            notch_class = self.scan_identifier()
            self.scan(' ')
            srg_class = self.scan_identifier()
            self.scan('\n')
            while self.try_scan('\t'):
                notch_member = self.scan_identifier()
                self.scan(' ')
                if self.next() == '(':
                    params = self.scan_java_method_signature()
                    self.scan(' ')
                    srg_method = self.scan_identifier()
                    self.methods[(notch_class, notch_member, params)] = srg_method
                    for i in range(params):
                        self.params[(notch_class, notch_member, params, i)] = srg_method.replace('func', 'p') + '_' + str(i)
                else:
                    srg_field = self.scan_identifier()
                    self.fields[(notch_class, notch_member)] = srg_field
                self.scan('\n')
