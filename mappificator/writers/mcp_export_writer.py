
import os
import csv
import zipfile
import subprocess
from typing import Mapping, Optional, Callable

from mappificator.source.source_map import SourceMap


def build_and_publish_mcp_export(version: str, path: str, source_map: SourceMap, field_comments: Optional[Mapping] = None, method_comments: Optional[Mapping] = None, log_output: Optional[Callable[[str], None]] = None):
    fields_comments = field_comments if field_comments is not None else dict()
    method_comments = method_comments if method_comments is not None else dict()

    fields_txt = write_csv_fields_or_methods(source_map.fields, fields_comments).dump()
    methods_txt = write_csv_fields_or_methods(source_map.methods, method_comments).dump()
    params_txt = write_csv_params(source_map.params).dump()

    file_path = os.path.join(path, 'mcp_snapshot-%s.zip' % version)
    with zipfile.ZipFile(file_path, 'w') as f:
        f.writestr('params.csv', params_txt)
        f.writestr('fields.csv', fields_txt)
        f.writestr('methods.csv', methods_txt)

    file_path = os.path.join(path, 'mcp_snapshot-%s.zip' % version)
    if not os.path.isfile(file_path):
        raise ValueError('Must first build export before publishing to maven local')

    proc = subprocess.Popen('mvn install:install-file -Dfile=%s -DgroupId=de.oceanlabs.mcp -DartifactId=mcp_snapshot -Dversion=%s -Dpackaging=zip' % (file_path, version), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while proc.poll() is None:
        output = proc.stdout.readline().decode('utf-8').replace('\r', '').replace('\n', '')
        if output != '':
            log_output(output)
    mvn_ret_code = proc.wait()  # catch return code
    if mvn_ret_code != 0:
        raise ValueError('Maven install returned error code %s' % str(mvn_ret_code))


class BufferedWriter:
    """ This exists as an intermediary between csv.writer and zipfile.writestr """

    def __init__(self):
        self.buffer = []

    def write(self, text):
        self.buffer.append(text)

    def dump(self):
        return ''.join(self.buffer)


def write_csv_fields_or_methods(data: Mapping, comments: Mapping) -> BufferedWriter:
    writer = BufferedWriter()
    csv_writer = csv.writer(writer, lineterminator='\n')
    csv_writer.writerow(['searge', 'name', 'side', 'desc'])
    for srg, named in sorted(data.items(), key=lambda t: srg_sort(t[0])):
        comment = comments[srg] if srg in comments else ''
        csv_writer.writerow([srg, named, '2', comment])  # side is ignored by FG
    return writer


def write_csv_params(params: Mapping) -> BufferedWriter:
    writer = BufferedWriter()
    csv_writer = csv.writer(writer, lineterminator='\n')
    csv_writer.writerow(['param', 'name', 'side'])
    for srg, named in sorted(params.items(), key=lambda t: srg_sort(t[0])):
        csv_writer.writerow([srg, named, '2'])  # side is ignored by FG
    return writer


def srg_sort(k: str) -> int:
    try:
        return int(k.split('_')[1])
    except ValueError:
        return 0
