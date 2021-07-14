# Architectury
# Produces a mojmap-named mappings project
# https://github.com/Architectury/Crane

from parsing import tiny_parser
from util import mapping_downloader
from util.mappings import Mappings


def read_crane(mc_version: str, crane_version: str) -> Mappings:
    """
    Source set is mojmap, mappings are parameters and javadocs only
    """
    text = mapping_downloader.load_crane(mc_version, crane_version)
    return tiny_parser.parse_tiny(text)
