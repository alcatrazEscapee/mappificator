# Simple one-time downloader for various minecraft mappings
# Supports Official, MCPConfig tsrg, MCP, tterrag's yarn2mcp, Fabric Intermediary, and Yarn
# Invoking the "load" methods will first look for a cached version of the file in `./build`, if not found, will invoke "download"
# Invoking the "download" methods will always download a new file, and save it in `./build`

import datetime
import io
import json
import os
import urllib.request
import urllib.error
import zipfile
from typing import Tuple, Optional, Any


CACHE_LOCATION = './build/'
OFFICIAL_MAPPINGS = {
    '1.16.2': {
        'client': 'https://launcher.mojang.com/v1/objects/16d12d67cd5341bfc848340f61f3ff6b957537fe/client.txt',
        'server': 'https://launcher.mojang.com/v1/objects/40337a76c8486473e5990f7bb44b13bc08b69e7a/server.txt'
    }
}


def set_cache_location(new_cache_location: str):
    global CACHE_LOCATION
    CACHE_LOCATION = new_cache_location


def load_yarn_v2(mc_version: str, yarn_version: Optional[str] = None) -> str:
    if yarn_version is None:
        # find the newest build if it exists
        yarn_mappings = sorted([f for f in os.listdir(CACHE_LOCATION) if os.path.isfile(CACHE_LOCATION + f) and f.startswith('yarn_v2-%s' % mc_version)])
        if yarn_mappings:
            print('Loading %s%s' % (CACHE_LOCATION, yarn_mappings[-1]))
            with open(CACHE_LOCATION + yarn_mappings[-1]) as f:
                return f.read()
    else:
        path = CACHE_LOCATION + 'yarn_v2-%s+build.%s.tiny' % (mc_version, yarn_version)
        # find exact match
        if os.path.isfile(path):
            print('Loading %s' % path)
            with open(path) as f:
                return f.read()

    yarn, path = download_yarn_v2(mc_version, yarn_version)
    with open(CACHE_LOCATION + path, 'w', encoding='utf-8') as f:
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
                mappings = sanitize_utf8(f.read())
    return mappings, path


def load_yarn_intermediary(mc_version: str) -> str:
    path = CACHE_LOCATION + 'yarn_intermediary-%s.tiny' % mc_version
    if os.path.isfile(path):
        print('Loading %s' % path)
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
        return sanitize_utf8(request.read())


def load_mcp_mappings(mc_version: str, mcp_date: Optional[str] = None) -> Tuple[str, str, str]:
    if mcp_date is None:
        mcp_date = str(datetime.date.today()).replace('-', '')
    root_path = CACHE_LOCATION + 'mcp_snapshot-%s-%s' % (mcp_date, mc_version)
    if os.path.isdir(root_path):
        print('Loading %s' % root_path)
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
    path = 'mcp_snapshot-%s-%s' % (mcp_date, mc_version)

    # Since the state of MCP is in limbo, use multiple sources
    urls = [
        'http://export.mcpbot.bspk.rs/mcp_snapshot/%s-%s/mcp_snapshot-%s-%s.zip' % (mcp_date, mc_version, mcp_date, mc_version),
        'https://www.dogforce-games.com/maven/de/oceanlabs/mcp/mcp_snapshot/%s-%s/mcp_snapshot-%s-%s.zip' % (mcp_date, mc_version, mcp_date, mc_version)
    ]
    export = error = None
    while export is None and urls:
        url = urls.pop(0)
        print('Downloading %s, from %s' % (path, (url[:30] + '...' if len(url) > 30 else url)))
        export, error = try_download(url)
    if export is None:
        raise error

    with io.BytesIO(export) as fio:
        with zipfile.ZipFile(fio, 'r') as export_zip:
            with export_zip.open('methods.csv') as f:
                methods = sanitize_utf8(f.read())
            with export_zip.open('fields.csv') as f:
                fields = sanitize_utf8(f.read())
            with export_zip.open('params.csv') as f:
                params = sanitize_utf8(f.read())
    return methods, fields, params, path


