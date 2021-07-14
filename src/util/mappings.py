from typing import Dict, Tuple, Optional, List

from util import utils


class Mappings:
    """
    A comprehensive representation of a set of mappings

    This encapsulates two distinct concepts:
    - A source set, which represents raw metadata about the classes, methods, and fields in a class
    - A set of mappings, which are simply names and docs that are added to the metadata

    Taken together, the source set can be completely remapped under the mappings.
    For example:
    - A field consists of a tuple (class name, field name, descriptor)
    - A remapped field consists of a tuple (remap(class name), mapped name, remap(descriptor))
    Where remap() is a function using the class mappings to convert one name to another
    """

    packages: Dict[str, 'Mappings.Package']
    classes: Dict[str, 'Mappings.Class']
    fields: Dict[Tuple[str, str, str], 'Mappings.Field']
    methods: Dict[Tuple[str, str, str], 'Mappings.Method']
    parameters: Dict[Tuple[str, str, str, int], 'Mappings.Parameter']

    class Package:
        name: str
        docs: List[str]

        def __init__(self, name: str):
            self.name = name
            self.docs = []

        def __str__(self):
            return 'package %s' % self.name

    class Class:
        name: str
        mapped: Optional[str]
        docs: List[str]
        fields: Dict[Tuple[str, str], 'Mappings.Field']
        methods: Dict[Tuple[str, str], 'Mappings.Method']

        def __init__(self, name: str):
            self.name = name
            self.mapped = None
            self.docs = []
            self.fields = {}
            self.methods = {}

        def __str__(self):
            return 'class %s%s' % (self.name, ' -> ' + self.mapped if self.mapped else '')

    class Field:
        name: str
        desc: str
        mapped: Optional[str]
        docs: List[str]

        def __init__(self, name: str, desc: str):
            self.name = name
            self.desc = desc
            self.mapped = None
            self.docs = []

        def __str__(self):
            return 'field %s %s%s' % (self.name, self.desc, ' -> ' + self.mapped if self.mapped else '')

    class Method:
        name: str
        desc: str
        mapped: Optional[str]
        docs: List[str]
        parameters: Dict[int, 'Mappings.Parameter']
        is_lambda: Optional[bool]

        def __init__(self, name: str, desc: str):
            self.name = name
            self.desc = desc
            self.mapped = None
            self.docs = []
            self.parameters = {}
            self.is_lambda = None

        def __str__(self):
            return 'method %s %s%s' % (self.name, self.desc, ' -> ' + self.mapped if self.mapped else '')

    class Parameter:
        index: int
        desc: str
        mapped: Optional[str]
        docs: List[str]

        def __init__(self, index: int):
            self.index = index
            self.mapped = None
            self.docs = []

        def __str__(self):
            return 'param %d%s' % (self.index, ' -> ' + self.mapped if self.mapped else '')

    def __init__(self):
        self.packages = {}
        self.classes = {}
        self.fields = {}
        self.methods = {}
        self.parameters = {}

    def __str__(self):
        return 'Mappings {Packages=%d, Classes=%d, Fields=%d, Methods=%d, Parameters=%d}' % (len(self.packages), len(self.classes), len(self.fields), len(self.methods), len(self.parameters))

    def add_package(self, name: str) -> 'Mappings.Package':
        if name in self.packages:
            return self.packages[name]

        p = Mappings.Package(name)
        self.packages[name] = p
        return p

    def add_class(self, name: str) -> 'Mappings.Class':
        if name in self.classes:
            return self.classes[name]

        c = Mappings.Class(name)
        self.classes[name] = c
        return c

    def add_field(self, clazz: 'Mappings.Class', name: str, desc: str) -> 'Mappings.Field':
        self.require_owned_class(clazz)

        key = clazz.name, name, desc
        if key in self.fields:
            return self.fields[key]

        f = Mappings.Field(name, desc)
        self.fields[key] = f
        clazz.fields[(name, desc)] = f
        return f

    def add_method(self, clazz: 'Mappings.Class', name: str, desc: str) -> 'Mappings.Method':
        self.require_owned_class(clazz)

        key = clazz.name, name, desc
        if key in self.methods:
            return self.methods[key]

        m = Mappings.Method(name, desc)
        self.methods[key] = m
        clazz.methods[(name, desc)] = m
        return m

    def add_parameter(self, clazz: 'Mappings.Class', method: 'Mappings.Method', index: int) -> 'Mappings.Parameter':
        self.require_owned_class_and_method(clazz, method)

        key = clazz.name, method.name, method.desc, index
        if key in self.parameters:
            return self.parameters[key]

        p = Mappings.Parameter(index)
        self.parameters[key] = p
        method.parameters[index] = p
        return p

    def add_parameters_from_method(self, clazz: 'Mappings.Class', method: 'Mappings.Method', is_static: bool):
        self.require_owned_class_and_method(clazz, method)

        _, param_types = utils.split_method_descriptor(method.desc)
        param_index = 0 if is_static else 1
        for param_type in param_types:
            param_key = (clazz.name, method.name, method.desc, param_index)
            p = Mappings.Parameter(param_index)
            p.desc = param_type
            method.parameters[param_index] = p
            self.parameters[param_key] = p
            if param_type == 'J' or param_type == 'D':
                param_index += 2
            else:
                param_index += 1

    # Mapping Transformations

    def remap(self, invert_namespaces: bool = False) -> 'Mappings':
        """
        Creates a new Mappings, representing the mapped source set of this Mappings.
        - Packages are dropped
        - Classes are remapped to the mapped namespace and dropped if not present
        - Methods and fields are remapped (including descriptors) to the mapped namespace
        - Parameters are copied but their mappings are dropped
        """
        mappings = Mappings()
        class_mappings = dict((k, c.mapped) for k, c in self.classes.items() if c.mapped)
        for clazz in self.classes.values():
            if clazz.mapped:
                mapped_class = mappings.add_class(clazz.mapped)
                if invert_namespaces:
                    mapped_class.mapped = clazz.name

                for field in clazz.fields.values():
                    if field.mapped:
                        mapped_field = mappings.add_field(mapped_class, field.mapped, utils.remap_descriptor(field.desc, class_mappings))
                        if invert_namespaces:
                            mapped_field.mapped = field.name

                for method in clazz.methods.values():
                    if method.mapped:
                        mapped_method = mappings.add_method(mapped_class, method.mapped, utils.remap_method_descriptor(method.desc, class_mappings))
                        if invert_namespaces:
                            mapped_method.mapped = method.name

                        for param in method.parameters.values():
                            mapped_parameter = mappings.add_parameter(mapped_class, mapped_method, param.index)
                            mapped_parameter.desc = utils.or_else(class_mappings, param.desc, param.desc)

        return mappings

    def invert(self) -> 'Mappings':
        """
        Creates a new Mappings, representing a the inverse of this mappings to the original source set
        - Packages are dropped
        - Classes, methods, and fields are inverted from mapped to the original namespace
        - Parameters are copied but their mappings are dropped
        """
        return self.remap(invert_namespaces=True)

    def compose(self, other: 'Mappings') -> 'Mappings':
        """
        Composes another mapping set from this mappings. The source set stays the same but mapped names are remapped
        - Packages are dropped
        - Classes, methods, and fields are included if they are present in both mappings, and mapped from the original source set to the other mappings
        - Parameters are copied but their mappings are only included from the other mappings
        """
        mappings = Mappings()

        # We need to compute a class map from the default source set -> named
        # This is used to remap descriptors, as they are used to query the other mapping set as keys (and then discarded)
        class_mappings = dict((k, c.mapped) for k, c in self.classes.items() if c.mapped)

        for clazz in self.classes.values():
            other_class = utils.or_else(other.classes, clazz.mapped)
            if other_class:
                mapped_class = mappings.add_class(clazz.name)
                mapped_class.mapped = other_class.mapped
                mapped_class.docs += other_class.docs

                for field in clazz.fields.values():
                    if field.mapped:
                        key = field.mapped, utils.remap_descriptor(field.desc, class_mappings)
                        other_field = utils.or_else(other_class.fields, key)
                        if other_field:
                            mapped_field = mappings.add_field(mapped_class, field.name, field.desc)
                            mapped_field.mapped = other_field.mapped
                            mapped_field.docs += other_field.docs

                for method in clazz.methods.values():
                    if method.mapped:
                        key = method.mapped, utils.remap_method_descriptor(method.desc, class_mappings)
                        other_method = utils.or_else(other_class.methods, key)
                        if other_method:
                            mapped_method = mappings.add_method(mapped_class, method.name, method.desc)
                            mapped_method.mapped = other_method.mapped
                            mapped_method.docs += other_method.docs

                            for other_param in other_method.parameters.values():
                                mapped_param = mappings.add_parameter(mapped_class, mapped_method, other_param.index)
                                mapped_param.mapped = other_param.mapped
                                mapped_param.docs += other_param.docs
        return mappings

    def inherit_domain(self, other: 'Mappings'):
        """
        Modifies the current mappings object
        Any mappings from the other source set, which do NOT exist in the current mapping, are appended to the current mappings as an identity mapping.
        """
        for other_class in other.classes.values():
            mapped_class = self.add_class(other_class.name)
            if not mapped_class.mapped:
                mapped_class.mapped = other_class.name

            for other_field in other_class.fields.values():
                mapped_field = self.add_field(mapped_class, other_field.name, other_field.desc)
                if not mapped_field.mapped:
                    mapped_field.mapped = other_field.name

            for other_method in other_class.methods.values():
                mapped_method = self.add_method(mapped_class, other_method.name, other_method.desc)
                if not mapped_method.mapped:
                    mapped_method.mapped = other_method.name

    def require_owned_class(self, clazz: 'Mappings.Class'):
        if clazz.name not in self.classes or self.classes[clazz.name] != clazz:
            raise ValueError('Class %s is not owned by mappings')

    def require_owned_class_and_method(self, clazz: 'Mappings.Class', method: 'Mappings.Method'):
        self.require_owned_class(clazz)

        method_key = clazz.name, method.name, method.desc
        if method_key not in self.methods or self.methods[method_key] != method:
            raise ValueError('Method %s is not owned by mappings')
