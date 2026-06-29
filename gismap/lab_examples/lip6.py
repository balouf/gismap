import re

from bs4 import BeautifulSoup as Soup

from gismap.lab.lab_author import AuthorMetadata, LabAuthor
from gismap.lab.labmap import LabMap
from gismap.utils.requests import get


def given_name_first(name):
    """Reorder a LIP6 ``"Surname Given(s)"`` label into ``"Given(s) Surname"``.

    LIP6 lists members surname-first, but the rest of GisMap assumes
    given-name-first (for initials and display). We treat the **first** token as
    the surname and move it to the end, which handles the common single-token
    surname as well as multi-token given names (e.g. ``"Lieu Choun Tong"`` ->
    ``"Choun Tong Lieu"``). Single-token names are returned unchanged. Compound
    surnames (rare here) would need an explicit override.
    """
    tokens = name.split()
    if len(tokens) < 2:
        return name
    return " ".join(tokens[1:] + tokens[:1])


class Lip6Map(LabMap):
    """
    Class for handling a LIP6 team using
    `https://www.lip6.fr/recherche/team_membres.php?acronyme=*team_acronym*` as entry point.
    Default to `NPA` team.
    """

    name = "NPA"
    overrides = {"Antoine Mirri": "drop"}

    def _author_iterator(self):
        url = f"https://www.lip6.fr/recherche/team_membres.php?acronyme={self.name}"
        soup = Soup(get(url), "lxml")
        for a in soup.table("a"):
            name = a.text.replace("\xa0", " ").strip()
            if not name:
                continue
            name = given_name_first(name)
            metadata = AuthorMetadata(group=self.name)
            previous = a.find_previous_sibling()
            if previous is not None and "user" in previous.get("class", []):
                metadata.url = previous["href"].strip()
            fiche = "https://www.lip6.fr/" + a["href"].split("/", 1)[1]
            img = Soup(get(fiche), "lxml").img
            if img and "reflet" in img["class"] and "noPhoto" not in img["src"]:
                metadata.img = "https://www.lip6.fr/" + img["src"].split("/", 1)[1]
            yield LabAuthor(name=name, metadata=metadata)


class Lip6Full(Lip6Map):
    """
    Class for handling all LIP6 teams using `https://www.lip6.fr/informations/annuaire.php` to get team names.
    """

    name = "LIP6"

    def _author_iterator(self):
        groups = re.compile(r'acronyme=(.*?)[\'"]')
        for group in groups.findall(get("https://www.lip6.fr/informations/annuaire.php")):
            yield from Lip6Map(name=group)._author_iterator()
