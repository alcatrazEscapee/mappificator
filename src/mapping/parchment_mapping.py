from typing import Dict, Tuple, List, Any, Callable, Set

from util import mapping_downloader, utils
from util.parser import Parser
from util.sources import SourceMap

MethodInheritanceTree = Dict[Tuple[str, str, str], Set[str]]  # (obf class, obf method, obf desc) -> { overriding obf classes }


class Parchment:
    class Field:
        def __init__(self, name: str, desc: str):
            self.name = name
            self.desc = desc
            self.docs: List[str] = []

        def __str__(self):
            return self.name

        def __eq__(self, other):
            return isinstance(other, Parchment.Field) and self.name == other.name and self.desc == other.desc

    class Parameter:
        def __init__(self, index: int):
            self.index = index
            self.name = ''
            self.doc = ''

        def __str__(self):
            return self.name + '[%d]' % self.index

        def __eq__(self, other):
            return isinstance(other, Parchment.Parameter) and self.index == other.index

    class Method:
        def __init__(self, name: str, desc: str):
            self.name = name
            self.desc = desc
            self.docs: List[str] = []
            self.params: List[Parchment.Parameter] = []

        def __str__(self):
            return self.name + self.desc

        def __eq__(self, other):
            return isinstance(other, Parchment.Method) and self.name == other.name and self.desc == other.desc

    class Package:
        def __init__(self, name: str):
            self.name = name
            self.docs: List[str] = []

        def __str__(self):
            return self.name

        def __eq__(self, other):
            return isinstance(other, Parchment.Package) and self.name == other.name

    class Class:
        def __init__(self, name: str):
            self.name = name
            self.simple_name = name[1 + name.rindex('/'):]
            self.docs: List[str] = []
            self.fields: Dict[Tuple[str, str], Parchment.Field] = {}
            self.methods: Dict[Tuple[str, str], Parchment.Method] = {}

        def __str__(self):
            return self.simple_name

        def __eq__(self, other):
            return isinstance(other, Parchment.Class) and self.name == other.name

    def __init__(self):
        self.packages: Dict[str, Parchment.Package] = {}
        self.classes: Dict[str, Parchment.Class] = {}
        self.fields: Dict[Tuple[str, str, str], Parchment.Field] = {}
        self.methods: Dict[Tuple[str, str, str], Parchment.Method] = {}
        self.parameters: Dict[Tuple[str, str, str, int], Parchment.Parameter] = {}

    def __str__(self):
        return 'Packages = %d, Classes = %d, Fields = %d, Methods = %d, Parameters = %d' % (len(self.packages), len(self.classes), len(self.fields), len(self.methods), len(self.parameters))

    def compare_to(self, other: 'Parchment') -> 'ParchmentComparison':
        return ParchmentComparison(self, other)

    def add_package(self, name: str) -> Package:
        if name not in self.packages:
            self.packages[name] = Parchment.Package(name)
        return self.packages[name]

    def add_class(self, name: str) -> Class:
        if name not in self.classes:
            c = Parchment.Class(name)
            self.classes[name] = c
            return c
        return self.classes[name]

    def add_field(self, clazz: Class, name: str, desc: str) -> Field:
        key = (clazz.name, name, desc)
        if key not in self.fields:
            f = Parchment.Field(name, desc)
            self.fields[key] = f
            clazz.fields[(name, desc)] = f
            return f
        return self.fields[key]

    def add_method(self, clazz: Class, name: str, desc: str) -> Method:
        key = (clazz.name, name, desc)
        if key not in self.methods:
            m = Parchment.Method(name, desc)
            self.methods[key] = m
            clazz.methods[(name, desc)] = m
            return m
        return self.methods[key]

    def add_parameter(self, clazz: Class, method: Method, index: int) -> Parameter:
        key = (clazz.name, method.name, method.desc, index)
        if key not in self.parameters:
            p = Parchment.Parameter(index)
            self.parameters[key] = p
            method.params.append(p)
            return p
        return self.parameters[key]

    def add_parameters_from_method(self, clazz: Class, method: Method, is_static: bool):
        _, param_types = Parser.decode_java_method_descriptor(method.desc)
        param_index = 0 if is_static else 1
        for param_type in param_types:
            param_key = (clazz.name, method.name, method.desc, param_index)
            p = Parchment.Parameter(param_index)
            method.params.append(p)
            self.parameters[param_key] = p
            if param_type in ('J', 'D'):
                param_index += 2
            else:
                param_index += 1


class ParchmentComparison:

    def __init__(self, left: Parchment, right: Parchment):
        self.left = left
        self.right = right
        self.left_only = apply_comparison(left, right, lambda l, r: l - r)
        self.right_only = apply_comparison(left, right, lambda l, r: r - l)
        self.union = apply_comparison(left, right, lambda l, r: l | r)
        self.intersect = apply_comparison(left, right, lambda l, r: l & r)


