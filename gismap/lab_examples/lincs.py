from bs4 import BeautifulSoup as Soup

from gismap.lab import LabAuthor
from gismap.lab.filters import re_filter
from gismap.lab.labmap import LabMap as Map
from gismap.utils.requests import get

ghosts = [
    "Altman",
    "Lelarge",
    "Teixera",
    "Friedman",
    "Fdida",
    "Blaszczyszyn",
    "Jacquet",
    "Panafieu",
    "Bušić",
    "Durand",
]
no_ghost = re_filter(ghosts)


class LINCS(Map):
    name = "LINCS"

    def _author_iterator(self):
        soup = Soup(get("https://www.lincs.fr/people/"), features="lxml")
        for entry in soup.main("div", class_="trombinoscope-row"):
            cols = entry("div")
            name = cols[1].text
            if not no_ghost(name):
                continue
            img = cols[0].img["src"]
            url = cols[-1].a
            if url:
                url = url.get("href")
            group = cols[2]("a")
            if group:
                group = group[-1].text
            else:
                group = "External"
            author = LabAuthor(name)
            author.metadata.img = img
            author.metadata.group = group
            author.metadata.url = url
            yield author
