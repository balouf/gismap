import requests
from bs4 import BeautifulSoup as Soup
from gismap.lab.labmap import LabMap
from gismap.lab.lab_author import AuthorMetadata, LabAuthor
from gismap.utils.requests import get


class CedricMap(LabMap):
    """
    Class for handling a CNAM Cedric team from its name.
    Default to `roc` team.
    """

    name = "roc"
    base_url = "https://cedric.cnam.fr"

    def _author_iterator(self):
        soup = Soup(get(f"{self.base_url}/equipes/{self.name}/"), features="lxml")
        searchers = [
            li.a
            for ul in soup.find("div", {"id": "annuaire"})("ul")[:3]
            for li in ul("li")
        ]
        done = set()
        for searcher in searchers:
            name = searcher.text.split("(")[0].strip()
            if name in done:
                continue
            url = f"{self.base_url}{searcher['href']}"
            sousoup = Soup(get(url), features="lxml")
            img = sousoup.find("img", {"class": "photo"})["src"]
            response = requests.head(img, allow_redirects=True)
            if int(response.headers.get("Content-Length")) < 3000:
                img = None
            done.add(name)
            yield LabAuthor(
                name=name,
                metadata=AuthorMetadata(url=url, img=img, group=self.name.upper()),
            )


class CedricFull(LabMap):
    """
    Class for handling all CNAM Cedric teams using `https://cedric.cnam.fr/equipes` to get team names.
    """

    name = "Cedric"

    def _author_iterator(self):
        base = "https://cedric.cnam.fr/equipes/"
        soup = Soup(get(base), features="lxml")
        teams = {
            a["href"].split("/")[-2]
            for a in soup("a")
            if base in a.get("href", "") and len(a["href"]) > len(base)
        }
        for team in teams:
            for author in CedricMap(name=team)._author_iterator():
                yield author
