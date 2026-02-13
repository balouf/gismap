"""Top-level package for GisMap."""

from importlib.metadata import metadata

from gismap.sources.hal import HAL as HAL, HALAuthor as HALAuthor
from gismap.sources.dblp import DBLP as DBLP, DBLPAuthor as DBLPAuthor
from gismap.sources.ldb import LDB as LDB, LDBAuthor as LDBAuthor
from gismap.utils.common import get_classes as get_classes
from gismap.gismo import make_gismo as make_gismo
from gismap.search import (
    Search as Search,
    SearchDocuments as SearchDocuments,
    SearchLandmarks as SearchLandmarks,
    SearchFeatures as SearchFeatures,
    search_to_html as search_to_html,
    search_to_text as search_to_text,
)
from gismap.gisgraphs.widget import GismapWidget as GismapWidget


infos = metadata(__name__)
__version__ = infos["Version"]
__author__ = """Fabien Mathieu"""
__email__ = "fabien.mathieu@normalesup.org"
