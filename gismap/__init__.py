"""Top-level package for GisMap."""

from importlib.metadata import metadata

from gismap.sources.dblp import DBLP as DBLP
from gismap.sources.dblp import DBLPAuthor as DBLPAuthor
from gismap.sources.hal import HAL as HAL
from gismap.sources.hal import HALAuthor as HALAuthor
from gismap.utils.common import get_classes as get_classes

infos = metadata(__name__)
__version__ = infos["Version"]
__author__ = """Fabien Mathieu"""
__email__ = "fabien.mathieu@normalesup.org"


def __getattr__(name):
    if name == "GismapWidget":
        from gismap.gisgraphs.widget import GismapWidget

        return GismapWidget
    if name == "make_gismo":
        from gismap.gismo import make_gismo

        return make_gismo
    if name in {"LDB", "LDBAuthor"}:
        from gismap.sources import ldb

        return getattr(ldb, name)
    if name in {
        "Search",
        "SearchDocuments",
        "SearchFeatures",
        "SearchLandmarks",
        "search_to_html",
        "search_to_text",
    }:
        import gismap.search

        return getattr(gismap.search, name)
    raise AttributeError(f"module 'gismap' has no attribute {name!r}")
