from bs4 import BeautifulSoup as Soup
import re

from gismap.lab.lab import Lab
from gismap.lab.lab_author import AuthorMetadata, LabAuthor
from gismap.utils.requests import get


class Lip6Lab(Lab):
    """
    Class for handling a LIP6 team using `https://www.lip6.fr/recherche/team_membres.php?acronyme=*team_acronym*` as entry point.
    Default to `NPA` team.
    """

    name = "NPA"

    def _author_iterator(self):
        url = f"https://www.lip6.fr/recherche/team_membres.php?acronyme={self.name}"
        soup = Soup(get(url), "lxml")
        for a in soup.table("a"):
            name = a.text.replace("\xa0", " ").strip()
            if not name:
                continue
            metadata = AuthorMetadata(group=self.name)
            previous = a.find_previous_sibling()
            if previous is not None and "user" in previous.get("class", []):
                metadata.url = previous["href"].strip()
            yield LabAuthor(name=name, metadata=metadata)


class Lip6(Lip6Lab):
    """
    Class for handling all LIP6 teams using `https://www.lip6.fr/informations/annuaire.php` to get team names.
    """

    name = "LIP6"

    def _author_iterator(self):
        groups = re.compile(r'acronyme=(.*?)[\'"]')
        for group in groups.findall(
            get("https://www.lip6.fr/informations/annuaire.php")
        ):
            for author in Lip6Lab(name=group)._author_iterator():
                yield author