def apply_comparison(left: Parchment, right: Parchment, op: Callable[[Set, Set], Set]) -> Parchment:
    def apply(lhs: Dict, rhs: Dict):
        keys = op(set(lhs.keys()), set(rhs.keys()))
        return dict((k, (lhs[k] if k in lhs else rhs[k])) for k in keys)

    ret = Parchment()
    ret.packages = apply(left.packages, right.packages)
    ret.classes = apply(left.classes, right.classes)
    ret.fields = apply(left.fields, right.fields)
    ret.methods = apply(left.methods, right.methods)
    ret.parameters = apply(left.parameters, right.parameters)
    return ret


def read(mc_version: str, parchment_version: str) -> Tuple[SourceMap, Parchment, Parchment, MethodInheritanceTree]:
    blackstone = mapping_downloader.load_blackstone(mc_version)
    parchment = mapping_downloader.load_parchment(mc_version, parchment_version)

    obf_to_moj = SourceMap()
    full = Parchment()
    named = Parchment()
    method_inheritance = {}

    parse_blackstone(blackstone, obf_to_moj, full, method_inheritance)
    parse_parchment(parchment, named)

    return obf_to_moj, full, named, method_inheritance


def parse_blackstone(blackstone: Dict[str, Any], obf_to_moj: SourceMap, named: Parchment, method_inheritance: MethodInheritanceTree):
    b_classes = utils.or_else(blackstone, 'classes', [])
    for b_class in b_classes:
        parse_blackstone_class(b_class, obf_to_moj, named, method_inheritance)


def parse_blackstone_class(b_class: Dict[str, Any], obf_to_moj: SourceMap, named: Parchment, method_inheritance: MethodInheritanceTree):
    # Class and package
    obf_class = b_class['name']['obf']
    moj_class = b_class['name']['moj']
    obf_to_moj.classes[obf_class] = moj_class

    package = moj_class[:moj_class.rindex('/')]

    named.add_package(package)
    named_class = named.add_class(moj_class)

    # Inner classes
    b_inners = utils.or_else(b_class, 'inner', [])
    for b_inner in b_inners:
        parse_blackstone_class(b_inner, obf_to_moj, named, method_inheritance)

    # Fields
    b_fields = utils.or_else(b_class, 'fields', [])
    for b_field in b_fields:
        b_name = b_field['name']

        obf_field = b_name['obf']
        moj_field = b_name['moj']
        moj_desc = b_field['descriptor']['moj']

        obf_to_moj.fields[(obf_class, obf_field)] = moj_field
        named.add_field(named_class, moj_field, moj_desc)

    # Methods
    b_methods = utils.or_else(b_class, 'methods', [])
    primary_methods = {}
    missing_methods = {}
    for b_method in b_methods:
        b_name = b_method['name']
        key = b_name['obf'], b_method['descriptor']['obf']
        if 'moj' in b_name:
            # Normal method
            primary_methods[key] = b_method
        else:
            missing_methods[key] = b_method

    # Iterate methods again, now with the ability to match primary -> missing to restore access flags
    for key, b_method in primary_methods.items():
        obf_method, obf_desc = key

        access_flags = b_method['security']
        if key in missing_methods:
            assert access_flags == 0
            access_flags = missing_methods[key]['security']

        moj_method = b_method['name']['moj']
        moj_desc = b_method['descriptor']['moj']
        obf_to_moj.methods[(obf_class, obf_method, obf_desc)] = moj_method

        _, param_types = Parser.decode_java_method_descriptor(moj_desc)

        named_method = named.add_method(named_class, moj_method, moj_desc)
        named.add_parameters_from_method(named_class, named_method, (access_flags & Parser.ACC_STATIC) != 0)

        if 'overrides' in b_method:
            method_inheritance[(obf_class, obf_method, obf_desc)] = set(b_override['owner']['obf'] for b_override in b_method['overrides'])


def parse_parchment(parchment: Dict[str, Any], named: Parchment):
    # Packages
    p_packages = utils.or_else(parchment, 'packages', [])
    for p_package in p_packages:
        named_package = named.add_package(p_package['name'])
        named_package.docs += utils.or_else(p_package, 'javadoc', [])

    # Classes
    p_classes = utils.or_else(parchment, 'classes', [])
    for p_class in p_classes:
        named_class = named.add_class(p_class['name'])
        named_class.docs += utils.or_else(p_class, 'javadoc', [])

        # Fields
        p_fields = utils.or_else(p_class, 'fields', [])
        for p_field in p_fields:
            named_field = named.add_field(named_class, p_field['name'], p_field['descriptor'])
            named_field.docs += utils.or_else(p_field, 'javadoc', [])

        # Methods
        p_methods = utils.or_else(p_class, 'methods', [])
        for p_method in p_methods:
            named_method = named.add_method(named_class, p_method['name'], p_method['descriptor'])
            named_method.docs += utils.or_else(p_method, 'javadoc', [])

            p_parameters = utils.or_else(p_method, 'parameters', [])
            for p_parameter in p_parameters:
                named_parameter = named.add_parameter(named_class, named_method, p_parameter['index'])
                named_parameter.name = utils.or_else(p_parameter, 'name', '')
                named_parameter.doc = utils.or_else(p_parameter, 'javadoc', '')
