import csv
from typing import Tuple, Dict

from mappificator.util import mapping_downloader
from mappificator.util.source_map import SourceMap


def read(mc_version: str):
    yarn_intermediary = mapping_downloader.load_yarn_intermediary(mc_version)
    classes, fields, methods = parse_intermediary(yarn_intermediary)

    return SourceMap(fields, methods, classes=classes)


def parse_intermediary(text: str) -> Tuple[Dict, Dict, Dict]:
    classes = {}
    fields = {}
    methods = {}

    for row in csv.reader(text.split('\n')[1:], delimiter='\t'):
        if not row:  # skip empty lines
            continue
        if row[0] == 'CLASS':
            # notch name -> intermediary name
            classes[row[1]] = row[2]
        elif row[0] == 'FIELD':
            # notch class, notch field -> intermediary field
            fields[(row[1], row[3])] = row[4]
        elif row[0] == 'METHOD':
            # notch class, notch method, params -> intermediary method
            methods[(row[1], row[3], row[2])] = row[4]
            # todo: proper param indexes (need to know static / non-static method and long/double types)

    return classes, fields, methods
