from html import escape

import numpy as np
from gismo.gismo import XGismo

from gismap.utils.fuzzy import similarity_matrix


def make_post_publi(lab):
    """
    Hook to turn publication key stored in a corpus into actual publication.

    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        Lab that contains the corpus publications.

    Returns
    -------
    callable
    """

    def to_bib(g, i):
        item = g.corpus[i]
        return lab.publications[item]

    return to_bib


def make_gismo(lab, vectorizer_parameters=None):
    """
    Makes a gismo out of a lab.

    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        Lab that contains publications.
    vectorizer_parameters: :class:`dict`
        Overriding parameters for the Countvectorizer of the gismo.

    Returns
    -------
    gismo: :class:`~gismo.gismo.Gismo`
        Gismo of the lab.
    """
    from gismo.corpus import Corpus
    from gismo.embedding import Embedding
    from gismo.gismo import Gismo
    from sklearn.feature_extraction.text import CountVectorizer

    parameters = {"ngram_range": (1, 3), "dtype": float, "stop_words": sw, "min_df": 3}
    if vectorizer_parameters is not None:
        parameters.update(vectorizer_parameters)
    corpus = Corpus([p for p in lab.publications], to_text=lab.publi_to_text)
    vectorizer = CountVectorizer(**parameters)
    embedding = Embedding(vectorizer=vectorizer)
    embedding.fit_transform(corpus)
    gismo = Gismo(corpus, embedding)
    gismo.post_documents_item = make_post_publi(lab)
    return gismo


def publication_text(pub):
    """Text used for keyword extraction: title plus the first available abstract.

    Parameters
    ----------
    pub: :class:`~gismap.sources.models.Publication`
        A publication (typically a :class:`~gismap.sources.multi.SourcedPublication`).

    Returns
    -------
    :class:`str`
    """
    title = getattr(pub, "title", "") or ""
    abstract = ""
    for source in getattr(pub, "sources", None) or []:
        md = getattr(source, "metadata", None)
        if isinstance(md, dict) and md.get("abstract"):
            abstract = md["abstract"]
            break
    if not abstract:
        md = getattr(pub, "metadata", None)
        if isinstance(md, dict) and md.get("abstract"):
            abstract = md["abstract"]
    return f"{title}\n\n{abstract}" if abstract else title


def publication_author_keys(pub):
    """Author keys of a publication (the tokens of the author-side embedding)."""
    return [a.key for a in getattr(pub, "authors", None) or [] if getattr(a, "key", None)]


class WordCloud:
    """A set of ``(word, weight)`` pairs with a self-contained HTML rendering.

    Displays natively in notebooks via ``_repr_html_`` (font size and colour
    follow the weight); :meth:`to_html` / :meth:`save_html` produce a standalone
    snippet with no external dependency.

    Parameters
    ----------
    words: :class:`list`
        ``(word, weight)`` pairs, expected in descending weight order.
    title: :class:`str`, optional
        Caption shown above the cloud.
    """

    def __init__(self, words, title=None):
        self.words = list(words)
        self.title = title

    def __repr__(self):
        return f"WordCloud({len(self.words)} words)"

    def __iter__(self):
        return iter(self.words)

    def to_html(self, min_size=12, max_size=46):
        """Render the cloud as a self-contained HTML string."""
        if not self.words:
            return '<div class="gismap-wordcloud"><em>No keywords.</em></div>'
        weights = [w for _, w in self.words]
        lo, span = min(weights), (max(weights) - min(weights)) or 1.0
        n = len(self.words)
        spans = []
        for rank, (word, weight) in enumerate(self.words):
            t = (weight - lo) / span  # 0..1 by weight
            size = min_size + (max_size - min_size) * (t**0.5)
            hue = int(205 + 80 * (rank / max(1, n - 1)))  # blue -> violet by rank
            # hsl colours are readable on both light and dark backgrounds.
            spans.append(
                f'<span style="display:inline-block;margin:0.1em 0.32em;line-height:1.15;'
                f"font-size:{size:.1f}px;font-weight:{400 + int(300 * t)};"
                f'color:hsl({hue},62%,55%);" title="{escape(f"{weight:.4g}")}">{escape(word)}</span>'
            )
        header = (
            f'<div style="font-size:0.85em;opacity:0.7;margin-bottom:0.5em;color:inherit;">{escape(self.title)}</div>'
            if self.title
            else ""
        )
        return (
            '<div class="gismap-wordcloud" style="padding:14px 18px;border-radius:10px;'
            "border:1px solid rgba(127,127,127,0.25);background:rgba(127,127,127,0.06);"
            'text-align:center;">'
            f"{header}<div>{''.join(spans)}</div></div>"
        )

    def _repr_html_(self):
        return self.to_html()

    def save_html(self, name):
        """Write the cloud to a standalone ``.html`` file."""
        from pathlib import Path

        path = Path(name).with_suffix(".html")
        with open(path, "w", encoding="utf8") as f:
            f.write(f"<!doctype html><html><head><meta charset='utf-8'></head><body>{self.to_html()}</body></html>")