def load_yarn2mcp_mappings(mc_version: str, mcp_date: str, mix_type: str = 'mixed') -> Tuple[str, str, str]:
    root_path = CACHE_LOCATION + 'yarn2mcp_snapshot-%s-%s-%s' % (mcp_date, mc_version, mix_type)
    if os.path.isdir(root_path):
        print('Loading %s' % root_path)
        with open(root_path + '/methods.csv') as f:
            methods = f.read()
        with open(root_path + '/fields.csv') as f:
            fields = f.read()
        try:
            with open(root_path + '/params.csv') as f:
                params = f.read()
        except FileNotFoundError:
            params = ''
        return methods, fields, params

    methods, fields, params, _ = download_yarn2mcp_mappings(mc_version, mcp_date, mix_type)
    if not os.path.isdir(root_path):
        os.mkdir(root_path)
    with open(root_path + '/methods.csv', 'w') as f:
        f.write(methods)
    with open(root_path + '/fields.csv', 'w') as f:
        f.write(fields)
    with open(root_path + '/params.csv', 'w') as f:
        f.write(params)
    return methods, fields, params


def download_yarn2mcp_mappings(mc_version: str, mcp_date: str, mix_type: str) -> Tuple[str, str, str, str]:
    url = 'https://maven.tterrag.com/de/oceanlabs/mcp/mcp_snapshot/%s-%s-%s/mcp_snapshot-%s-%s-%s.zip' % (mcp_date, mix_type, mc_version, mcp_date, mix_type, mc_version)
    path = 'yarn2mcp-%s-%s-%s' % (mcp_date, mix_type, mc_version)
    print('Downloading %s' % path)
    with urllib.request.urlopen(url) as request:
        export = request.read()
    with io.BytesIO(export) as fio:
        with zipfile.ZipFile(fio, 'r') as export_zip:
            with export_zip.open('methods.csv') as f:
                methods = sanitize_utf8(f.read())
            with export_zip.open('fields.csv') as f:
                fields = sanitize_utf8(f.read())
            try:
                with export_zip.open('params.csv') as f:
                    params = sanitize_utf8(f.read())
            except KeyError:
                print('params.csv not found')
                params = ''
    return methods, fields, params, path


def load_mcp_srg(mc_version: str) -> str:
    path = CACHE_LOCATION + 'mcp_srg-%s.tsrg' % mc_version
    if os.path.isfile(path):
        print('Loading %s' % path)
        with open(path) as f:
            return f.read()

    joined = download_mcp_srg(mc_version)
    with open(path, 'w') as f:
        f.write(joined)
    return joined


def download_mcp_srg(mc_version: str) -> str:
    url = 'https://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config/%s/mcp_config-%s.zip' % (mc_version, mc_version)
    try:
        with urllib.request.urlopen(url) as request:
            mcp_config = request.read()
        with io.BytesIO(mcp_config) as fio:
            with zipfile.ZipFile(fio, 'r') as mcp_config_zip:
                with mcp_config_zip.open('config/joined.tsrg') as f:
                    joined = sanitize_utf8(f.read())
        return joined
    except:
        print('Unable to download mcp_srg from %s' % repr(url))
        raise


def load_official(mc_version: str) -> Tuple[str, str]:
    path = CACHE_LOCATION + 'official-%s' % mc_version
    if os.path.isdir(path):
        print('Loading %s' % path)
        with open(path + '/client.txt') as f:
            client = sanitize_utf8(f.read())
        with open(path + '/server.txt') as f:
            server = sanitize_utf8(f.read())
        return client, server

    client, server = download_official(mc_version)
    if not os.path.isdir(path):
        os.mkdir(path)
    with open(path + '/client.txt', 'w') as f:
        f.write(client)
    with open(path + '/server.txt', 'w') as f:
        f.write(server)
    return client, server


def download_official(mc_version: str, client_url: Optional[str] = None, server_url: Optional[str] = None) -> Tuple[str, str]:
    if (client_url is None or server_url is None) and mc_version not in OFFICIAL_MAPPINGS:
        print('Cannot download official mappings for %s' % mc_version)
    try:
        url = client_url if client_url is not None else OFFICIAL_MAPPINGS[mc_version]['client']
        with urllib.request.urlopen(url) as request:
            client = sanitize_utf8(request.read())

        url = server_url if server_url is not None else OFFICIAL_MAPPINGS[mc_version]['server']
        with urllib.request.urlopen(url) as request:
            server = sanitize_utf8(request.read())
        return client, server
    except:
        print('Unable to download official from %s' % repr(OFFICIAL_MAPPINGS[mc_version]))
        raise


def try_download(url: str) -> Optional[Any]:
    try:
        with urllib.request.urlopen(url) as request:
            result = request.read()
            return result, None
    except urllib.error.HTTPError as e:
        return None, e


def sanitize_utf8(text) -> str:
    if not isinstance(text, str):
        text = text.decode('utf-8')
    return text.replace('\r\n', '\n').replace('\u200c', '')
