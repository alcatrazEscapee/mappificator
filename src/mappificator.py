# This is why we can't have nice things

import re
from typing import Dict, Tuple, List, Set, Any

from mapping import official_mapping, intermediary_mapping, yarn_mapping, parchment_mapping
from mapping.parchment_mapping import Parchment
from util import utils, mapping_downloader
from util.parser import Parser
from util.sources import SourceMap, SourceSetComparison

CLI_HELP = """
This is an interface similar to K9 used to reverse engineer mapped names. It will read the mapping log file and can show information about all mapped items, search, and filter based on input commands.
A command consists of a space separated list of elements, which each either produce a set of results, or act upon the previous (current) results. At the end of the statement, the results will be displayed.
Commands:
> help      - print this menu
> exit      - exits the CLI
> nc <name> - lists [n]otch [c]lass names matching <name>
> c <name>  - lists srg [c]lass names matching <name>
> m <name>  - lists named [m]ethods matching <name>
> f <name>  - lists named [f]ields matching <name>
> p <name>  - lists named [p]arams matching <name>
> fc <name> - [f]ilters the results (methods, fields, or params) by the [c]lass <name>
> fm <name> - [f]ilters the results (params) by the [m]ethod <name>
> [ <num>   - only includes a single entry, at index <num> of the previous results
> gm        - [g]ets all [m]ethods from the first class of the previous results
> gp        - [g]ets all [p]arameters from the first method of the previous results
> max <num> - include up to <num> entries in the output (default 10)
"""


def main():
    """ Entry point and argument parser """

    mc_version = '1.17'
    yarn_version = '9'
    parchment_version = '2021.07.04-nightly-SNAPSHOT'

    # mojmap, mojmap_lambdas = official_mapping.read('1.17')
    obf_to_moj, full, parchment, method_inheritance = parchment_mapping.read(mc_version, parchment_version)

    # mojmap_v_blackstone = mojmap.keys().compare_to(obf_to_moj.keys())
    # full_v_named = full.compare_to(named)

    intermediary = intermediary_mapping.read(mc_version)
    yarn, yarn_comments = yarn_mapping.read(mc_version, yarn_version)

    moj_v_intermediary = obf_to_moj.keys().compare_to(intermediary.keys())

    intermediary_methods = dict(intermediary.methods)
    for method in obf_to_moj.methods.keys():
        if method not in intermediary.methods and method in method_inheritance:
            obf_class, obf_method, obf_desc = method
            for override_obf_class in method_inheritance[method]:
                key = override_obf_class, obf_method, obf_desc
                if key in intermediary.methods:
                    intermediary_methods[method] = intermediary.methods[key]
                    break

    intermediary.methods = intermediary_methods
    moj_v_intermediary_fixed = obf_to_moj.keys().compare_to(intermediary.keys())

    print('Done')


def create_merged_mappings(named: Parchment, parchment: Parchment, intermediary: SourceMap, yarn: SourceMap, yarn_docs: SourceMap):
    # Copy package level docs from parchment
    for key, named_package in named.packages.items():
        if key in parchment.packages:
            named_package.docs += parchment.packages[key].docs

    # Copy class level docs from parchment, and optionally apply yarn docs and comments
    for key, named_class in named.classes.items():
        if key in parchment.classes:
            parchment_class = parchment.classes[key]
            named_class.docs += parchment_class.docs
        if key in intermediary.classes:
            intermediary_class = intermediary.classes[key]
            docs = ['']
            if intermediary_class in yarn.classes:
                docs.append('Yarn: {@code %s}' % yarn.classes[intermediary.classes[key]])
            if intermediary_class in yarn_docs.classes:
                docs.append(list(yarn_docs.classes[intermediary_class].split('\n')))