class GismoLab(XGismo):
    """Cross-embedding of a lab's authors and the words of their publications.

    Built on Gismo's :class:`~gismo.gismo.XGismo`, it relates authors to the
    vocabulary of their work, so a single object answers keyword queries by
    topic, by author, by group, or for the whole lab. Building it embeds every
    publication twice (words and authors), so reuse one instance across queries
    rather than rebuilding per call (e.g. ``LabMap.wordcloud`` rebuilds each time).

    Parameters
    ----------
    lab: :class:`~gismap.lab.labmap.LabMap`
        A populated lab (``update_publis`` / ``build`` must have run).
    ngram_range: :class:`tuple`, default=(1, 3)
        N-gram range for the keyword vectorizer.
    stop_words: :class:`list`, optional
        Stop words for the keyword vectorizer. Defaults to the package list
        (English + French + academic noise).
    """

    def __init__(self, lab, ngram_range=(1, 3), stop_words=None):
        from gismo.corpus import Corpus
        from gismo.embedding import Embedding
        from sklearn.feature_extraction.text import CountVectorizer

        if not getattr(lab, "publications", None):
            raise ValueError("Lab has no publications; run build()/update_publis() first.")
        if stop_words is None:
            stop_words = sw
        pubs = list(lab.publications.values())

        text_embedding = Embedding(
            vectorizer=CountVectorizer(dtype=float, ngram_range=ngram_range, stop_words=stop_words)
        )
        text_embedding.fit_transform(Corpus(pubs, to_text=publication_text))

        a_embedding = Embedding(
            vectorizer=CountVectorizer(dtype=float, preprocessor=lambda x: x, tokenizer=lambda x: x, token_pattern=None)
        )
        a_embedding.fit_transform(Corpus(pubs, to_text=publication_author_keys))

        super().__init__(x_embedding=a_embedding, y_embedding=text_embedding)
        self.author_dict = {a.key: a for p in pubs for a in (p.authors or []) if getattr(a, "key", None)}
        self.post_features_item = lambda g, i: (g.embedding.features[i], g.diteration.y_relevance[i])

    def _group_keys(self, group):
        return [k for k, a in self.author_dict.items() if getattr(getattr(a, "metadata", None), "group", None) == group]

    def keywords(self, query=None, group=None, y=True, k=50, threshold=50, length_impact=0.1):
        """Return ranked ``(word, weight)`` pairs, with near-duplicate n-grams merged.

        Parameters
        ----------
        query: :class:`str` or :class:`list`, optional
            A text query (``y=True``), or a list of author keys (``y=False``).
            Defaults to the whole lab (empty query).
        group: :class:`str`, optional
            Restrict to the authors of this group (overrides ``query``).
        y, k, threshold, length_impact:
            Ranking and de-duplication tuning (see Gismo / similarity_matrix).
        """
        if group is not None:
            query, y = self._group_keys(group), False
            if not query:
                return []
        if query is None:
            query = ""
        self.rank(query, y=y)
        # Sort colocations first so a low length_impact regroups subsequences
        # ("p2p" absorbed by "p2p networks") instead of listing them separately.
        r = sorted(self.get_features_by_rank(k=k), key=lambda item: -len(item[0]))
        if not r:
            return []
        jc = similarity_matrix(r, key=lambda x: x[0], length_impact=length_impact)
        done = np.zeros(len(r), dtype=bool)
        words = []
        for i in range(len(r)):
            if done[i]:
                continue
            locs = [j for j in np.where(jc[i, :] > threshold)[0] if not done[j]]
            done[locs] = True
            words.append((r[locs[0]][0], sum(r[j][1] for j in locs)))
        return sorted(words, key=lambda w: -w[1])

    def wordcloud(self, query=None, group=None, **kwargs):
        """Like :meth:`keywords`, but wrapped in a renderable :class:`WordCloud`."""
        if group is not None:
            title = f"Keywords — group “{group}”"
        elif isinstance(query, str) and query:
            title = f"Keywords — “{query}”"
        elif query:
            title = "Keywords — selected authors"
        else:
            title = "Keywords — whole lab"
        return WordCloud(self.keywords(query=query, group=group, **kwargs), title=title)


