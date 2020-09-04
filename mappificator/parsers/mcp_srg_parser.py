
import re

from mappificator.parsers.abstract_parser import AbstractParser


class McpSrgParser(AbstractParser):

    SRG_REGEX = re.compile('(^func_[0-9]+_[a-zA-Z_]+)|(^field_[0-9]+_[a-zA-Z_]+)|(^p_[\w]+_\d+_$)')

    def __init__(self, text: str):
        super().__init__(text)

        self.classes = {}
        self.methods = {}
        self.fields = {}
        self.params = {}

        while not self.eof():
            notch_class = self.scan_identifier()
            self.scan(' ')
            srg_class = self.scan_identifier()
            self.scan('\n')
            self.classes[notch_class] = srg_class
            while self.try_scan('\t'):
                notch_member = self.scan_identifier()
                self.scan(' ')
                if self.next() == '(':
                    params, amount = self.scan_java_method_signature()
                    self.scan(' ')
                    srg_method = self.scan_identifier()
                    self.methods[(notch_class, notch_member, params)] = srg_method
                    # Make a best effort guess at the params. Since we do not know if this is a static method, or the exact type of each argument, we cannot know the actual param indexes
                    for i in range(amount):
                        if srg_method.startswith('func_'):
                            srg_param = 'p_' + srg_method.split('_')[1] + '_' + str(i) + '_'
                        else:
                            srg_param = 'p_' + srg_method + '_' + str(i) + '_'
                        self.params[(notch_class, notch_member, params, i)] = srg_param
                else:
                    srg_field = self.scan_identifier()
                    self.fields[(notch_class, notch_member)] = srg_field
                self.scan('\n')