"""
    parser = argparse.ArgumentParser(description='A collection of bodging scripts to work with Minecraft mappings and alleviate suffering.')

    parser.add_argument('--cli', action='store_true', dest='cli', help='Run the CLI for mapping reverse engineering.')
    parser.add_argument('--version', type=str, default=None, help='Sets the version of the exported mappings.')

    # Mapping sources
    parser.add_argument('--include-yarn', action='store_true', dest='include_yarn', help='If the exported mappings should source Fabric Yarn mappings for parameter names in addition to method, field, and parameter comments')
    parser.add_argument('--include-mapping-comments', action='store_true', dest='include_mapping_comments', help='If the exported mappings should include auto-generated comments on every method and field, identifying the method in alternative (srg, intermediary, mcp, and yarn) mapping systems.')

    # Individual versions
    parser.add_argument('--mc-version', type=str, default='1.16.5', help='The Minecraft version used to download official mappings, and MCP Config')
    parser.add_argument('--mcp-version', type=str, default='1.16.5', help='The Minecraft version used to download mcp mappings')
    parser.add_argument('--mcp-date', type=str, default='20210309', help='The snapshot date for the mcp mappings')
    parser.add_argument('--intermediary-version', type=str, default='1.16.5', help='The Minecraft version used to download Fabric Intermediary, and Yarn mappings')
    parser.add_argument('--yarn-version', type=str, default='6', help='The build number used for Fabric Yarn mappings')

    args = parser.parse_args()
    version = args.version  # Dynamically assign a version if one was not already
    if version is None:
        version = 'complete-%s-%s' % (args.mc_version, args.mcp_date)
        if args.include_yarn:
            version += '-yarn%s' % args.yarn_version
        if args.include_mapping_comments:
            version += '-c'

    if args.cli:
        cli(version)
    else:
        make(args.include_yarn, args.include_mapping_comments, version, args.mc_version, args.mcp_version, args.mcp_date, args.intermediary_version, args.yarn_version)
        print('MCP Export Built. Version = \'%s\'' % version)
"""


def make(include_yarn: bool, include_mapping_comments: bool, version: str, mc_version: str, mcp_version: str, mcp_date: str, intermediary_version: str, yarn_version: str):
    print('Reading mappings...')

    mojmap, mojmap_lambdas = official_mapping.read(mc_version)
    srg, srg_indexed_params, srg_reverse_constructors = srg_mapping.read(mc_version)
    mcp, mcp_comments = mcp_mapping.read(mcp_version, mcp_date)

    if include_yarn:
        intermediary = intermediary_mapping.read(intermediary_version)
        yarn, yarn_comments = yarn_mapping.read(intermediary_version, yarn_version)

    manual_mappings = mapping_downloader.load_corrections(mc_version)

    print('Validating mappings...')

    # Validate srg is a subset of official (classes, methods, and fields)
    mojmap_v_srg = mojmap.keys().compare_to(srg.keys())
    assert not mojmap_v_srg.right_only.classes
    assert not mojmap_v_srg.right_only.methods
    assert not mojmap_v_srg.right_only.fields

    # Filter out mcp names which are not used in this mc version
    mcp = mcp.filter_keys(srg.values())
    srg_v_mcp = srg.values().compare_to(mcp.keys())
    assert srg_v_mcp.right_only.is_empty()

    # Map srg -> official
    temp = SourceMap(fields=srg.fields, methods=srg.methods)  # notch -> srg (methods / fields)
    temp = temp.inverse()  # srg -> notch (fuzzy, methods / fields)
    temp = temp.compose(mojmap)  # srg -> official (fuzzy, methods / fields)
    result = temp.select()  # srg -> official (methods / fields)

    # Load srg -> intermediary and create yarn param and comment maps
    if include_yarn:
        srg_to_intermediary = map_srg_to_intermediary(srg, srg_reverse_constructors, intermediary)
        srg_to_yarn = srg_to_intermediary.compose(yarn, True)
        srg_to_yarn_comments = srg_to_intermediary.compose(yarn_comments, True)
    else:
        srg_to_yarn, srg_to_yarn_comments = SourceMap(), SourceMap()

    # Procedurally generate the rest of the parameters, watching for conflicts with each other.
    generate_param_names(srg, srg_indexed_params, mcp, srg_to_yarn, manual_mappings, mojmap_lambdas, result)

    print('=== Mappings ===')
    print_compare(srg.values().compare_to(result.keys()))

    # Comments
    comments = SourceMap()

    # MCP Comments
    utils.append_mapping(comments.fields, mcp_comments.fields)
    utils.append_mapping(comments.methods, mcp_comments.methods)

    if include_yarn:
        append_comments(comments.fields, srg_to_yarn_comments.fields)
        append_comments(comments.methods, srg_to_yarn_comments.methods)

    print('=== Comments ===')
    print_compare(srg.values().compare_to(comments.keys()))

    if include_mapping_comments:
        if include_yarn:
            append_mapping_comments(comments.fields, ('mcp', mcp.fields), ('intermediary', srg_to_intermediary.fields), ('yarn', srg_to_yarn.fields))
            append_mapping_comments(comments.methods, ('mcp', mcp.methods), ('intermediary', srg_to_intermediary.methods), ('yarn', srg_to_yarn.methods))
        else:
            append_mapping_comments(comments.fields, ('mcp', mcp.fields))
            append_mapping_comments(comments.methods, ('mcp', mcp.methods))

    # Write reverse lookup log output
    write_reverse_lookup_log(version, srg, result)

    # Write mcp mappings
    mcp_mapping.write(version, result, comments.fields, comments.methods)
    mcp_mapping.publish(version)


