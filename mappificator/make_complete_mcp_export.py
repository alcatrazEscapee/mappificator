# This is why we can't have nice things

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
    # 'v2' is the current iteration
    version = 'complete-20200723-1.16.2-v2'

    print('Reading mappings...')

    mojmap = official_mapping.read('1.16.2')
    srg, srg_param_groups = srg_mapping.read('1.16.2')
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

    # Validate and inject auto generated parameters
    for group in srg_param_groups:
        named_group = set()

        # go through sorted param list:
        for srg_param, param_type in sorted(group, key=lambda k: k[0]):
            if srg_param in mcp.params:
                auto = False
                name = mcp.params[srg_param]
            elif srg_param in ss.params:
                auto = False
                name = ss.params[srg_param]
            else:
                # Auto-generate name based on class name
                auto = True
                name = Parser.convert_descriptor_to_type(param_type, srg.classes)
                if '/' in name:  # Remove packages
                    name = name.split('/')[-1]
                if '$' in name:  # Remove inner classes
                    name = name.split('$')[-1]
                if len(name) >= 2 and name.startswith('I') and name[1].isupper():  # Remove I prefix on interfaces
                    name = name[1:]
                name = name[0].lower() + name[1:]  # camelCase
                name += '_'  # Signal that this is an automatic name, prevent conflicts with local variables

            if name in named_group:
                # Need to resolve a conflict with an existing name
                proto_name = name
                count = 1
                while name in named_group:
                    if auto:
                        name = proto_name[:-1] + str(count) + '_'
                    else:
                        name = proto_name + str(count)
                    count += 1

            result.params[srg_param] = name
            named_group.add(name)

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

    # Write mcp mappings
    mcp_mapping.write(version, '../build', result, field_comments, method_comments)
    mcp_mapping.publish(version, '../build')

    print('Done')


def print_compare(compare: SourceSetComparison):
    print('Fields: %d / %d (%.2f%%)' % (len(compare.intersect.fields), len(compare.left.fields), 100 * len(compare.intersect.fields) / len(compare.left.fields)))
    print('Methods: %d / %d (%.2f%%)' % (len(compare.intersect.methods), len(compare.left.methods), 100 * len(compare.intersect.methods) / len(compare.left.methods)))
    print('Params: %d / %d (%.2f%%)' % (len(compare.intersect.params), len(compare.left.params), 100 * len(compare.intersect.params) / len(compare.left.params)))


if __name__ == '__main__':
    main()
