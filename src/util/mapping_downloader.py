# Simple one-time downloader for various minecraft mappings sources and files
# Caches all downloaded files locally

import io
import json
import os
import urllib.error
import urllib.request
import zipfile

from typing import Tuple, Optional, Any, Dict

FABRIC_YARN_URL = 'https://maven.fabricmc.net/net/fabricmc/yarn/%s+build.%s/yarn-%s+build.%s-v2.jar'
FABRIC_INTERMEDIARY_URL = 'https://raw.githubusercontent.com/FabricMC/intermediary/master/mappings/%s.tiny'
FORGE_MCP_CONFIG_URL = 'https://files.minecraftforge.net/maven/de/oceanlabs/mcp/mcp_config/%s/mcp_config-%s.zip'
PARCHMENT_BLACKSTONE_URL = 'https://maven.parchmentmc.org/org/parchmentmc/data/blackstone/%s/blackstone-%s.zip'
PARCHMENT_URL = 'https://maven.parchmentmc.org/org/parchmentmc/data/parchment-%s/%s/parchment-%s-%s.zip'
OFFICIAL_MANIFEST_URL = 'https://launchermeta.mojang.com/mc/game/version_manifest.json'

FABRIC_YARN_CACHE = 'yarn_v2-%s+build.%s.tiny'
FABRIC_INTERMEDIARY_CACHE = 'yarn_intermediary-%s.tiny'
MCP_CONFIG_CACHE = 'mcpconfig-%s'
PARCHMENT_BLACKSTONE_CACHE = 'blackstone-%s.json'
PARCHMENT_CACHE = 'parchment-%s-%s.json'
OFFICIAL_MANIFEST_CACHE = 'official-manifest.json'
OFFICIAL_VERSION_MANIFEST_CACHE = 'official-manifest-%s.json'
OFFICIAL_MAPPING_CACHE = 'official-%s'
CORRECTIONS_CACHE = 'corrections-%s.json'

PATH = '../build'

os.makedirs(PATH, exist_ok=True)


def load_yarn(mc_version: str, yarn_version: str) -> str:
    path = FABRIC_YARN_CACHE % (mc_version, yarn_version)
    if is_cached(path):
        return load_text(path)

    data = download(FABRIC_YARN_URL % (mc_version, yarn_version, mc_version, yarn_version))
    with io.BytesIO(data) as fio:
        with zipfile.ZipFile(fio, 'r') as tiny_zip:
            with tiny_zip.open('mappings/mappings.tiny') as f:
                mappings = as_text(f.read())

    save_text(path, mappings)
    return mappings


def load_fabric_intermediary(mc_version: str) -> str:
    path = FABRIC_INTERMEDIARY_CACHE % mc_version
    if is_cached(path):
        return load_text(path)

    mappings = as_text(download(FABRIC_INTERMEDIARY_URL % mc_version))
    save_text(path, mappings)
    return mappings


def load_mcpconfig(mc_version: str) -> Tuple[str, str, str]:
    path = MCP_CONFIG_CACHE % mc_version
    if is_cached(path):
        return load_text(path + '/joined.tsrg'), load_text(path + '/static_methods.txt'), load_text(path + '/constructors.txt')

    data = download(FORGE_MCP_CONFIG_URL % (mc_version, mc_version))
    joined, static_methods, constructors = extract_from_zip(data, 'config/joined.tsrg', 'config/static_methods.txt', 'config/constructors.txt')

    save_text(path + '/joined.tsrg', joined)
    save_text(path + '/static_methods.txt', static_methods)
    save_text(path + '/constructors.txt', constructors)
    return joined, static_methods, constructors


def load_blackstone(mc_version: str) -> Dict[str, Any]:
    path = PARCHMENT_BLACKSTONE_CACHE % mc_version
    if is_cached(path):
        return json.loads(load_text(path))

    data = download(PARCHMENT_BLACKSTONE_URL % (mc_version, mc_version))
    mappings, *_ = extract_from_zip(data, 'merged.json')
    save_text(path, mappings)
    return json.loads(mappings)


def load_parchment(mc_version: str, parchment_version: str) -> Dict[str, Any]:
    path = PARCHMENT_CACHE % (mc_version, parchment_version)
    if is_cached(path):
        return json.loads(load_text(path))

    data = download(PARCHMENT_URL % (mc_version, parchment_version, mc_version, parchment_version))
    mappings, *_ = extract_from_zip(data, 'parchment.json')
    save_text(path, mappings)
    return json.loads(mappings)


