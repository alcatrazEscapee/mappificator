# This is why we can't have nice things

from collections import defaultdict
from typing import Dict

import logging
import mapping_downloader

from parsers.mcp_mapping_parser import McpMappingParser
from parsers.mcp_srg_parser import McpSrgParser
from parsers.yarn_intermediary_parser import YarnIntermediaryParser
from parsers.yarn_v2_mapping_parser import YarnV2MappingParser
from parsers.official_parser import OfficialParser

from source_map import SourceMap


def main():
    logging.basicConfig(filename='logs/output.log', level=logging.INFO, filemode='w')

    print('Reading mappings...\n')

    methods_raw, fields_raw, params_raw = mapping_downloader.load_mcp_mappings('1.16.1', '20200723')
    methods_parser, fields_parser, params_parser = McpMappingParser(methods_raw), McpMappingParser(fields_raw), McpMappingParser(params_raw)
    mcp = SourceMap(fields_parser.mappings, methods_parser.mappings, params_parser.mappings)

    methods_raw, fields_raw, params_raw = mapping_downloader.load_yarn2mcp_mappings('1.16.2', '20200830')
    methods_parser, fields_parser, params_parser = McpMappingParser(methods_raw), McpMappingParser(fields_raw), McpMappingParser(params_raw)
    yarn2mcp = SourceMap(fields_parser.mappings, methods_parser.mappings, params_parser.mappings)

    methods_raw, fields_raw, params_raw = mapping_downloader.load_yarn2mcp_mappings('1.16.2', '20200830', 'yarn')
    methods_parser, fields_parser, params_parser = McpMappingParser(methods_raw), McpMappingParser(fields_raw), McpMappingParser(params_raw)
    yarn2mcp_yarn = SourceMap(fields_parser.mappings, methods_parser.mappings, params_parser.mappings)

    srg_raw = mapping_downloader.load_mcp_srg('1.16.2')
    srg_parser = McpSrgParser(srg_raw)
    srg = SourceMap(srg_parser.fields, srg_parser.methods, srg_parser.params)

    intermediary_raw = mapping_downloader.load_yarn_intermediary('1.16.2')
    intermediary_parser = YarnIntermediaryParser(intermediary_raw)
    intermediary = SourceMap(intermediary_parser.fields, intermediary_parser.methods, intermediary_parser.params)

    yarn_raw = mapping_downloader.load_yarn_v2('1.16.2')
    yarn_parser = YarnV2MappingParser(yarn_raw)
    yarn = SourceMap(yarn_parser.fields, yarn_parser.methods, yarn_parser.params)

    client, server = mapping_downloader.load_official('1.16.2')
    client_parser, server_parser = OfficialParser(client), OfficialParser(server)
    official_client, official_server = SourceMap(client_parser.fields, client_parser.methods), SourceMap(server_parser.fields, server_parser.methods)

    print('Fixing Intermediary Inheritance')
    fix_intermediary_inheritance(intermediary.methods, intermediary.params, srg.methods, srg.params, yarn.methods)
    srg_intermediary = map_srg_to_yarn(srg, intermediary, yarn)

    print('\nResults\n')

    print('Notch -> Official (Client)', official_client)
    print('Notch -> Official (Server)', official_server)
    print('Notch -> Intermediary', intermediary)
    print('Notch -> SRG', srg)
    print('Intermediary -> Yarn', yarn)
    print('SRG -> MCP', mcp)
    print('SRG -> Yarn2Mcp (Mixed)', yarn2mcp)
    print('SRG -> Yarn2Mcp (Yarn)', yarn2mcp_yarn)

    print('Notch (Intermediary, SRG)', intermediary.keys(), srg.keys())
    print('Intermediary', intermediary.values())
    print('SRG', srg.values())

    print('SRG -> Intermediary', srg_intermediary)

    mixed = SourceMap.compose_layered([
        mcp,
        srg_intermediary.compose(yarn)
    ])

    print('Mixed MCP, Yarn', mixed)

    print('MCP', mcp.compare_to(srg.values()))
    print('Yarn', yarn.compare_to(srg.values()))
    print('Mixed MCP, Yarn', mixed.compare_to(srg.values()))
    print('Yarn2Mcp (Mixed)', yarn2mcp.compare_to(srg.values()))
    print('Yarn2Mcp (Yarn)', yarn2mcp_yarn.compare_to(srg.values()))


