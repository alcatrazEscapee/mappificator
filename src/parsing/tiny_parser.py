# A parser to handle .tiny files, used by both Fabric projects (Yarn, Intermediary) and Crane

from typing import Any

from util.mappings import Mappings
from util.parser import Parser


def parse_tiny(text: str) -> Mappings:
    parser = Parser(text)

    if parser.try_scan('tiny\t2\t0\t'):
        return parse_tiny_v2(parser)
    elif parser.try_scan('v1\t'):
        return parse_tiny_v1(parser)
    else:
        raise ValueError('Unknown tiny format')


def parse_tiny_v2(parser: Parser) -> Mappings:
    # tiny can technically represent a map from a source set to any number of named namespaces
    # with current tech, this would be rather difficult (and also unnecessary) to handle, so we don't try
    mappings = Mappings()

    parser.scan_identifier()  # the origin namespace
    if parser.next() == '\t':  # optional mapped namespace
        parser.scan('\t')
        parser.scan_identifier()
    parser.scan('\n')

    named_class = named_member = named_method = named_parameter = None
    while not parser.end():
        if parser.try_scan('c\t'):
            named_class = parse_tiny_class(parser, mappings)
        elif parser.try_scan('\tm\t'):
            if named_class is None:
                parser.error('Expected class before method')
            named_member = named_method = parse_tiny_method(parser, mappings, named_class)
        elif parser.try_scan('\tf\t'):
            if named_class is None:
                parser.error('Expected class before field')
            named_member = parse_tiny_field(parser, mappings, named_class)
        elif parser.try_scan('\t\tp\t'):
            if named_method is None:
                parser.error('Expected method before parameter')
            named_parameter = parse_tiny_v2_parameter(parser, mappings, named_class, named_method)
        elif parser.try_scan('\tc\t'):
            if named_class is None:
                parser.error('Expected class before class comment')
            doc = parser.scan_until('\n', include_end=False)
            named_class.docs += doc.encode('utf-8').decode('unicode_escape').split('\\n')
        elif parser.try_scan('\t\tc\t'):
            if named_member is None:
                parser.error('Expected method or field before member comment')
            parse_tiny_v2_comment(parser, named_member)
        elif parser.try_scan('\t\t\tc\t'):
            if named_parameter is None:
                parser.error('Expected parameter before parameter comment')
            parse_tiny_v2_comment(parser, named_parameter)
        else:
            parser.scan_until('\n')  # Tiny spec says to skip unrecognized lines

    return mappings


def parse_tiny_v1(parser: Parser) -> Mappings:
    mappings = Mappings()

    parser.scan_identifier()  # the origin namespace
    if parser.next() == '\t':  # optional mapped namespace
        parser.scan('\t')
        parser.scan_identifier()
    parser.scan('\n')

    while not parser.end():
        if parser.try_scan('CLASS\t'):
            parse_tiny_class(parser, mappings)
        elif parser.try_scan('FIELD\t'):
            clazz = parser.scan_identifier()
            parser.scan('\t')
            parse_tiny_field(parser, mappings, mappings.add_class(clazz))
        elif parser.try_scan('METHOD\t'):
            clazz = parser.scan_identifier()
            parser.scan('\t')
            parse_tiny_method(parser, mappings, mappings.add_class(clazz))
        else:
            parser.error('Unexpected line')

    return mappings


def parse_tiny_class(parser: Parser, mappings: Mappings) -> Mappings.Class:
    src_class = parser.scan_identifier()
    named_class = mappings.add_class(src_class)
    if parser.try_scan('\t'):
        named_class.mapped = parser.scan_identifier()
    parser.scan('\n')
    return named_class


def parse_tiny_method(parser: Parser, mappings: Mappings, named_class: Mappings.Class) -> Mappings.Method:
    desc = parser.scan_identifier()
    parser.scan('\t')
    name = parser.scan_identifier()
    named_method = mappings.add_method(named_class, name, desc)
    if parser.try_scan('\t'):
        named_method.mapped = parser.scan_identifier()
    parser.scan('\n')
    return named_method


def parse_tiny_field(parser: Parser, mappings: Mappings, named_class: Mappings.Class) -> Mappings.Field:
    desc = parser.scan_identifier()
    parser.scan('\t')
    name = parser.scan_identifier()
    named_field = mappings.add_field(named_class, name, desc)
    if parser.try_scan('\t'):
        named_field.mapped = parser.scan_identifier()
    parser.scan('\n')
    return named_field


def parse_tiny_v2_parameter(parser: Parser, mappings: Mappings, named_class: Mappings.Class, named_method: Mappings.Method) -> Mappings.Parameter:
    index = int(parser.scan_identifier(Parser.NUMERIC))
    named_parameter = mappings.add_parameter(named_class, named_method, index)
    if parser.try_scan('\t'):
        parser.try_scan('\t')  # yarn has two tabs before the parameter name?
        named_parameter.mapped = parser.scan_identifier()
    parser.scan('\n')
    return named_parameter


def parse_tiny_v2_comment(parser: Parser, member: Any):
    doc = parser.scan_until('\n', include_end=False)
    doc = doc.encode('utf-8').decode('unicode_escape')
    member.docs += doc.strip().split('\n')
