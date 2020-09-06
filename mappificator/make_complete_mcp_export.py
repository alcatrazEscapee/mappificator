# This is why we can't have nice things

from typing import Dict, Set, Any

from mappificator.mapping import official_mapping, srg_mapping, mcp_mapping, spreadsheet_mapping
from mappificator.util import utils
from mappificator.util.parser import Parser
from mappificator.util.source_map import SourceMap
from mappificator.util.source_set import SourceSetComparison


def main():
    # This is the MCP export version
    # 'complete' identifies the methodology
    # '20200723' is the mcp bot export used
    # '1.16.2' is the minecraft version
    # 'v3' is the current iteration
    version = 'complete-20200723-1.16.2-v6'

    print('Reading mappings...')

    mojmap, mojmap_lambdas = official_mapping.read('1.16.2')
    srg, srg_indexed_params = srg_mapping.read('1.16.2')
    mcp, mcp_method_comments, mcp_field_comments = mcp_mapping.read('1.16.1', '20200723')
    ss, ss_method_comments, ss_field_comments = spreadsheet_mapping.read()

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
    generate_param_names(srg, srg_indexed_params, mojmap_lambdas, mcp, ss, result)

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
    write_reverse_lookup_log(version, '../build', srg, result)

    # Write mcp mappings
    mcp_mapping.write(version, '../build', result, field_comments, method_comments)
    mcp_mapping.publish(version, '../build')

    print('Done')


def print_compare(compare: SourceSetComparison):
    print('Fields: %d / %d (%.2f%%)' % (len(compare.intersect.fields), len(compare.left.fields), 100 * len(compare.intersect.fields) / len(compare.left.fields)))
    print('Methods: %d / %d (%.2f%%)' % (len(compare.intersect.methods), len(compare.left.methods), 100 * len(compare.intersect.methods) / len(compare.left.methods)))
    print('Params: %d / %d (%.2f%%)' % (len(compare.intersect.params), len(compare.left.params), 100 * len(compare.intersect.params) / len(compare.left.params)))


def generate_param_names(srg: SourceMap, srg_indexed_params: Dict[str, Dict[Any, Set]], mojmap_lambdas: Set, mcp: SourceMap, ss: SourceMap, result: SourceMap):
    # Generate parameter names
    # This is done in stages, to account for possible conflicts between parameter groups
    # Both lambdas and anon. classes may cause conflicts within the same class
    for notch_class, entries in srg_indexed_params.items():

        class_groups = []  # groups that need to be checked for conflicts at a class level
        method_groups = []  # groups belonging to a single method

        for entry, param_group in entries.items():
            anon_class, notch_method, method_desc = entry
            # Exclude param groups which belong to anon. classes
            if anon_class is not None:
                class_groups.append(param_group)
                continue
            # Exclude param groups which belong to lambda methods
            method_key = (notch_class, notch_method, method_desc)
            if method_key in mojmap_lambdas:
                class_groups.append(param_group)
                continue

            method_groups.append(param_group)

        # Generate params for each method group, checking for conflicts within the group
        class_reserved_names = set()
        for group in method_groups:
            reserved_names = set()
            for srg_param, param_type in sorted(group, key=lambda k: k[0]):
                if srg_param in result.params:
                    # Already named this param. We accept this name as final, and throw an error if it leads to a conflict in this method
                    name = result.params[srg_param]
                elif srg_param in mcp.params:
                    name = mcp.params[srg_param]
                elif srg_param in ss.params:
                    name = ss.params[srg_param]
                else:
                    # Auto-generate name based on class name
                    name = generate_param_name(param_type, srg.classes, reserved_names)

                if name in reserved_names:
                    if name in result.params:
                        raise ValueError('A parameter conflicts with one that is already assigned!')
                    name = resolve_name_conflicts(name, reserved_names)

                result.params[srg_param] = name
                reserved_names.add(name)
                class_reserved_names.add(name)

        # Next, generate params for each class level group, checking conflicts against all previously named params for this class
        for group in class_groups:
            for srg_param, param_type in sorted(group, key=lambda k: k[0]):
                if srg_param in result.params:
                    name = result.params[srg_param]
                elif srg_param in mcp.params:
                    name = mcp.params[srg_param]
                elif srg_param in ss.params:
                    name = ss.params[srg_param]
                else:
                    # Auto-generate name based on class name
                    name = generate_param_name(param_type, srg.classes, class_reserved_names)

                if name in class_reserved_names:
                    if name in result.params:
                        raise ValueError('A parameter conflicts with one that is already assigned!')
                    name = resolve_name_conflicts(name, class_reserved_names)

                result.params[srg_param] = name
                class_reserved_names.add(name)


def generate_param_name(param_type: str, srg_classes: Dict, reserved_names: Set) -> str:
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

    if name in reserved_names:
        proto_name = name[:-1]  # strip the trailing underscore
        count = 1
        while name in reserved_names:
            name = proto_name + str(count) + '_'
            count += 1

    return name


def resolve_name_conflicts(name: str, reserved_names: Set) -> str:
    if name in reserved_names:
        proto_name = name
        count = 1
        while name in reserved_names:
            name = proto_name + str(count)
            count += 1
    return name


def write_reverse_lookup_log(version: str, path: str, srg: SourceMap, result: SourceMap):
    with open(path + '/mcp_snapshot-complete-%s.log' % version, 'w') as f:
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
