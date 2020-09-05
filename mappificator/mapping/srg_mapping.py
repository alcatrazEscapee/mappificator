from typing import Dict, Tuple, Set, FrozenSet

from mappificator.util import mapping_downloader
from mappificator.util.parser import Parser
from mappificator.util.source_map import SourceMap


def read(mc_version: str) -> Tuple[SourceMap, Set[FrozenSet]]:
    joined, static_methods, constructors = mapping_downloader.download_mcp_srg(mc_version)

    classes, methods, fields = parse_mcpconfig_joined_tsrg(joined)
    static_methods = parse_mcpconfig_static_methods(static_methods)
    constructors = parse_mcpconfig_constructors(constructors)

    params, grouped_params = generate_srg_params(methods, static_methods, constructors)

    return SourceMap(fields, methods, params, classes), grouped_params


def parse_mcpconfig_joined_tsrg(srg_joined: str) -> Tuple[Dict, Dict, Dict]:
    """
    Parse joined.tsrg into a mapping of classes, methods and fields

    """
    classes = {}
    methods = {}
    fields = {}
    parser = Parser(srg_joined)

    while not parser.eof():
        notch_class = parser.scan_identifier()
        parser.scan(' ')
        srg_class = parser.scan_identifier()
        parser.scan('\n')
        classes[notch_class] = srg_class
        while parser.try_scan('\t'):
            notch_member = parser.scan_identifier()
            parser.scan(' ')
            if parser.next() == '(':
                _, _, desc = parser.scan_java_method_descriptor()
                parser.scan(' ')
                srg_method = parser.scan_identifier()
                methods[(notch_class, notch_member, desc)] = srg_method
            else:
                srg_field = parser.scan_identifier()
                fields[(notch_class, notch_member)] = srg_field
            parser.scan('\n')

    return classes, methods, fields


def parse_mcpconfig_static_methods(srg_static_methods: str) -> Set:
    static_methods = set()
    parser = Parser(srg_static_methods)
    while not parser.eof():
        srg_method = parser.scan_identifier()
        parser.scan('\n')
        static_methods.add(srg_method)

    return static_methods


def parse_mcpconfig_constructors(srg_constructors: str) -> Dict:
    constructors: Dict = {}
    parser = Parser(srg_constructors)
    while not parser.eof():
        srg_id = int(parser.scan_identifier())
        parser.scan(' ')
        srg_class = parser.scan_identifier()
        parser.scan(' ')
        _, _, desc = parser.scan_java_method_descriptor()
        parser.scan('\n')

        constructors[(srg_class, '<init>', desc)] = srg_id

    return constructors


def generate_srg_params(methods: Dict, static_methods: Set, constructors: Dict) -> Tuple[Dict, Set[FrozenSet]]:
    """
    Generate srg named parameters by looking through method and constructors

    """
    params = {}
    grouped_params = set()
    for method, srg_method in methods.items():
        group = set()
        notch_class, notch_method, method_desc = method
        _, param_types = Parser.decode_java_method_descriptor(method_desc)

        param_index = 0
        if srg_method not in static_methods:
            param_index += 1

        for param_type in param_types:
            if srg_method.startswith('func_'):
                srg_id = srg_method.split('_')[1]
            else:
                srg_id = srg_method
            srg_param = 'p_' + srg_id + '_' + str(param_index) + '_'
            params[(notch_class, notch_method, method_desc, param_index)] = srg_param
            group.add((srg_param, param_type))
            if param_type in ('J', 'D'):
                param_index += 2
            else:
                param_index += 1

        grouped_params.add(frozenset(group))

    for method, srg_id in constructors.items():
        group = set()
        notch_class, _, method_desc = method
        _, param_types = Parser.decode_java_method_descriptor(method_desc)

        param_index = 1
        for param_type in param_types:
            srg_param = 'p_i' + str(srg_id) + '_' + str(param_index) + '_'
            params[(notch_class, '<init>', method_desc, param_index)] = srg_param
            group.add((srg_param, param_type))
            if param_type in ('J', 'D'):
                param_index += 2
            else:
                param_index += 1

        grouped_params.add(frozenset(group))

    return params, grouped_params
