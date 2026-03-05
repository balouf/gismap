from bs4 import BeautifulSoup as Soup

from gismap.lab.labmap import LabMap
from gismap.lab.lab_author import AuthorMetadata, LabAuthor
from gismap.utils.requests import get


def get_irif_teams():
    soup = Soup(get("https://www.irif.fr/"), "lxml")
    teams = [a for a in soup("ul", {"class": "nav"})[1]("a") if hasattr(a, "href") and "equipes" in a["href"]]
    return {a["href"].split("/")[-2]: a.text.strip() for a in teams}


irif_teams = get_irif_teams()


class IrifMap(LabMap):
    """
    Class for handling an IRIF team using `https://www.irif.fr/equipes/*team_acronym*/index` as entry point.
    Default to `graphes` team.
    """

    name = "graphes"

    def _author_iterator(self):
        url = f"https://www.irif.fr/equipes/{self.name}/index"
        soup = Soup(get(url), "lxml")
        for a in [td.a for td in soup("td", {"class": "col0"})]:
            if a is None:
                continue
            name = a.text.replace("\xa0", " ").strip()
            if not name:
                continue
            metadata = AuthorMetadata(group=irif_teams[self.name], url=a["href"])
            yield LabAuthor(name=name, metadata=metadata)


class IrifFull(IrifMap):
    """
    Class for handling all IRIF teams.
    """

    name = "IRIF"

    def _author_iterator(self):
        author_dict = dict()
        for team in irif_teams:
            for author in IrifMap(name=team)._author_iterator():
                if author.name in author_dict:
                    author_dict[author.name].metadata.group = "Polyteam"
                else:
                    author_dict[author.name] = author
        for author in author_dict.values():
            yield author
