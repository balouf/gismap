import re
from bs4 import BeautifulSoup as Soup
from gismap.lab.lab import Lab, AuthorMetadata, LabAuthor
from gismap.utils.requests import get


def name_changer(name, rosetta):
    return rosetta.get(name, name)


class LaasLab(Lab):
    """
    Class for handling a LAAS team from its name.
    Default to `sara` team.
    """

    name = "sara"
    base_url = "https://www.laas.fr"
    rosetta = {"Urtzi Ayesta Morate": "Urtzi Ayesta"}

    def _author_iterator(self):
        soup = Soup(get(f"{self.base_url}/fr/equipes/{self.name}/"), features="lxml")
        for a in soup("div", {"class": "membre"})[0]("a"):
            url = self.base_url + a["href"]
            name = name_changer(a.img["alt"], self.rosetta)
            img = (
                self.base_url + a.img["src"]
                if "public_avatar" in a.img["class"]
                else None
            )
            yield LabAuthor(name=name, metadata=AuthorMetadata(url=url, img=img))


class Solace(Lab):
    """
    Class for handling the Solace team (`https://solace.cnrs.fr`).
    """

    name = "Solace"
    regex = re.compile(r"<li>(.*?)(,| \(|</li>)")

    def _author_iterator(self):
        html = get("https://solace.cnrs.fr/people.html")
        for name, _ in self.regex.findall(html):
            soup = Soup(name, features="lxml")
            url = soup.a["href"] if soup.a else None
            yield LabAuthor(name=soup.text.strip(), metadata=AuthorMetadata(url=url))
