from bs4 import BeautifulSoup as Soup
from gismap.utils.requests import get
from gismap.lab.filters import re_filter
from gismap.lab import LabAuthor, Map


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
]
no_ghost = re_filter(ghosts)


class LINCS(Map):
    name = "LINCS"

    def _author_iterator(self):
        soup = Soup(get("https://www.lincs.fr/people/"))
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
                group = None
            author = LabAuthor(name)
            author.metadata.img = img
            author.metadata.group = group
            author.metadata.url = url
            yield author
