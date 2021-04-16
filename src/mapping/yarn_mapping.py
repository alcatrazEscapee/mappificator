from typing import Tuple, Optional

from util import mapping_downloader
from util.parser import Parser
from util.sources import SourceMap


def read(mc_version: str, yarn_version: Optional[str] = None) -> Tuple[SourceMap, SourceMap]:
    yarn_v2 = mapping_downloader.load_yarn_v2(mc_version, yarn_version)
    return parse_yarn_v2(yarn_v2)


def parse_yarn_v2(text: str) -> Tuple[SourceMap, SourceMap]:
    parser = Parser(text)

    mappings = SourceMap()
    comments = SourceMap()

    # skip the header line
    parser.scan_until('\n')
    while not parser.eof():
        if parser.try_scan('c'):
            parser.scan('\t')
            intermediary_clazz = parser.scan_identifier()
            parser.scan('\t')
            named_clazz = parser.scan_identifier()
            parser.scan('\n')
            mappings.classes[intermediary_clazz] = named_clazz
            intermediary_method = intermediary_method_desc = None
            param_index = 0
            while not parser.eof():
                if parser.try_scan('\tm\t'):
                    intermediary_method_desc, intermediary_method, named_method = parse_mapping(parser)
                    mappings.methods[intermediary_method] = named_method
                elif parser.try_scan('\tf\t'):
                    _, intermediary_field, named_field = parse_mapping(parser)
                    mappings.fields[intermediary_field] = named_field
                elif parser.try_scan('\t\tp\t'):
                    param_index, named_param = parse_param(parser)
                    param_index = int(param_index)
                    if intermediary_method == '<init>':  # constructors need to be identified via class and descriptor
                        mappings.params[(intermediary_clazz, intermediary_method_desc, '<init>', param_index)] = named_param
                    else:
                        mappings.params[(intermediary_method, param_index)] = named_param
                elif parser.try_scan('\tc\t'):
                    comment = parser.scan_until('\n')
                    comments.classes[intermediary_clazz] = comment
                elif parser.try_scan('\t\tc\t'):
                    comment = parser.scan_until('\n')
                    comments.methods[intermediary_method] = comment
                elif parser.try_scan('\t\t\tc\t'):
                    comment = parser.scan_until('\n')
                    comments.params[(intermediary_method, param_index)] = comment
                else:
                    break
        else:
            parser.error('unknown')

    return mappings, comments


def parse_class(parser: Parser) -> Tuple[str, str, str]:
    parser.scan('\t')
    notch_class = parser.scan_identifier()
    parser.scan('\t')
    intermediary = parser.scan_identifier()
    if parser.try_scan('\t'):
        name = parser.scan_identifier()
    else:
        name = intermediary
    parser.scan('\n')
    return notch_class, intermediary, name


def parse_mapping(parser: Parser) -> Tuple[str, str, str]:
    params = parser.scan_identifier()
    parser.scan('\t')
    intermediary = parser.scan_identifier()
    parser.scan('\t')
    named = parser.scan_identifier()
    parser.scan('\n')
    return params, intermediary, named


def parse_param(parser: Parser) -> Tuple[str, str]:
    index = parser.scan_identifier()
    parser.scan('\t\t')
    named = parser.scan_identifier()
    parser.scan('\n')
    return index, named
