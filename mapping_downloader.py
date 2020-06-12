# Simple one-time downloader

import datetime
import io
import json
import os
import urllib.request
import zipfile
from typing import Tuple, Optional

# There's probably an API for it but for sure it's not documented anywhere and asking is just going to receive a 'just read the code' so why bother
MCP_SRG_EXTRA_RUBBISH = {
    '1.15.2': '20200515.085601',
    '1.15.1': '20191217.105819'
}


def load_yarn_v2(mc_version: str, yarn_version: Optional[str] = None) -> str:
    if yarn_version is None:
        # find the newest build if it exists
        yarn_mappings = sorted([f for f in os.listdir('./build/') if os.path.isfile('./build/' + f) and f.startswith('yarn_v2-%s' % mc_version)])
        if yarn_mappings:
            with open('./build/' + yarn_mappings[-1]) as f:
                return f.read()
    else:
        path = './build/yarn_v2-%s+build.%s.tiny' % (mc_version, yarn_version)
        # find exact match
        if os.path.isfile(path):
            with open(path) as f:
                return f.read()

    yarn, path = download_yarn_v2(mc_version, yarn_version)
    with open('./build/' + path, 'w', encoding='utf-8') as f:
        f.write(yarn)
    return yarn


def download_yarn_v2(mc_version: str, yarn_version: Optional[str] = None) -> Tuple[str, str]:
    # fetch yarn metadata in order to determine available build numbers
    meta_url = 'https://meta.fabricmc.net/v2/versions/yarn'
    with urllib.request.urlopen(meta_url) as request:
        versions = json.loads(request.read().decode('utf-8'))

    # filter versions based on passed in mc and yarn version numbers
    versions = [v for v in versions if v['gameVersion'] == mc_version and (yarn_version is None or v['build'] == yarn_version)]
    if versions is None:
        raise RuntimeError('Unable to find a version matching %s and %s' % (mc_version, str(yarn_version)))
    if yarn_version is None:
        versions.sort(key=lambda k: -k['build'])
        yarn_version = versions[0]['build']

    # download specified yarn build
    path = 'yarn_v2-%s+build.%s.tiny' % (mc_version, yarn_version)
    print('Downloading %s' % path)
    url = 'https://maven.fabricmc.net/net/fabricmc/yarn/%s+build.%s/yarn-%s+build.%s-v2.jar' % (mc_version, yarn_version, mc_version, yarn_version)
    with urllib.request.urlopen(url) as request:
        tiny_jar = request.read()
    with io.BytesIO(tiny_jar) as fio:
        with zipfile.ZipFile(fio, 'r') as tiny_zip:
            with tiny_zip.open('mappings/mappings.tiny') as f:
                mappings = f.read().decode('utf-8').replace('\r\n', '\n')
    return mappings, path


def load_yarn_intermediary(mc_version: str) -> str:
    path = './build/yarn_intermediary-%s.tiny' % mc_version
    if os.path.isfile(path):
        with open(path) as f:
            return f.read()

    intermediary = download_yarn_intermediary(mc_version)
    with open(path, 'w') as f:
        f.write(intermediary)
    return intermediary


def download_yarn_intermediary(mc_version: str) -> str:
    print('Downloading yarn_intermediary-%s.tiny' % mc_version)
    url = 'https://raw.githubusercontent.com/FabricMC/intermediary/master/mappings//%s.tiny' % mc_version
    with urllib.request.urlopen(url) as request:
        return request.read().decode('utf-8').replace('\r\n', '\n')


def load_mcp_mappings(mc_version: str, mcp_date: Optional[str] = None) -> Tuple[str, str, str]:
    if mcp_date is None:
        mcp_date = str(datetime.date.today()).replace('-', '')
    root_path = './build/mcp_snapshot-%s-%s' % (mcp_date, mc_version)
    if os.path.isdir(root_path):
        with open(root_path + '/methods.csv') as f:
            methods = f.read()
        with open(root_path + '/fields.csv') as f:
            fields = f.read()
        with open(root_path + '/params.csv') as f:
            params = f.read()
        return methods, fields, params

    methods, fields, params, _ = download_mcp_mappings(mc_version, mcp_date)
    if not os.path.isdir(root_path):
        os.mkdir(root_path)
    with open(root_path + '/methods.csv', 'w') as f:
        f.write(methods)
    with open(root_path + '/fields.csv', 'w') as f:
        f.write(fields)
    with open(root_path + '/params.csv', 'w') as f:
        f.write(params)
    return methods, fields, params


def download_mcp_mappings(mc_version: str, mcp_date: Optional[str] = None) -> Tuple[str, str, str, str]:
    if mcp_date is None:
        mcp_date = str(datetime.date.today()).replace('-', '')
    url = 'http://export.mcpbot.bspk.rs/mcp_snapshot/%s-%s/mcp_snapshot-%s-%s.zip' % (mcp_date, mc_version, mcp_date, mc_version)
    path = 'mcp_snapshot-%s-%s' % (mcp_date, mc_version)
    print('Downloading %s' % path)
    with urllib.request.urlopen(url) as request:
        export = request.read()
    with io.BytesIO(export) as fio:
        with zipfile.ZipFile(fio, 'r') as export_zip:
            with export_zip.open('methods.csv') as f:
                methods = f.read().decode('utf-8').replace('\r\n', '\n')
            with export_zip.open('fields.csv') as f:
                fields = f.read().decode('utf-8').replace('\r\n', '\n')
            with export_zip.open('params.csv') as f:
                params = f.read().decode('utf-8').replace('\r\n', '\n')
    return methods, fields, params, path


def load_mcp_srg(mc_version: str, extra_rubbish: str = '') -> str:
    path = './build/mcp_srg-%s.tsrg' % mc_version
    if os.path.isfile(path):
        with open(path) as f:
            return f.read()

    joined = download_mcp_srg(mc_version)
    with open(path, 'w') as f:
        f.write(joined)
    return joined


def download_mcp_srg(mc_version: str) -> str:
    extra_rubbish = MCP_SRG_EXTRA_RUBBISH[mc_version]
    url = 'https://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config/%s-%s/mcp_config-%s-%s.zip' % (mc_version, extra_rubbish, mc_version, extra_rubbish)
    try:
        with urllib.request.urlopen(url) as request:
            mcp_config = request.read()
        with io.BytesIO(mcp_config) as fio:
            with zipfile.ZipFile(fio, 'r') as mcp_config_zip:
                with mcp_config_zip.open('config/joined.tsrg') as f:
                    joined = f.read().decode('utf-8').replace('\r\n', '\n')
    except:
        print('Unable to download mcp_srg from %s' % repr(url))
        raise
    return joined
