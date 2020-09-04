from mappificator.parsers.abstract_parser import AbstractParser


class OfficialParser(AbstractParser):

    def __init__(self, text: str):
        super().__init__(text)

        self.classes = {}
        self.methods = {}
        self.fields = {}
        self.params = {}

        temp_methods = {}  # during parsing these will be stored with mojang names, they need to be converted to notch identifiers

        # Skip comment lines (license text)
        while self.try_scan('#'):
            self.scan_until('\n')

        while not self.eof():
            # Class
            mojmap_class = self.scan_identifier().replace('.', '/')
            self.scan(' -> ')
            notch_class = self.scan_identifier().replace('.', '/')
            self.scan(':\n')

            self.classes[notch_class] = mojmap_class

            # Class members
            while self.try_scan('    '):
                if self.next() in AbstractParser.NUMERIC_CHARS:
                    # Ignore these - they seem to be line numbers?
                    self.scan_until(':')
                    self.scan_until(':')

                member_type = self.scan_identifier().replace('.', '/')
                self.scan(' ')
                mojmap_member = self.scan_identifier().replace('.', '/')
                self.scan(' -> ')
                notch_member = self.scan_identifier().replace('.', '/')
                self.scan('\n')

                if mojmap_member.endswith(')'):
                    # Method
                    mojmap_method, params = mojmap_member.split('(')  # Extract the method name and params
                    params = params[:-1]  # Remove the last end bracket
                    params = params.split(',')  # Split params
                    if params == ['']:  # Skip empty param lists from splitting
                        params = []
                    params = tuple(params)  # Replace package names with '/'

                    # Ignore constructors / static init blocks
                    if notch_member != '<clinit>' and notch_member != '<init>':
                        temp_methods[(notch_class, notch_member, member_type, tuple(params))] = mojmap_method

                else:
                    # Field
                    self.fields[(notch_class, notch_member)] = mojmap_member

        mojmap_to_notch_classes = dict((mojmap, notch) for notch, mojmap in self.classes.items())

        for method, mojmap_method in temp_methods.items():
            notch_class, notch_method, return_type, params = method
            return_desc = AbstractParser.convert_type_to_descriptor(return_type, mojmap_to_notch_classes)
            params_desc = []
            for p in params:
                params_desc.append(AbstractParser.convert_type_to_descriptor(p, mojmap_to_notch_classes))
            method_desc = '(' + ''.join(params_desc) + ')' + return_desc
            self.methods[(notch_class, notch_method, method_desc)] = mojmap_method
