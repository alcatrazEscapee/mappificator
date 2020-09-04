# This is why we can't have nice things

from mappificator.util import mapping_downloader, mapping_util
from mappificator.writers import mcp_export_writer

from mappificator.parsers.mcp_mapping_parser import McpMappingParser
from mappificator.parsers.mcp_srg_parser import McpSrgParser
from mappificator.parsers.official_parser import OfficialParser

from mappificator.source.source_map import SourceMap


def main():
    version = 'mcp-official-20200723-1.16.2'

    print('Reading mappings...')

    srg_raw = mapping_downloader.load_mcp_srg('1.16.2')
    srg_parser = McpSrgParser(srg_raw)
    srg = SourceMap(srg_parser.fields, srg_parser.methods, srg_parser.params, srg_parser.classes)

    client, server = mapping_downloader.load_official('1.16.2')
    client_parser, server_parser = OfficialParser(client), OfficialParser(server)
    official_client, official_server = SourceMap(client_parser.fields, client_parser.methods, None, client_parser.classes), SourceMap(server_parser.fields, server_parser.methods, None, server_parser.classes)

    methods_raw, fields_raw, params_raw = mapping_downloader.load_mcp_mappings('1.16.1', '20200723')
    methods_parser, fields_parser, params_parser = McpMappingParser(methods_raw), McpMappingParser(fields_raw), McpMappingParser(params_raw)
    mcp = SourceMap(fields_parser.mappings, methods_parser.mappings, params_parser.mappings)

    print('Validating official')

    # Validate official server is a subset of official client (in entirety)
    official_client_v_server = official_client.keys().compare_to(official_server.keys())
    assert official_client_v_server.right_only.is_empty()

    print('Validating srg')
    # Validate srg is a subset of official client (classes, methods, and fields)
    official_client_v_srg = official_client.keys().compare_to(srg.keys())
    assert not official_client_v_srg.right_only.classes
    assert not official_client_v_srg.right_only.methods
    assert not official_client_v_srg.right_only.fields

    # srg may contain things which are unable to be mapped. These are stripped out here (methods, fields and params)
    temp = srg.filter(lambda k, v: bool(McpSrgParser.SRG_REGEX.match(v)))
    srg = SourceMap(temp.fields, temp.methods, temp.params, srg.classes)

    print('Validating mcp')
    mcp = mcp.filter_keys(srg.values())

    # Sanity check, assert that mcp is now a strict subset of the srg values
    srg_v_mcp = srg.values().compare_to(mcp.keys())
    assert srg_v_mcp.right_only.is_empty()

    # Generate the result mappings
    temp = SourceMap(fields=srg.fields, methods=srg.methods)  # notch -> srg (methods / fields)
    temp = temp.inverse()  # srg -> notch (fuzzy, methods / fields)
    temp = temp.compose(official_client)  # srg -> official (fuzzy, methods / fields)
    srg_2_official = temp.select()  # srg -> official (methods / fields)
    mapping_util.append_mapping(srg_2_official.params, mcp.params)  # append params from mcp

    # Write mcp mappings
    mcp_export_writer.build_and_publish_mcp_export(version, '../build/', srg_2_official, fields_parser.comments, methods_parser.comments)


if __name__ == '__main__':
    main()