def print_compare(compare: SourceSetComparison):
    print('Fields: %d / %d (%.2f%%)' % (len(compare.intersect.fields), len(compare.left.fields), 100 * len(compare.intersect.fields) / len(compare.left.fields)))
    print('Methods: %d / %d (%.2f%%)' % (len(compare.intersect.methods), len(compare.left.methods), 100 * len(compare.intersect.methods) / len(compare.left.methods)))
    print('Params: %d / %d (%.2f%%)' % (len(compare.intersect.params), len(compare.left.params), 100 * len(compare.intersect.params) / len(compare.left.params)))


def map_srg_to_intermediary(srg: SourceMap, srg_reverse_constructors: Dict[int, Tuple[str, List[str]]], intermediary: SourceMap) -> SourceMap:
    srg_v_intermediary = srg.keys().compare_to(intermediary.keys())
    assert not srg_v_intermediary.right_only.classes  # intermediary classes are a subset of srg classes

    # Filter legacy srg classes
    extra_srg_classes = srg_v_intermediary.left_only.classes
    print('Removing %d legacy srg classes: %s' % (len(extra_srg_classes), str(sorted(extra_srg_classes))))

    def filter_classes(k, _):
        if isinstance(k, str):  # classes
            return k not in extra_srg_classes
        else:  # methods, fields, and params from that class
            return k[0] not in extra_srg_classes

    srg = srg.filter(filter_classes)

    srg_v_intermediary = srg.keys().compare_to(intermediary.keys())

    # Assert srg v intermediary classes and fields match
    assert not srg_v_intermediary.right_only.classes
    assert not srg_v_intermediary.left_only.classes
    assert not srg_v_intermediary.right_only.fields
    assert not srg_v_intermediary.left_only.fields

    # Assert intermediary methods are a subset of srg
    assert not srg_v_intermediary.right_only.methods

    print('Inspecting method mappings...')
    print('  %6d extra srg mappings (before fixing inheritance)' % len(srg_v_intermediary.left_only.methods))

    # Fix missing intermediary methods by matching identical srg methods
    # This fixes issues due to inheritance
    inverse_srg = utils.invert_mapping(srg.methods)  # srg methods -> notch
    multiple_matches = set()
    no_matches = set()
    intermediary_methods = dict(intermediary.methods)
    for srg_method, notch_methods in inverse_srg.items():
        if not srg_method.startswith('func_'):
            continue  # skip non-srg named methods

        # Map srg -> {all notch} -> {all intermediary}
        matches = set()
        for notch_method in notch_methods:
            if notch_method in intermediary.methods:
                matches.add(notch_method)

        if matches:  # Any notch -> intermediary matches found
            if len(matches) == 1:  # Exact match (one notch, one intermediary), add directly
                match = matches.pop()
                for notch_method in notch_methods:
                    intermediary_methods[notch_method] = intermediary.methods[match]
            else:  # Multiple notch methods
                intermediary_matches = set(intermediary.methods[m] for m in matches)
                if len(intermediary_matches) == 1:  # All share the same intermediary method. Map them all
                    intermediary_method, *_ = intermediary_matches
                    for notch_method in notch_methods:
                        intermediary_methods[notch_method] = intermediary_method
                else:  # Multiple intermediary methods. Pick one at random and map all notch methods to that one.
                    intermediary_method = intermediary.methods[utils.peek_set(matches)]
                    for notch_method in notch_methods:
                        intermediary_methods[notch_method] = intermediary_method
                    multiple_matches.add((srg_method, frozenset(notch_methods), frozenset(matches), frozenset(intermediary.methods[m] for m in matches)))

        else:  # No matches - these are srg methods that are included from previous versions
            no_matches.add((srg_method, frozenset(notch_methods)))

    print('  %6d srg methods with no intermediary match' % (len(no_matches)))
    print('  %6d srg methods with multiple intermediary matches' % (len(multiple_matches)))

    intermediary = SourceMap(intermediary.fields, intermediary_methods, classes=intermediary.classes)

    srg_v_intermediary = srg.keys().compare_to(intermediary.keys())

    print('  %6d extra srg mappings (after fixing inheritance)' % len(srg_v_intermediary.left_only.methods))

    temp = SourceMap(classes=srg.classes, fields=srg.fields, methods=srg.methods)  # notch -> srg (classes / methods / fields)
    temp = temp.inverse()  # srg -> notch (fuzzy)
    temp = temp.compose(intermediary, remove_missing=True)  # srg -> intermediary (fuzzy)
    result = temp.select()  # srg -> intermediary

    # Create a mapping of srg method id -> srg method name (including the notch suffix) for use in looking up param -> methods
    no_srg_id = set()
    srg_method_lookup = {}
    for srg_method in srg.methods.values():
        match = re.match(srg_mapping.METHOD_PATTERN, srg_method)
        if match:
            srg_id = int(match.group(1))
            if srg_id in srg_method_lookup:
                assert srg_method_lookup[srg_id] == srg_method  # Should be no duplicate id -> method mappings
            else:
                srg_method_lookup[srg_id] = srg_method
        else:
            no_srg_id.add(srg_method)

    # Create a mapping from srg -> intermediary classes, for use in method descriptor replacements
    srg_intermediary_class_method_descriptors = {}
    for srg_clazz, intermediary_clazz in result.classes.items():
        srg_intermediary_class_method_descriptors['L%s;' % srg_clazz] = 'L%s;' % intermediary_clazz

    def remap_clazz_desc(clazz: str) -> str:
        if clazz in srg_intermediary_class_method_descriptors:
            return srg_intermediary_class_method_descriptors[clazz]
        return clazz

    # Fill out parameters by inspecting srg param names, and mapping them through to intermediary pairs of (method, index)
    no_method_matches = set()

    for srg_param in srg.params.values():
        # Only map parameters that match a unique srg id
        match = re.match(srg_mapping.PARAMETER_PATTERN, srg_param)
        if match:
            # extract the srg method name -> intermediary method. Map the index, and produce a param mapping
            ctor, srg_id, param_index = match.groups()
            srg_id = int(srg_id)
            if ctor == 'i':  # if the param was for a constructor, which are not present in srg or intermediary, but we still need to map params
                srg_clazz, srg_ctor_params = srg_reverse_constructors[srg_id]

                # First, map the constructor description to intermediary, as yarn constructor parameters require the method descriptor in addition to the index
                intermediary_clazz = remap_clazz_desc(srg_clazz)
                intermediary_ctor_params = [remap_clazz_desc(param) for param in srg_ctor_params]
                intermediary_constructor_desc = '(%s)V' % ''.join(intermediary_ctor_params)

                # Record the parameter as a four-tuple of intermediary class, constructor desc, '<init>', index
                result.params[srg_param] = (intermediary_clazz, intermediary_constructor_desc, '<init>', param_index)
            else:
                srg_method = srg_method_lookup[srg_id]
                if srg_method in result.methods:
                    intermediary_method = result.methods[srg_method]
                    result.params[srg_param] = (intermediary_method, param_index)  # Record the intermediary method / index pair
                else:
                    no_method_matches.add((srg_param, srg_id, srg_method))  # Missing srg -> intermediary mapping

    print('Inspecting parameter mappings...')
    print('  %6d srg params' % len(srg.params))
    print('  %6d srg methods with a non-unique srg id, cannot map params' % len(no_srg_id))
    print('  %6d srg -> intermediary param mappings' % len(result.params))

    return result


