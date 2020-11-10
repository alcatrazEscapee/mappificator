# I cannot believe this is STILL the state of forge mappings. But here we go

import csv
from typing import Tuple, Dict

from util import mapping_downloader
from util.sources import SourceMap, SourceSet


def read(mc_version: str) -> Tuple[SourceSet, SourceMap, Dict[str, str], Dict[str, str]]:
    names = mapping_downloader.load_mcp_spreadsheet(mc_version)

    all_fields = set()
    all_methods = set()
    all_params = set()

    named_fields = {}
    named_methods = {}
    named_params = {}

    field_comments = {}
    method_comments = {}

    for row in csv.reader(names.split('\n')[1:]):
        # Quote: "we don't suggest using the unverified ones if you plan on building your own mappings. They are probably broken until verified"
        # And yes, after many encounters they are indeed broken.
        if row and row[0] == 'TRUE':
            srg_member = row[2]
            named_member = row[3]
            if len(row) >= 6 and row[5] != '':
                comment = row[5]
            else:
                comment = None

            if srg_member.startswith('func_'):
                all_methods.add(srg_member)
                if named_member != '':
                    named_methods[srg_member] = named_member
                if comment is not None:
                    method_comments[srg_member] = comment
            elif srg_member.startswith('field_'):
                all_fields.add(srg_member)
                if named_member != '':
                    named_fields[srg_member] = named_member
                if comment is not None:
                    field_comments[srg_member] = comment
            elif srg_member.startswith('p_'):
                all_params.add(srg_member)
                if named_member != '':
                    named_params[srg_member] = named_member
            else:
                raise RuntimeError('Unable to parse row: %s' % str(row))

    return SourceSet(all_fields, all_methods, all_params), SourceMap(named_fields, named_methods, named_params), method_comments, field_comments
