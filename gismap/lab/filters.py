import re

# editorials = re.compile(r"ditorial|foreword", re.IGNORECASE)
# charlatans = re.compile(r"Raoult|Kofman|Buob")

editorials = ["ditorial", "Foreword", "Brief Announcement", "Preface", "Préface"]
charlatans = ["Raoult", "Kofman", "Buob"]


def re_filter(words):
    """
    Parameters
    ----------
    words: :class:`list` or :class:`str`
        List of word(s) to filter.

    Returns
    -------
    callable
        Filter function.
    """
    if isinstance(words, str):
        taboo = re.compile(words)
    else:
        taboo = re.compile("|".join(words))
    return lambda txt: taboo.search(txt) is None


def publication_size_filter(n_max=9):
    """
    Parameters
    ----------
    n_max: int, default=9
        Maximum number of co-authors allowed.

    Returns
    -------
    callable
        Filter on number of co-authors.
    """
    return lambda p: len(p.authors) <= n_max


def publication_oneword_filter(n_min=2):
    """

    Parameters
    ----------
    n_min: int, default=2
        Minimum number of words required in the title.

    Returns
    -------
    callable
        Filter on number of words required in the title.
    """
    return lambda p: len(p.title.split()) >= n_min


def publication_taboo_filter(w=None):
    """
    Parameters
    ----------
    w: :class:`list`, optional
        List of words to filter.

    Returns
    -------
    Callable
        Filter function on publications.
    """
    if w is None:
        w = editorials
    regex = re_filter(w)
    return lambda p: regex(p.title)


def author_taboo_filter(w=None):
    """
    Parameters
    ----------
    w: :class:`list`, optional
        List of words to filter.

    Returns
    -------
    Callable
        Filter function on authors.
    """
    if w is None:
        w = charlatans
    regex = re_filter(w)
    return lambda p: regex(p.name)