def generate_param_names(srg: SourceMap, srg_indexed_params: Dict[str, Dict[Any, Set]], mcp: SourceMap, yarn: SourceMap, manual_params: Dict[str, str], mojmap_lambdas: Set, result: SourceMap):
    # The set of param names which match class names. These are denied ('In' is suffixed) in order to prevent conflicts with local variables
    reserved_class_name_params = set()
    for srg_class in srg.classes.values():
        if '/' in srg_class:  # Remove packages
            srg_class = srg_class.split('/')[-1]
        if '$' in srg_class:  # Ignore inner classes for this rule, as in sources they use '$' in the name
            continue
        srg_class = srg_class.lower()  # lowercase the entire class name
        reserved_class_name_params.add(srg_class)

    unique_srg_pattern = re.compile('p_i?[0-9]+_[0-9]+_')

    # Group indexing by class
    for notch_class, entries in srg_indexed_params.items():

        class_groups = []  # groups that need to be checked for conflicts at a class level
        method_groups = []  # groups belonging to a single method

        for entry, param_group in entries.items():
            anon_class, notch_method, method_desc = entry
            # Exclude param groups which belong to lambda methods
            method_key = (notch_class, notch_method, method_desc)
            if method_key in mojmap_lambdas:
                class_groups.append(param_group)
                continue

            method_groups.append(param_group)

        class_reserved_names = set()
        for group in method_groups:
            reserved_names = set()

            for srg_param, param_type in sorted(group):
                # Ignore srg params that don't have a srg id. These will not be accurate (as they'll only work for the first method of this name found) and cause lots of conflicts
                if not re.match(unique_srg_pattern, srg_param):
                    continue

                # Strict order of precedence of which mapping to apply
                if srg_param in result.params:  # Already mapped, do not try and remap. Add the name for conflict resolution
                    reserved_names.add(result.params[srg_param])
                    continue
                elif srg_param in manual_params:
                    name = manual_params[srg_param]
                elif srg_param in mcp.params:
                    name = mcp.params[srg_param]
                elif srg_param in yarn.params:
                    name = yarn.params[srg_param]
                else:
                    name = generate_param_name(param_type, srg.classes)

                if name in reserved_class_name_params or name in utils.JAVA_KEYWORDS:
                    name += 'In'  # prevent local variable conflicts, or names mapped to keywords

                if name in reserved_names:
                    name = resolve_name_conflicts(name, reserved_names)

                result.params[srg_param] = name
                reserved_names.add(name)

            class_reserved_names |= reserved_names

        for group in class_groups:
            for srg_param, param_type in sorted(group):
                # Ignore srg params that don't have a srg id. These will not be accurate (as they'll only work for the first method of this name found) and cause lots of conflicts
                if not re.match(unique_srg_pattern, srg_param):
                    continue
                # Strict order of precedence of which mapping to apply
                if srg_param in result.params:  # Already mapped, do not try and remap. Add the name for conflict resolution
                    class_reserved_names.add(result.params[srg_param])
                    continue
                elif srg_param in manual_params:
                    name = manual_params[srg_param]
                elif srg_param in mcp.params:
                    name = mcp.params[srg_param]
                elif srg_param in yarn.params:
                    name = yarn.params[srg_param]
                else:
                    name = generate_param_name(param_type, srg.classes)

                if name in reserved_class_name_params or name in utils.JAVA_KEYWORDS:
                    name += 'In'  # prevent local variable conflicts, or names mapped to keywords

                if name in class_reserved_names:
                    name = resolve_name_conflicts(name, class_reserved_names)

                result.params[srg_param] = name
                class_reserved_names.add(name)


