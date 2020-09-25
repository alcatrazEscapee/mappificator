# This is why we can't have nice things

import re
from typing import Dict, Set, Any

from mapping import srg_mapping, mcp_mapping, spreadsheet_mapping, official_mapping
from util import utils, mapping_downloader
from util.parser import Parser
from util.sources import SourceMap, SourceSetComparison

# This is the MCP export version
# 'complete' identifies the methodology
# 'YYYYMMDD' is the mcp bot export used
# '#.#.#' is the minecraft version
# 'v#' is the current iteration
VERSION = 'complete-20200912-1.16.3-v5'


def main():
    print('Reading mappings...')

    mojmap, mojmap_lambdas = official_mapping.read('1.16.3')
    srg, srg_indexed_params = srg_mapping.read('1.16.3')
    mcp, mcp_method_comments, mcp_field_comments = mcp_mapping.read('1.16.2', '20200912')
    ss, ss_method_comments, ss_field_comments = spreadsheet_mapping.read('1.16.3')
    manual_mappings = mapping_downloader.load_manual_corrections('1.16.3')

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

    mcp_v_ss = mcp.keys().compare_to(ss.keys())
    srg_v_ss = srg.values().compare_to(ss.keys())
    srg_v_both = srg.values().compare_to(mcp_v_ss.union)

    # Print basic conclusions using official, mojmap and mcp mappings

    print('=== MCP Mappings ===')
    print_compare(srg_v_mcp)
    print('=== MCP Spreadsheet ===')
    print_compare(srg_v_ss)
    print('=== MCP Mappings + Spreadsheet ===')
    print_compare(srg_v_both)

    # Generate the result mappings
    temp = SourceMap(fields=srg.fields, methods=srg.methods)  # notch -> srg (methods / fields)
    temp = temp.inverse()  # srg -> notch (fuzzy, methods / fields)
    temp = temp.compose(mojmap)  # srg -> official (fuzzy, methods / fields)
    result = temp.select()  # srg -> official (methods / fields)

    # Procedurally generate the rest of the parameters, watching for conflicts with each other.
    generate_param_names(srg, srg_indexed_params, mcp, ss, manual_mappings, mojmap_lambdas, result)

    print('=== Mojmap + MCP Bot + MCP Spreadsheet + Auto Param ===')
    print_compare(srg.values().compare_to(result.keys()))

    # Comments
    field_comments = {}
    utils.append_mapping(field_comments, mcp_field_comments)
    utils.append_mapping(field_comments, ss_field_comments)
    print('Field Comments = %d' % len(field_comments))

    method_comments = {}
    utils.append_mapping(method_comments, mcp_method_comments)
    utils.append_mapping(method_comments, ss_method_comments)
    print('Method Comments = %d' % len(method_comments))

    # Write reverse lookup log output
    write_reverse_lookup_log(VERSION, '../build', srg, result)

    # Write mcp mappings
    mcp_mapping.write(VERSION, 'build', result, field_comments, method_comments)
    mcp_mapping.publish(VERSION, 'build')

    print('Done')


def print_compare(compare: SourceSetComparison):
    print('Fields: %d / %d (%.2f%%)' % (len(compare.intersect.fields), len(compare.left.fields), 100 * len(compare.intersect.fields) / len(compare.left.fields)))
    print('Methods: %d / %d (%.2f%%)' % (len(compare.intersect.methods), len(compare.left.methods), 100 * len(compare.intersect.methods) / len(compare.left.methods)))
    print('Params: %d / %d (%.2f%%)' % (len(compare.intersect.params), len(compare.left.params), 100 * len(compare.intersect.params) / len(compare.left.params)))


def generate_param_names(srg: SourceMap, srg_indexed_params: Dict[str, Dict[Any, Set]], mcp: SourceMap, ss: SourceMap, manual_params: Dict[str, str], mojmap_lambdas: Set, result: SourceMap):
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
                elif srg_param in ss.params:
                    name = ss.params[srg_param]
                else:
                    name = generate_param_name(param_type, srg.classes)

                if name in reserved_class_name_params:
                    name = name + 'In'  # prevent local variable conflicts

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
                elif srg_param in ss.params:
                    name = ss.params[srg_param]
                else:
                    name = generate_param_name(param_type, srg.classes)

                if name in reserved_class_name_params:
                    name = name + 'In'  # prevent local variable conflicts

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


def write_reverse_lookup_log(version: str, path: str, srg: SourceMap, result: SourceMap):
    with open(path + '/mcp_snapshot-%s.log' % version, 'w') as f:
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


if __name__ == '__main__':
    main()
