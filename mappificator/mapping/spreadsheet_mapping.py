# I cannot believe this is STILL the state of forge mappings. But here we go

import csv
from typing import Tuple, Dict

from mappificator.util import mapping_downloader
from mappificator.util.sources import SourceMap


def read(mc_version: str) -> Tuple[SourceMap, Dict[str, str], Dict[str, str]]:
    names = mapping_downloader.load_mcp_spreadsheet(mc_version)
    fields = {}
    field_comments = {}
    methods = {}
    method_comments = {}
    params = {}

    for row in csv.reader(names.split('\n')[1:]):
        if row:
            srg_member = row[2]
            named_member = row[3]
            if named_member != '':
                if len(row) >= 6 and row[5] != '':
                    comment = row[5]
                else:
                    comment = None

                if srg_member.startswith('func_'):
                    methods[srg_member] = named_member
                    if comment is not None:
                        method_comments[srg_member] = comment
                elif srg_member.startswith('field_'):
                    fields[srg_member] = named_member
                    if comment is not None:
                        field_comments[srg_member] = comment
                elif srg_member.startswith('p_'):
                    params[srg_member] = named_member

    return SourceMap(fields, methods, params), method_comments, field_comments
