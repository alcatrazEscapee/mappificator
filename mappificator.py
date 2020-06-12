# This is why we can't have nice things

from collections import defaultdict

import mapping_downloader

from parsers.mcp_mapping_parser import McpMappingParser
from parsers.mcp_srg_parser import McpSrgParser
from parsers.yarn_intermediary_parser import YarnIntermediaryParser
from parsers.yarn_v2_mapping_parser import YarnV2MappingParser

from source_map import SourceMap


def main():
    with open('./output.log', 'w') as f:
        methods, fields, params = mapping_downloader.load_mcp_mappings('1.15.1')
        methods, fields, params = McpMappingParser(methods), McpMappingParser(fields), McpMappingParser(params)
        mcp = SourceMap(fields.mappings, methods.mappings, params.mappings)

        srg = mapping_downloader.load_mcp_srg('1.15.2')
        srg = McpSrgParser(srg)
        srg = SourceMap(srg.fields, srg.methods, srg.params)

        intermediary = mapping_downloader.load_yarn_intermediary('1.16-pre4')
        intermediary = YarnIntermediaryParser(intermediary)
        intermediary = SourceMap(intermediary.fields, intermediary.methods, intermediary.params)

        yarn = mapping_downloader.load_yarn_v2('1.16-pre4')
        yarn = YarnV2MappingParser(yarn)
        yarn = SourceMap(yarn.fields, yarn.methods, yarn.params)

        fix_intermediary_inheritance(f, intermediary.methods, intermediary.params, srg.methods, srg.params, yarn.methods)
        srg_intermediary = map_srg_to_yarn(f, srg, intermediary, yarn)

        print('Notch -> Intermediary', intermediary)
        print('Notch -> SRG', srg)
        print('Intermediary -> Yarn', yarn)
        print('SRG -> MCP', mcp)

        print('Notch (Intermediary, SRG)', intermediary.keys(), srg.keys())
        print('Intermediary', intermediary.values())
        print('SRG', srg.values())

        print('SRG -> Intermediary', srg_intermediary)

        mixed = SourceMap.compose_layered([
            mcp,
            srg_intermediary.compose(yarn)
        ])
        srg_yarn = srg_intermediary.compose(yarn)

        print('Mixed MCP, Yarn', mixed)
        print('Srg -> Yarn', srg_yarn)

        print('MCP', mcp.compare_to(srg.values()))
        print('Mixed MCP, Yarn', mixed.compare_to(srg.values()))
        print('Yarn', srg_yarn.compare_to(srg.values()))


def fix_intermediary_inheritance(log_writer, intermediary_methods, intermediary_params, srg_methods, srg_params, yarn_methods):
    log_writer.write('### Fixing Intermediary Inheritance ###\n')

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
            log_writer.write('[Intermediary Inheritance Fix] No match: %s\n' % str(missing))
        else:
            # one reason why this happens: a method is overridden with a widened type
            # in this case we actually rely on the yarn mappings to detect if there are actual duplicates, as it won't compile otherwise
            if any(m not in yarn_methods for m in intermediary_matches):
                log_writer.write('[Intermediary Inheritance Fix] Multiple matches without yarn names for %s -> %s -> %s -> %s\n' % (missing, srg_methods[missing], matches, [intermediary_methods[m] for m in matches]))
            else:
                yarn = set(yarn_methods[m] for m in intermediary_matches)
                if len(yarn) == 1:
                    # pick a match at random
                    match = matches.pop()
                    intermediary_methods[missing] = intermediary_methods[match]
                    for i in range(srg_param_counts[missing]):
                        intermediary_params[(*missing, i)] = intermediary_methods[match] + '_' + str(i)
                    log_writer.write('[Intermediary Inheritance Fix] Multiple similar matches detected: %s -> %s -> %s -> %s. Choosing %s\n' % (missing, srg_methods[missing], matches, [intermediary_methods[m] for m in matches], match))
                else:
                    matches = list(matches)
                    log_writer.write('[Intermediary Inheritance Fix] Multiple distinct matches for %s -> %s -> %s -> %s -> %s\n' % (missing, srg_methods[missing], matches, [intermediary_methods[m] for m in matches], [yarn_methods[m] for m in intermediary_matches]))


def map_srg_to_yarn(log_writer, srg, intermediary, yarn):
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
                log_writer.write('[SRG -> Intermediary] No matches for %s %s -> %s\n' % (name, v, inverse_srg_map[v]))
            else:
                if any(m not in yarn_map for m in matches):
                    log_writer.write('[SRG -> Intermediary] Multiple matches without yarn names for %s %s -> %s -> %s\n' % (name, v, inverse_srg_map[v], matches))
                else:
                    yarn = set(yarn_map[m] for m in matches)
                    if len(yarn) == 1:
                        # pick a match at random
                        match = matches.pop()
                        mixed_map[v] = match
                    else:
                        log_writer.write('[SRG -> Intermediary] Multiple distinct matches without yarn names for %s %s -> %s -> %s\n' % (name, v, inverse_srg_map[v], matches))

    return SourceMap(*mixed_maps)


if __name__ == '__main__':
    main()