stop_words = [
    "01",
    "20plus",
    "academia",
    "academic",
    "academy",
    "académie",
    "acm",
    "activities",
    "actualités",
    "adresse",
    "advances",
    "affichertoutesdepuis",
    "ajouter",
    "an",
    "ancitations",
    "and",
    "annual",
    "annéetrier",
    "antipolis",
    "are",
    "article",
    "articledisponiblesnon",
    "articles",
    "articles0",
    "arxiv",
    "as",
    "astérisque",
    "at",
    "attended",
    "au",
    "auteuradresse",
    "auteurnouveaux",
    "auteurnouvelles",
    "aux",
    "award",
    "awarded",
    "awards",
    "base",
    "based",
    "be",
    "been",
    "bibliography",
    "bibliothèquemétriquesalertesparamètresconnexionconnexionobtenir",
    "board",
    "book",
    "born",
    "by",
    "california",
    "called",
    "can",
    "celles",
    "centrale",
    "centre",
    "ces",
    "cet",
    "cette",
    "chair",
    "chaussées",
    "ciarlet",
    "citations",
    "citationstrier",
    "cited",
    "citée",
    "cnrs",
    "cnrsadresse",
    "coauteurscoauteurssuivre",
    "collaboration",
    "colloquium",
    "collège",
    "columbia",
    "committee",
    "comptabilisées",
    "conference",
    "contact",
    "contributions",
    "council",
    "cours",
    "course",
    "courses",
    "dans",
    "de",
    "des",
    "diegoadresse",
    "différentes",
    "director",
    "disponiblessur",
    "doi",
    "données",
    "doubleles",
    "du",
    "décompte",
    "early",
    "earned",
    "ecole",
    "ed",
    "edinburgh",
    "elected",
    "en",
    "english",
    "ens",
    "envoi",
    "et",
    "europaea",
    "european",
    "events",
    "exigences",
    "fellow",
    "financementcoauteurstout",
    "for",
    "formerly",
    "forum",
    "fr",
    "france",
    "franceadresse",
    "français",
    "françois",
    "french",
    "from",
    "fusionnéesle",
    "fusionnés",
    "google",
    "grenoble",
    "gérard",
    "habilitation",
    "had",
    "he",
    "her",
    "here",
    "highly",
    "his",
    "home",
    "hong",
    "honorary",
    "ici",
    "ieee",
    "imag",
    "in",
    "inclut",
    "informatique",
    "innovation",
    "inria",
    "insa",
    "institut",
    "international",
    "invited",
    "is",
    "isbn",
    "it",
    "je",
    "jean",
    "jour",
    "journal",
    "july",
    "known",
    "kong",
    "la",
    "lab",
    "le",
    "lecture",
    "les",
    "lille",
    "liées",
    "liés",
    "lncs",
    "lyon",
    "mail",
    "maintenant",
    "medal",
    "media",
    "member",
    "mises",
    "mon",
    "monde",
    "my",
    "mécanique",
    "national",
    "ne",
    "nombre",
    "normale",
    "notes",
    "notificationsokmon",
    "novel",
    "of",
    "olivier",
    "on",
    "opération",
    "ordre",
    "page",
    "pages",
    "paper",
    "par",
    "paraccès",
    "parcitée",
    "paris",
    "paristech",
    "partout",
    "pas",
    "pdf",
    "peut",
    "peuvent",
    "peux",
    "ph",
    "phd",
    "pierre",
    "plus",
    "polytechnique",
    "ponts",
    "pour",
    "pp",
    "premier",
    "preprint",
    "president",
    "prix",
    "prize",
    "proceedings",
    "professor",
    "profil",
    "profilcitée",
    "profilma",
    "programme",
    "programmes",
    "propre",
    "présentation",
    "publications",
    "publiccoauteurstitretriertrier",
    "published",
    "que",
    "qui",
    "received",
    "recherche",
    "record",
    "report",
    "research",
    "researcher",
    "réaliser",
    "réessayer",
    "résultatsaideconfidentialitéconditions",
    "saclayadresse",
    "san",
    "scholar",
    "scholarchargement",
    "school",
    "sciences",
    "scientifique",
    "scientist",
    "selected",
    "senior",
    "she",
    "sigmod",
    "silver",
    "site",
    "slides",
    "sont",
    "sophia",
    "sorbonne",
    "southern",
    "speaker",
    "springer",
    "stanford",
    "sud",
    "suivants",
    "suivies",
    "summer",
    "supervision",
    "supérieure",
    "supérieureadresse",
    "sur",
    "symposium",
    "système",
    "tard",
    "temps",
    "texas",
    "that",
    "the",
    "then",
    "theses",
    "titrecitée",
    "to",
    "transactions",
    "travaux",
    "télécom",
    "un",
    "under",
    "une",
    "univ",
    "university",
    "universityadresse",
    "université",
    "upmc",
    "usa",
    "using",
    "validée",
    "verimag",
    "verlag",
    "veuillez",
    "via",
    "vol",
    "was",
    "with",
    "won",
    "worked",
    "www",
    "year",
    "école",
    "être",
    "towards",
    "paradigm",
    "we",
    "this",
    "which",
    "our",
    "proposed",
    "their",
    "approach",
    "each",
    "such",
    "show",
    "what",
    "nous",
]

sw = stop_words + [str(i) for i in range(2100)]