def load_official(mc_version: str) -> Tuple[str, str]:
    def load_manifest(use_cache: bool = True) -> Tuple[Dict, bool]:
        if is_cached(OFFICIAL_MANIFEST_CACHE) and use_cache:
            return json.loads(load_text(OFFICIAL_MANIFEST_CACHE)), True
        else:
            manifest = as_text(download(OFFICIAL_MANIFEST_URL))
            save_text(OFFICIAL_MANIFEST_CACHE, manifest)
            return json.loads(manifest), False

    def find_game_version_manifest_matching(manifest_json_in: Dict, mc_version_in: str) -> Optional[str]:
        for game_version_json in manifest_json_in['versions']:
            if game_version_json['id'] == mc_version_in:
                return game_version_json['url']
        return None

    # Check the official mapping cache
    mapping_path = OFFICIAL_MAPPING_CACHE % mc_version
    if is_cached(mapping_path):
        return load_text(mapping_path + '/client.txt'), load_text(mapping_path + '/server.txt')

    # Need to download the official mappings. Check if the version manifest is present
    version_meta_path = OFFICIAL_VERSION_MANIFEST_CACHE % mc_version
    if is_cached(version_meta_path):
        # Load the version manifest, in order to get the mapping urls
        version_meta_json = json.loads(load_text(version_meta_path))
    else:
        # No version manifest, so load the full manifest
        manifest_json, was_cached = load_manifest()

        # Find the version manifest matching the mc version
        version_manifest_url = find_game_version_manifest_matching(manifest_json, mc_version)

        # If not found, and the manifest was cached, then reload the manifest without caching and try again
        # This is as the manifest might need to be refreshed for new version releases of Minecraft
        if version_manifest_url is None and was_cached:
            manifest_json, was_cached = load_manifest(False)
            version_manifest_url = find_game_version_manifest_matching(manifest_json, mc_version)

        # Should now have a version manifest location
        assert version_manifest_url is not None, 'No manifest entry for game version %s' % mc_version

        # Download and save manifest
        version_manifest = as_text(download(version_manifest_url))
        save_text(version_meta_path, version_manifest)

        version_meta_json = json.loads(version_manifest)

    # Identify urls for mappings
    client_url = version_meta_json['downloads']['client_mappings']['url']
    server_url = version_meta_json['downloads']['server_mappings']['url']

    # Load official mappings
    client, server = as_text(download(client_url)), as_text(download(server_url))

    # And save to cache
    save_text(mapping_path + '/client.txt', client)
    save_text(mapping_path + '/server.txt', server)

    return client, server


def load_corrections(mc_version: str) -> Dict[str, str]:
    path = CORRECTIONS_CACHE % mc_version
    if is_cached(path):
        return json.loads(load_text(path))

    save_text(path, '{}\n')
    return {}


# Utility functions
# Writing / Reading from files, common cache functionality, etc.

def is_cached(file_path: str) -> bool:
    path = os.path.join(PATH, file_path)
    return os.path.isfile(path) or os.path.isdir(path)


def load_text(file_path: str) -> str:
    path = os.path.join(PATH, file_path)
    try:
        with open(path, 'r') as f:
            text = f.read()
        return text
    except OSError as e:
        raise Exception('Loading %s' % repr(file_path)) from e


def save_text(file_path: str, text: str):
    path = os.path.join(PATH, file_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


def download(url: str) -> Any:
    try:
        with urllib.request.urlopen(url) as request:
            res = request.read()
        return res
    except urllib.error.HTTPError as e:
        raise Exception('Requested %s' % url) from e


def as_text(raw: Any) -> str:
    if not isinstance(raw, str):
        raw = raw.decode('utf-8')
    return raw.replace('\r\n', '\n').replace('\u200c', '')


def extract_from_zip(raw: Any, *files: str) -> Tuple[str, ...]:
    results = []
    try:
        with io.BytesIO(raw) as fio:
            with zipfile.ZipFile(fio, 'r') as zip_io:
                for file in files:
                    with zip_io.open(file) as f:
                        results.append(as_text(f.read()))
    except Exception as e:
        raise Exception('Extracting %s' % repr(files)) from e
    return tuple(results)
