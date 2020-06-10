
from typing import Dict, Tuple, Optional, Set


class Mapping:

    Simple = Dict[str, str]
    Field = Dict[Tuple[str, str], str]
    Method = Dict[Tuple[str, str, str], str]
    Param = Dict[Tuple[str, str, str, int], str]

    def __init__(self, name: str, notch_fields: Set[Tuple[str, str]], mapped_fields: Field, notch_methods: Set[Tuple[str, str, str]], mapped_methods: Method, notch_params: Set[Tuple[str, str, str, str]], mapped_params: Param, notch_classes: Optional[Set[str]] = None, mapped_classes: Optional[Simple] = None):
        self.name = name
        self.notch_fields = notch_fields
        self.notch_methods = notch_methods
        self.mapped_fields = mapped_fields
        self.mapped_methods = mapped_methods
        self.notch_params = notch_params
        self.mapped_params = mapped_params
        self.notch_classes = notch_classes
        self.mapped_classes = mapped_classes

    def print_stats(self):
        print('\n--- Mapping: %s ---' % self.name)
        print('Fields: %d / %d (%2.2f%%)' % (len(self.mapped_fields), len(self.notch_fields), 100 * len(self.mapped_fields) / len(self.notch_fields)))
        print('Methods: %d / %d (%2.2f%%)' % (len(self.mapped_methods), len(self.notch_methods), 100 * len(self.mapped_methods) / len(self.notch_methods)))
        print('Params: %d / %d (%2.2f%%)' % (len(self.mapped_params), len(self.notch_params), 100 * len(self.mapped_params) / len(self.notch_params)))
        if self.notch_classes is not None:
            print('Classes: %d / %d (%2.2f%%)' % (len(self.mapped_classes), len(self.notch_classes), 100 * len(self.mapped_classes) / len(self.notch_classes)))

    @staticmethod
    def compare_and_print_stats(first: 'Mapping', second: 'Mapping'):
        first.print_stats()
        second.print_stats()

        print('\n--- Fields ---')
        unique_fields = len(set(first.mapped_fields.keys()) - set(second.mapped_fields.keys()))
        other_fields = len(set(second.mapped_fields.keys() - set(first.mapped_fields.keys())))
        both_fields = len(set(first.mapped_fields.keys()) | set(second.mapped_fields.keys()))

        print('Unique %s: %d (%2.2f%%)' % (first.name, unique_fields, 100 * unique_fields / len(first.notch_fields)))
        print('Unique %s: %d (%2.2f%%)' % (second.name, other_fields, 100 * other_fields / len(first.notch_fields)))
        print('Both: %d (%2.2f%%)' % (both_fields, 100 * both_fields / len(first.notch_fields)))
        print('Missing: %d (%2.2f%%)' % (len(first.notch_fields) - both_fields, 100 * (len(first.notch_fields) - both_fields) / len(first.notch_fields)))

        print('\n--- Methods ---')
        unique_methods = len(set(first.mapped_methods.keys()) - set(second.mapped_methods.keys()))
        other_methods = len(set(second.mapped_methods.keys() - set(first.mapped_methods.keys())))
        both_methods = len(set(first.mapped_methods.keys()) | set(second.mapped_methods.keys()))

        print('Unique %s: %d (%2.2f%%)' % (first.name, unique_methods, 100 * unique_methods / len(first.notch_methods)))
        print('Unique %s: %d (%2.2f%%)' % (second.name, other_methods, 100 * other_methods / len(first.notch_methods)))
        print('Both: %d (%2.2f%%)' % (both_methods, 100 * both_methods / len(first.notch_methods)))
        print('Missing: %d (%2.2f%%)' % (len(first.notch_methods) - both_methods, 100 * (len(first.notch_methods) - both_methods) / len(first.notch_methods)))

        print('\n--- Params ---')
        unique_params = len(set(first.mapped_params.keys()) - set(second.mapped_params.keys()))
        other_params = len(set(second.mapped_params.keys() - set(first.mapped_params.keys())))
        both_params = len(set(first.mapped_params.keys()) | set(second.mapped_params.keys()))

        print('Unique %s: %d (%2.2f%%)' % (first.name, unique_params, 100 * unique_params / len(first.notch_params)))
        print('Unique %s: %d (%2.2f%%)' % (second.name, other_params, 100 * other_params / len(first.notch_params)))
        print('Both: %d (%2.2f%%)' % (both_params, 100 * both_params / len(first.notch_params)))
        print('Missing: %d (%2.2f%%)' % (len(first.notch_params) - both_params, 100 * (len(first.notch_params) - both_params) / len(first.notch_params)))