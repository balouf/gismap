from bs4 import BeautifulSoup as Soup
from gismap.utils.common import get_classes
from gismap.lab import LabAuthor
from gismap.lab.lab_author import AuthorMetadata
from gismap.lab.labmap import LabMap
from gismap.utils.requests import get


def strip_li(li):
    """
    Parameters
    ----------
    li: :class:`~bs4.Tag`
        HTML list item

    Returns
    -------
    :class:`str`
        Searcher name
    """
    return li.text.split(',')[0].strip()


class CoTel(LabMap):
    """
    Abstract class for Algotel/Cores PC committee maps.

    Cf https://algotel.eu.org/
    """
    year = None
    @property
    def name(self):
        return f"algotel_cores_{self.year}"


_algotel_2026 = [
    "Achour Mostéfaoui", "Anaïs Durand", "Anne-Cécile Orgerie", "Antonella Del Pozzo",
    "Arnaud Casteigts", "Arnaud Labourel", "Cédric Bentz", "Colette Johnen",
    "Cristel Pelsser", "Emmanuelle Anceaume", "Fabien Mathieu", "Gewu Bu",
    "Hervé Rivano", "Hicham Khalifé", "Isabelle Guérin Lassous", "Jérémie Chalopin",
    "Jérémie Decouchant", "Jérémie Leguay", "Joanna Moulierac", "Josiane Kouam",
    "Lélia Blin", "Marc-Olivier Buob", "Nancy Perrot", "Pascal Berthou",
    "Pascal Felber", "Sara Tucci Piergiovanni", "Sébastien Tixeuil", "Stéphane Rovedakis",
    "Swan Dubois", "Vania Conan", "Xavier Défago",
]

_cores_2026 = [
    "André-Luc Beylot", "Anne Fladenmuller", "Bertrand Ducourthial", "Emmanuel Lavinal",
    "Francesco Bronzino", "Francois Lemercier", "Gérard Chalhoub", "Ghada Jaber",
    "Hind Castel", "Juan Fraire", "Julien Montavont", "Laurent Chasserat",
    "Lynda Zitoune", "Nathalie Mitton", "Oana Iova", "Pedro Velloso",
    "Rahim Kacimi", "Razvan Stanica", "Réjane Dalce", "Sahar Hoteit",
    "Sara Berri", "Tara Yahia", "Thai-Mai-Trang Nguyen", "Thibault Cholez",
    "Véronique Vèque", "Yassine Hadjadj-Aoul",
]


class AlgoRes2026(CoTel):
    """
    2026 edition. Website not yet public; PC hardcoded from internal source.
    """
    year = 2026
    def _author_iterator(self):
        for names, group in [(_algotel_2026, "algotel"), (_cores_2026, "cores")]:
            for searcher in names:
                yield LabAuthor(name=searcher, metadata=AuthorMetadata(group=group.title()))


class AlgoRes2025(CoTel):
    """
    https://algotel-cores25.sciencesconf.org/
    """
    year = 2025
    def _author_iterator(self):
        for i, group in [(13, "cores"), (9, "algotel")]:
            soup = Soup(get(f"https://algotel-cores25.sciencesconf.org/resource/page/id/{i}"), features="lxml")
            for searcher in [strip_li(li) for li in soup.ul("li")]:
                yield LabAuthor(name=searcher, metadata=AuthorMetadata(group=group.title()))


class AlgoRes2024(CoTel):
    """
    https://algotelcores2024.sciencesconf.org
    """
    year = 2024
    def _author_iterator(self):
        for group in ["cores", "algotel"]:
            soup = Soup(get(f"https://algotelcores2024.sciencesconf.org/data/{group}.html", encoding="utf-8"), features="lxml")
            for searcher in soup("ul", {"class": "person"}):
                yield LabAuthor(name=strip_li(searcher.li), metadata=AuthorMetadata(group=group.title()))


