"""Top-level package for GisMap."""

from importlib.metadata import metadata

from gismap.gisgraphs.widget import GismapWidget as GismapWidget
from gismap.gismo import make_gismo as make_gismo
from gismap.search import Search as Search
from gismap.search import SearchDocuments as SearchDocuments
from gismap.search import SearchFeatures as SearchFeatures
from gismap.search import SearchLandmarks as SearchLandmarks
from gismap.search import search_to_html as search_to_html
from gismap.search import search_to_text as search_to_text
from gismap.sources.dblp import DBLP as DBLP
from gismap.sources.dblp import DBLPAuthor as DBLPAuthor
from gismap.sources.hal import HAL as HAL
from gismap.sources.hal import HALAuthor as HALAuthor
from gismap.sources.ldb import LDB as LDB
from gismap.sources.ldb import LDBAuthor as LDBAuthor
from gismap.utils.common import get_classes as get_classes

infos = metadata(__name__)
__version__ = infos["Version"]
__author__ = """Fabien Mathieu"""
__email__ = "fabien.mathieu@normalesup.org"
