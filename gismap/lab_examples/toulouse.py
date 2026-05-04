import re

from bs4 import BeautifulSoup as Soup

from gismap.lab.filters import editorials
from gismap.lab.lab_author import AuthorMetadata, LabAuthor
from gismap.lab.labmap import LabMap
from gismap.utils.requests import get


def name_changer(name, rosetta):
    return rosetta.get(name, name)


#: LAAS support services exposed under ``/fr/services/`` rather than ``/fr/equipes/``.
LAAS_SERVICES = ["i2c", "team", "idea"]

#: Default ``editorials`` plus institutional words that pollute LAAS publication lists
#: (annual reports, internal proceedings, etc.).
LAAS_TABOO = editorials + ["LAAS", "CNRS", "Comteam", "Prospective", "Bilan"]


class LaasMap(LabMap):
    """
    Class for handling a LAAS team from its name.
    Defaults to the `sara` team.

    Parameters
    ----------
    name: :class:`str`, default="sara"
        Team or service identifier as used in the LAAS website URLs.
    department_level: :class:`bool`, default=False
        If True, label authors by their parent department (e.g. RISC) rather than
        by their team name. Service members are labelled "Support".
    **kwargs
        Forwarded to :class:`~gismap.lab.labmap.LabMap`. The LAAS-tuned defaults
        ``max_co_authors=50`` and ``taboo_words=LAAS_TABOO`` are applied unless
        overridden by the caller.
    """

    name = "sara"
    base_url = "https://www.laas.fr"
    rosetta = {"Urtzi Ayesta Morate": "Urtzi Ayesta"}
    services = set(LAAS_SERVICES)

    def __init__(self, *args, department_level=False, **kwargs):
        self.department_level = department_level
        kwargs.setdefault("max_co_authors", 50)
        kwargs.setdefault("taboo_words", LAAS_TABOO)
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        meta = "services" if self.name in self.services else "equipes"
        soup = Soup(get(f"{self.base_url}/fr/{meta}/{self.name}/"), features="lxml")
        if self.department_level:
            if self.name in self.services:
                group = "Support"
            else:
                group = soup.find("div", {"class": "others-equipe"}).find("p", {"class": "font11"}).text.upper()
        else:
            group = self.name.upper()
        for a in soup("div", {"class": "membre"})[0]("a"):
            url = self.base_url + a["href"]
            name = name_changer(a.img["alt"], self.rosetta)
            img = self.base_url + a.img["src"] if "public_avatar" in a.img["class"] else None
            yield LabAuthor(
                name=name,
                metadata=AuthorMetadata(url=url, img=img, group=group),
            )


class LaasFull(LabMap):
    """
    Class for handling all LAAS teams using `https://www.laas.fr/fr/equipes/` to get team names.

    Parameters
    ----------
    with_support: :class:`bool`, default=True
        If True, include the support services listed in :data:`LAAS_SERVICES`
        in addition to the research teams.
    department_level: :class:`bool`, default=True
        Forwarded to :class:`LaasMap` for each team. If True, authors are
        grouped by department rather than by team.
    **kwargs
        Forwarded to :class:`~gismap.lab.labmap.LabMap`. As in :class:`LaasMap`,
        ``max_co_authors=50`` and ``taboo_words=LAAS_TABOO`` are the defaults.
    """

    name = "LAAS"

    def __init__(self, *args, with_support=True, department_level=True, **kwargs):
        self.with_support = with_support
        self.department_level = department_level
        kwargs.setdefault("max_co_authors", 50)
        kwargs.setdefault("taboo_words", LAAS_TABOO)
        super().__init__(*args, **kwargs)

    def _author_iterator(self):
        soup = Soup(get("https://www.laas.fr/fr/equipes/"), features="lxml")
        teams = [a["href"].split("/")[-2] for a in soup("a", {"class": "badge"})]
        if self.with_support:
            teams += LAAS_SERVICES
        res = dict()
        for team in sorted(teams):
            for author in LaasMap(name=team, department_level=self.department_level)._author_iterator():
                res[author.name] = author
        yield from sorted(res.values(), key=lambda a: a.metadata.group)


class SolaceMap(LabMap):
    """
    Class for handling the Solace team (`https://solace.cnrs.fr`).
    """

    name = "Solace"
    regex = re.compile(r"<li>(.*?)(,| \(|</li>)")

    def _author_iterator(self):
        html = get("https://solace.cnrs.fr/people.html", verify=False)
        for name, _ in self.regex.findall(html):
            soup = Soup(name, features="lxml")
            url = soup.a["href"] if soup.a else None
            yield LabAuthor(
                name=soup.text.strip(),
                metadata=AuthorMetadata(url=url, group=self.name.upper()),
            )
