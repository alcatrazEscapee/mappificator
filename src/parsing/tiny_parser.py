# A parser to handle .tiny files, used by both Fabric projects (Yarn, Intermediary) and Crane

import re

from util.mappings import Mappings, Mappable
from util.parser import Parser


def parse_tiny(text: str) -> Mappings:
    parser = Parser(text)

    if parser.accept('tiny\t2\t0\t'):
        return parse_tiny_v2(parser)
    elif parser.accept('v1\t'):
        return parse_tiny_v1(parser)
    else:
        raise ValueError('Unknown tiny format')


def parse_tiny_v2(parser: Parser) -> Mappings:
    # tiny can technically represent a map from a source set to any number of named namespaces
    # with current tech, this would be rather difficult (and also unnecessary) to handle, so we don't try
    mappings = Mappings()

    parser.accept_identifier()  # the origin namespace
    if parser.peek() == '\t':  # optional mapped namespace
        parser.expect('\t')
        parser.accept_identifier()
    parser.expect('\n')

    named_class = named_member = named_method = named_parameter = None
    while not parser.end():
        if parser.accept('c\t'):
            named_class = parse_tiny_class(parser, mappings)
        elif parser.accept('\tm\t'):
            if named_class is None:
                parser.error('Expected class before method')
            named_member = named_method = parse_tiny_method(parser, mappings, named_class)
        elif parser.accept('\tf\t'):
            if named_class is None:
                parser.error('Expected class before field')
            named_member = parse_tiny_field(parser, mappings, named_class)
        elif parser.accept('\t\tp\t'):
            if named_method is None:
                parser.error('Expected method before parameter')
            named_parameter = parse_tiny_v2_parameter(parser, mappings, named_class, named_method)
        elif parser.accept('\tc\t'):
            if named_class is None:
                parser.error('Expected class before class comment')
            parse_tiny_v2_comment(parser, named_class)
        elif parser.accept('\t\tc\t'):
            if named_member is None:
                parser.error('Expected method or field before member comment')
            parse_tiny_v2_comment(parser, named_member)
        elif parser.accept('\t\t\tc\t'):
            if named_parameter is None:
                parser.error('Expected parameter before parameter comment')
            parse_tiny_v2_comment(parser, named_parameter)
        else:
            parser.accept_until_including('\n')  # Tiny spec says to skip unrecognized lines

    return mappings


def parse_tiny_v1(parser: Parser) -> Mappings:
    mappings = Mappings()

    parser.accept_identifier()  # the origin namespace
    if parser.peek() == '\t':  # optional mapped namespace
        parser.expect('\t')
        parser.accept_identifier()
    parser.expect('\n')

    while not parser.end():
        if parser.accept('CLASS\t'):
            parse_tiny_class(parser, mappings)
        elif parser.accept('FIELD\t'):
            clazz = parser.accept_identifier()
            parser.expect('\t')
            parse_tiny_field(parser, mappings, mappings.add_class(clazz))
        elif parser.accept('METHOD\t'):
            clazz = parser.accept_identifier()
            parser.expect('\t')
            parse_tiny_method(parser, mappings, mappings.add_class(clazz))
        else:
            parser.error('Unexpected line')

    return mappings


def parse_tiny_class(parser: Parser, mappings: Mappings) -> Mappings.Class:
    src_class = parser.accept_identifier()
    named_class = mappings.add_class(src_class)
    if parser.accept('\t'):
        named_class.mapped = parser.accept_identifier()
    parser.expect('\n')
    return named_class


def parse_tiny_method(parser: Parser, mappings: Mappings, named_class: Mappings.Class) -> Mappings.Method:
    desc = parser.accept_identifier()
    parser.expect('\t')
    name = parser.accept_identifier()
    named_method = mappings.add_method(named_class, name, desc)
    if parser.accept('\t'):
        named_method.mapped = parser.accept_identifier()
    parser.expect('\n')
    return named_method


def parse_tiny_field(parser: Parser, mappings: Mappings, named_class: Mappings.Class) -> Mappings.Field:
    desc = parser.accept_identifier()
    parser.expect('\t')
    name = parser.accept_identifier()
    named_field = mappings.add_field(named_class, name, desc)
    if parser.accept('\t'):
        named_field.mapped = parser.accept_identifier()
    parser.expect('\n')
    return named_field


def parse_tiny_v2_parameter(parser: Parser, mappings: Mappings, named_class: Mappings.Class, named_method: Mappings.Method) -> Mappings.Parameter:
    index = parser.accept_integer()
    named_parameter = mappings.add_parameter(named_class, named_method, index)
    if parser.accept('\t'):
        parser.accept('\t')  # yarn has two tabs before the parameter name?
        named_parameter.mapped = parser.accept_identifier()
    parser.expect('\n')
    return named_parameter


def parse_tiny_v2_comment(parser: Parser, member: Mappable):
    # Yarn's stance on newlines:
    # '\n' indicates a space
    # '\n\n' indicates a newline
    # '<p>' indicates a new paragraph (empty line)
    # Source: https://github.com/FabricMC/yarn/blob/1.17.1/CONVENTIONS.md
    doc = parser.accept_until('\n')
    doc = doc.encode('utf-8').decode('unicode_escape')  # convert raw \n sequences into actual newlines
    doc = doc.replace('\n\n', '<p>').replace('\n', ' ').replace('<p>', '\n')  # convert all tokens correctly
    doc = re.sub('\n+', '\n', doc)  # reduce unnecessary extra newlines
    member.docs += doc.split('\n')
