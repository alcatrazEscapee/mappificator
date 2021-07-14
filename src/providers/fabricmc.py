# Fabric
# Produces Intermediary (unique mappings) and Yarn (named mappings)
# https://github.com/FabricMC/

from parsing import tiny_parser
from util import mapping_downloader
from util.mappings import Mappings


def read_intermediary(mc_version: str) -> Mappings:
    intermediary = mapping_downloader.load_fabric_intermediary(mc_version)
    return tiny_parser.parse_tiny(intermediary)


def read_yarn(mc_version: str, yarn_version: str) -> Mappings:
    """
    Source set is intermediary, Mappings are yarn
    """
    yarn = mapping_downloader.load_yarn(mc_version, yarn_version)
    return tiny_parser.parse_tiny(yarn)