def generate_param_name(param_type: str, srg_classes: Dict) -> str:
    name, arrays = Parser.convert_descriptor_to_type(param_type, srg_classes)
    if '/' in name:  # Remove packages
        name = name.split('/')[-1]
    if '$' in name:  # Remove inner classes
        name = name.split('$')[-1]
    if len(name) >= 2 and name.startswith('I') and name[1].isupper():  # Remove I prefix on interfaces
        name = name[1:]
    if arrays > 0:  # Add 'Array' for array levels
        name += 'Array' * arrays
    name = name[0].lower() + name[1:]  # lowerCamelCase
    name += '_'  # Signal that this is an automatic name, prevent conflicts with local variables
    return name


def resolve_name_conflicts(name: str, reserved_names: Set) -> str:
    if name in reserved_names:
        if name.endswith('_'):
            proto_name = name[:-1]
            auto = True
        else:
            proto_name = name
            auto = False
        proto_name = proto_name.rstrip('0123456789')  # strip any previous numeric value off the end
        count = 1
        while name in reserved_names:
            name = proto_name + str(count)
            if auto:
                name += '_'
            count += 1
    return name


def append_comments(comments: Dict[str, str], extra_comments: Dict[str, str]):
    for srg, comment in extra_comments.items():
        if srg in comments:
            comment = comments[srg] + '\\n' + comment
        comments[srg] = comment


def append_mapping_comments(comments: Dict[str, str], *mappings: Tuple[str, Dict[str, str]]):
    mapping_comments = {}  # First, build the series of each mapping comments
    for mapping_name, mapping in mappings:
        for srg, named in mapping.items():
            if srg in mapping_comments:
                comment = mapping_comments[srg] + ', '
            else:
                comment = 'Mappings: ' + srg + ' (srg), '
            comment += named + ' (' + mapping_name + ')'
            mapping_comments[srg] = comment

    # Then, append all comments as a single block to the end of existing comments
    append_comments(comments, mapping_comments)