class AlgoRes2023(CoTel):
    """
    https://coresalgotel2023.i3s.univ-cotedazur.fr
    """
    year = 2023
    def _author_iterator(self):
        soup = Soup(get("https://coresalgotel2023.i3s.univ-cotedazur.fr/comites.html", encoding="utf-8"), features="lxml")
        for group, searchers in zip(["algotel", "cores"], [ul("li") for ul in soup.table("ul")]):
            for searcher in searchers:
                yield LabAuthor(name=strip_li(searcher), metadata=AuthorMetadata(group=group.title()))


class AlgoRes2022(CoTel):
    """
    https://sites.google.com/view/algotel-cores-2022
    """
    year = 2022
    def _author_iterator(self):
        for group in ["cores", "algotel"]:
            soup = Soup(get(f"https://sites.google.com/view/algotel-cores-2022/{group}-2022/comités"), features="lxml")
            for searcher in soup("ul")[-1]("li"):
                yield LabAuthor(name=strip_li(searcher), metadata=AuthorMetadata(group=group.title()))


class AlgoRes2021(CoTel):
    """
    https://apps.univ-lr.fr/cgi-bin/WebObjects/Colloque.woa/wa/menu?code=2721&idMenu=10922
    """
    year = 2021
    def _author_iterator(self):
        for i, group in [(10953, "cores"), (10947, "algotel")]:
            soup = Soup(get(f"https://apps.univ-lr.fr/cgi-bin/WebObjects/Colloque.woa/wa/menu?code=2721&idMenu={i}"), features="lxml")
            for searcher in soup("ul")[-1]("li"):
                yield LabAuthor(name=strip_li(searcher), metadata=AuthorMetadata(group=group.title()))


class AlgoRes2020(CoTel):
    """
    https://cores-algotel-2020.imag.fr/
    """
    year = 2020
    rosetta = {"Eric": "Éric Gourdin"}

    def _author_iterator(self):
        for i, group in [("index188e.html?page_id=73", "cores"), ("index4404.html?page_id=70", "algotel")]:
            soup = Soup(get(f"https://cores-algotel-2020.imag.fr/{i}", encoding="utf-8"), features="lxml")
            for searcher in soup.ul("li"):
                searcher = strip_li(searcher)
                searcher = self.rosetta.get(searcher, searcher)
                yield LabAuthor(name=searcher, metadata=AuthorMetadata(group=group.title()))


class AlgoRes2019(CoTel):
    """
    https://www.irit.fr/algotel2019/
    https://www.irit.fr/cores2019/index.html
    """
    year = 2019
    def _author_iterator(self):
        for url, group in [
            ("https://www.irit.fr/algotel2019/", "algotel"),
            ("https://www.irit.fr/cores2019/index.html", "cores"),
        ]:
            soup = Soup(get(url), features="lxml")
            for h3 in soup("h3"):
                if "programme" in h3.text.lower():
                    for p in h3.find_next_sibling("div")("p"):
                        yield LabAuthor(name=p.text.split(",")[0].strip(), metadata=AuthorMetadata(group=group.title()))
                    break


class AlgoRes2018(CoTel):
    """
    https://algotel2018.complexnetworks.fr/comite.html
    http://cores2018.complexnetworks.fr/comite.html
    """
    year = 2018
    rosetta = {"Gourdin": "Eric Gourdin", "Carneiro Viana": "Aline Carneiro Viana"}
    def _author_iterator(self):
        # Algotel: <p> tags after "Comité de programme" h2
        soup = Soup(get("https://algotel2018.complexnetworks.fr/comite.html", encoding="utf-8"), features="lxml")
        for h in soup("h2"):
            if "programme" in h.text.lower():
                for p in h.find_next_siblings("p"):
                    name = p.text.split(",")[0].strip()
                    name = self.rosetta.get(name, name)
                    yield LabAuthor(name=name, metadata=AuthorMetadata(group="Algotel"))
                break
        # Cores: <p> tags directly (single section page)
        soup = Soup(get("http://cores2018.complexnetworks.fr/comite.html", encoding="utf-8"), features="lxml")
        for p in soup("p"):
            name = p.text.split(",")[0].strip()
            if name:
                yield LabAuthor(name=name, metadata=AuthorMetadata(group="Cores"))


