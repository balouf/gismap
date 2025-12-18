from bs4 import BeautifulSoup as Soup

from gismap.lab import LabAuthor
from gismap.lab.lab_author import AuthorMetadata
from gismap.lab.labmap import LabMap
from gismap.utils.requests import get


def lamsade_parse(div):
    """
    Parameters
    ----------
    div: :class:`~bs4.BeautifulSoup`
        Soup of the div of one researcher

    Returns
    -------
    :class:`tuple`
        name, image url (or None), webpage (or None)
    """
    img = div.img['src'] if div.img else None
    url = div.a['href'] if div.a else None
    name = div.h2.text.strip().title()
    name = " ".join(name.split(" ", 1)[::-1])
    return name, img, url


class Lamsade(LabMap):
    """
    Class for handling the Lamsade team (Dauphine).
    """

    name = "Lamsade"
    base_url = "https://www.lamsade.dauphine.fr/"
    directory = "fr/personnes/enseignants-chercheurs-et-chercheurs.html"

    def _author_iterator(self):
        soup = Soup(get(self.base_url+self.directory), features="lxml")
        for a in soup('div', class_="dauphinecv-item"):
            name, img, url = lamsade_parse(a)
            img = self.base_url+img if img else None
            url = self.base_url+url if url else None
            yield LabAuthor(name=name, metadata=AuthorMetadata(url=url, img=img, group=self.name))
