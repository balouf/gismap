"""Top-level package for Analytical Lab Cartography In Computer Science."""
from importlib.metadata import metadata

infos = metadata(__name__)
__version__ = infos["Version"]
__author__ = """Fabien Mathieu"""
__email__ = 'loufab@gmail.com'


from gismap.database.hal import HALAuthor
from gismap.database.dblp import DBLPAuthor
from gismap.lab.lab import Lab
from gismap.lab.member import Member
from gismap.lab.publication import Publication
from gismap.utils.common import get_classes

from gismap.gismo import make_gismo
from gismap.search import Search, SearchDocuments, SearchLandmarks, SearchFeatures, search_to_html, search_to_text