_algotel_2017 = [
    "Aline Carneiro Viana", "Stephane Devismes", "Karine Altisen", "Emmanuelle Anceaume",
    "Farid Benbadis", "Janna Burman", "Arnaud Casteigts", "Hakima Chaouchi",
    "David Coudert", "Sylvie Delaet", "Yoann Dieudonne", "Hugues Fauconnier",
    "Emmanuel Godard", "Vincent Gramoli", "Frederic Guinand", "Luis Henrique",
    "Sahar Hoteit", "Luigi Iannone", "Oana Iova", "Hicham Khalife",
    "Ralf Klasing", "Pascal Lafourcade", "Patrick Maille", "Nathalie Mitton",
    "Achour Mostefaoui", "Anelise Munaretto", "Franck Petit", "Stephane Rovedakis",
    "Damien Saucez", "Thomas Silverston", "Fabrice Theoleyre", "Gilles Tredan",
    "Artur Ziviani",
]

_cores_2017 = [
    "Franck Rousseau", "Fabrice Valois", "Dominique Barthel", "Andre-Luc Beylot",
    "Yann Busnel", "Isabelle Chrisment", "Vania Conan", "Marcelo Dias de Amorim",
    "Bertrand Ducourthial", "Andrzej Duda", "Eric Fleury", "Jean-Loup Guillaume",
    "Fabrice Guillemin", "Alexandre Guitton", "Katia Jaffres-Runser", "Houda Labiod",
    "Xavier Lagrange", "Pascale Minet", "Nathalie Mitton", "Thomas Noel",
    "Georgios Papadopoulos", "Cristel Pellser", "Bruno Quoitin", "Razvan Stanica",
    "Thierry Turletti", "Pascal Thubert", "Guillaume Urvoy-Keller", "Veronique Veque",
]


class AlgoRes2017(CoTel):
    """
    https://web.archive.org/web/20170719001105/http://algotel2017.ensai.fr/
    https://web.archive.org/web/20171203000444/http://cores2017.ensai.fr/
    """
    year = 2017
    def _author_iterator(self):
        for names, group in [(_algotel_2017, "algotel"), (_cores_2017, "cores")]:
            for searcher in names:
                yield LabAuthor(name=searcher, metadata=AuthorMetadata(group=group.title()))


class AlgoRes2016(CoTel):
    """
    https://algotel2016.labri.fr/index.php?committee
    https://algotel2016.labri.fr/index.php?cores
    """
    year = 2016
    rosetta = {"Laurent Viennot LIAFA": "Laurent Viennot"}
    def _author_iterator(self):
        # Algotel: committee names in the largest <ul> with 30 <li>
        soup = Soup(get("https://algotel2016.labri.fr/index.php?committee"), features="lxml")
        ul = max(soup("ul"), key=lambda u: len(u("li")))
        for li in ul("li"):
            name = strip_li(li)
            name = self.rosetta.get(name, name)
            yield LabAuthor(name=name, metadata=AuthorMetadata(group="Algotel"))
        # Cores: <p> tags after "Comité scientifique" h3
        soup = Soup(get("https://algotel2016.labri.fr/index.php?cores"), features="lxml")
        for h in soup("h3"):
            if "scientifique" in h.text.lower():
                for p in h.find_next_siblings("p"):
                    name = p.text.split(",")[0].strip()
                    if name:
                        yield LabAuthor(name=name, metadata=AuthorMetadata(group="Cores"))
                break


cotels = get_classes(CoTel, key="year")