def write_reverse_lookup_log(version: str, srg: SourceMap, result: SourceMap):
    with open(mapping_downloader.get_cache_root() + '/mcp_snapshot-%s.log' % version, 'w') as f:
        for notch_class, srg_class in srg.classes.items():
            f.write('C\t%s\t%s\n' % (notch_class, srg_class))
        for field, srg_field in srg.fields.items():
            notch_class, notch_field = field
            named_class = srg.classes[notch_class] if notch_class in srg.classes else notch_class
            f.write('F\t%s\t%s\t%s\n' % (named_class, result.fields[srg_field], srg_field))
        for method, srg_method in srg.methods.items():
            notch_class, notch_method, method_desc = method
            named_class = srg.classes[notch_class] if notch_class in srg.classes else notch_class
            f.write('M\t%s\t%s\t%s\t%s\n' % (named_class, result.methods[srg_method], srg_method, method_desc))
        for param, srg_param in srg.params.items():
            notch_class, notch_method, method_desc, param_index = param
            named_class = srg.classes[notch_class] if notch_class in srg.classes else notch_class
            method_key = (notch_class, notch_method, method_desc)
            if method_key in srg.methods:
                srg_method = srg.methods[method_key]
                named_method = result.methods[srg_method]
            else:
                named_method = srg_method = notch_method
            named_param = result.params[srg_param] if srg_param in result.params else srg_param
            f.write('P\t%s\t%s\t%s\t%s\t%s\t%s\n' % (named_class, named_method, param_index, named_param, srg_method, srg_param))


def cli(version: str):
    print('Loading CLI...')

    with open(mapping_downloader.get_cache_root() + 'mcp_snapshot-%s.log' % version) as f:
        log = f.read()

    sources = []
    for line in log.split('\n'):
        if line != '':
            sources.append(tuple(line.split('\t')))
    indexed = {'C': [], 'F': [], 'M': [], 'P': []}
    for s in sources:
        indexed[s[0]].append(s)

    print(CLI_HELP)

    cmd = input('\n>')
    while cmd != 'exit':
        try:
            results = []
            cmd_parts = [c.lower() for c in cmd.split(' ')]
            if cmd_parts == ['help']:
                print(CLI_HELP)
                cmd = input('>')
                continue
            max_show = 10
            index = 0
            while index < len(cmd_parts):
                cmd_part = cmd_parts[index]
                if cmd_part == 'c':  # list classes
                    clazz = cmd_parts[index + 1]
                    results = [i for i in indexed['C'] if clazz in i[2].lower()]
                elif cmd_part == 'nc':  # list notch classes
                    clazz = cmd_parts[index + 1]
                    results = [i for i in indexed['C'] if clazz in i[1].lower()]
                elif cmd_part == 'f':  # list fields
                    field = cmd_parts[index + 1]
                    results = [i for i in indexed['F'] if field in i[2].lower()]
                elif cmd_part == 'm':  # list methods
                    method = cmd_parts[index + 1]
                    results = [i for i in indexed['M'] if method in i[2].lower()]
                elif cmd_part == 'p':  # list params
                    param = cmd_parts[index + 1]
                    results = [i for i in indexed['P'] if param in i[4].lower()]
                elif cmd_part == 'fc':  # filter classes (on a field, method or class search)
                    clazz = cmd_parts[index + 1]
                    results = [r for r in results if clazz in r[1].lower()]
                elif cmd_part == 'fm':  # filter methods (on a param search)
                    method = cmd_parts[index + 1]
                    results = [r for r in results if method in r[2].lower()]
                elif cmd_part == '[':  # picks a single result
                    i = int(cmd_parts[index + 1])
                    results = [results[i]]
                elif cmd_part == 'gp':  # gets parameters for the first method name
                    method = results[0]
                    results = [p for p in indexed['P'] if method[1] == p[1] and method[2] == p[2]]
                    index -= 1
                elif cmd_part == 'gm':  # gets methods for each class
                    clazz = results[0]
                    results = [m for m in indexed['M'] if clazz[2] == m[1]]
                    index -= 1
                elif cmd_part == 'max':  # max results returned
                    max_show = int(cmd_parts[index + 1])

                index += 2

            for r in results[:max_show]:
                print(r)
            if len(results) > max_show:
                print('First %d results shown. Use max # for more' % max_show)
            if not results:
                print('No Results')
        except Exception as e:
            print('Error: ' + str(e))
        cmd = input('\n>')


if __name__ == '__main__':
    main()
