import csv
from typing import Tuple, Dict

from util import mapping_downloader
from util.sources import SourceMap


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
        elif row[0].startswith('#'):
            # counter / comment line
            pass
        else:
            raise RuntimeError('Intermediary Mapping Error: Unknown line: %s' % str(row))

    return classes, fields, methods