def fix_intermediary_inheritance(intermediary_methods: Dict, intermediary_params: Dict, srg_methods: Dict, srg_params: Dict, yarn_methods: Dict):
    logging.info('### Fixing Intermediary Inheritance ###')

    # build an inverse srg map
    inverse_srg_methods = defaultdict(list)
    for k, v in srg_methods.items():
        inverse_srg_methods[v].append(k)

    # and build a map of parameter counts
    srg_param_counts = defaultdict(int)
    for srg in srg_params.keys():
        srg_param_counts[tuple(srg[0:3])] += 1

    # Identify methods that are missing from yarn
    missing_methods = set(srg_methods.keys()) - set(intermediary_methods.keys())
    for missing in missing_methods:
        # identify matching notch / srg names
        matches = inverse_srg_methods[srg_methods[missing]]
        matches = [match for match in matches if match in intermediary_methods]
        intermediary_matches = [intermediary_methods[m] for m in matches]
        unique_intermediary_matches = len(set(intermediary_matches))
        if unique_intermediary_matches == 1:
            match = matches.pop()
            intermediary_methods[missing] = intermediary_methods[match]
            for i in range(srg_param_counts[missing]):
                intermediary_params[(*missing, i)] = intermediary_methods[match] + '_' + str(i)
        elif unique_intermediary_matches == 0:
            logging.info('[Intermediary Inheritance Fix] No match: %s' % str(missing))
        else:
            # one reason why this happens: a method is overridden with a widened type
            # in this case we actually rely on the yarn mappings to detect if there are actual duplicates, as it won't compile otherwise
            if any(m not in yarn_methods for m in intermediary_matches):
                logging.info('[Intermediary Inheritance Fix] Multiple matches without yarn names for %s -> %s -> %s -> %s' % (missing, srg_methods[missing], matches, [intermediary_methods[m] for m in matches]))
            else:
                yarn = set(yarn_methods[m] for m in intermediary_matches)
                if len(yarn) == 1:
                    # pick a match at random
                    match = matches.pop()
                    intermediary_methods[missing] = intermediary_methods[match]
                    for i in range(srg_param_counts[missing]):
                        intermediary_params[(*missing, i)] = intermediary_methods[match] + '_' + str(i)
                    logging.info('[Intermediary Inheritance Fix] Multiple similar matches detected: %s -> %s -> %s -> %s. Choosing %s' % (missing, srg_methods[missing], matches, [intermediary_methods[m] for m in matches], match))
                else:
                    matches = list(matches)
                    logging.info('[Intermediary Inheritance Fix] Multiple distinct matches for %s -> %s -> %s -> %s -> %s' % (missing, srg_methods[missing], matches, [intermediary_methods[m] for m in matches], [yarn_methods[m] for m in intermediary_matches]))


def map_srg_to_yarn(srg: SourceMap, intermediary: SourceMap, yarn: SourceMap):
    # Iterate through each map type
    mixed_maps = [dict(), dict(), dict()]
    names = ['fields', 'methods', 'params']
    for srg_map, intermediary_map, yarn_map, mixed_map, name in zip(srg.maps(), intermediary.maps(), yarn.maps(), mixed_maps, names):
        # Inverse srg
        inverse_srg_map = defaultdict(list)
        for k, v in srg_map.items():
            inverse_srg_map[v].append(k)

        for v in set(srg_map.values()):
            matches = [intermediary_map[k] for k in inverse_srg_map[v] if k in intermediary_map]
            unique_matches = len(set(matches))
            if unique_matches == 1:
                match = matches.pop()
                mixed_map[v] = match
            elif unique_matches == 0:
                logging.info('[SRG -> Intermediary] No matches for %s %s -> %s' % (name, v, inverse_srg_map[v]))
            else:
                if any(m not in yarn_map for m in matches):
                    logging.info('[SRG -> Intermediary] Multiple matches without yarn names for %s %s -> %s -> %s' % (name, v, inverse_srg_map[v], matches))
                else:
                    yarn = set(yarn_map[m] for m in matches)
                    if len(yarn) == 1:
                        # pick a match at random
                        match = matches.pop()
                        mixed_map[v] = match
                    else:
                        logging.info('[SRG -> Intermediary] Multiple distinct matches without yarn names for %s %s -> %s -> %s' % (name, v, inverse_srg_map[v], matches))

    return SourceMap(*mixed_maps)


if __name__ == '__main__':
    main()
