from bof.fuzz import Process
import unicodedata


class Corrector:
    """
    A simple word corrector base on input vocabulary. Short words are discarded.

    Parameters
    ----------
    voc: :class:`list`
        Words (each entry may contain multiple words).
    score_cutoff: :class:`int`, default=20
        Threshold for correction.
    min_length: :class:`int`, default=3
        Minimal number of caracters for correction to kick in.

    Examples
    --------

    >>> vocabulary = ['My Taylor Swift is Rich']
    >>> phrase = "How riche ise Tailor Swyft"
    >>> cor = Corrector(vocabulary, min_length=4)
    >>> cor(phrase)
    'How rich ise taylor swift'
    >>> cor = Corrector(vocabulary, min_length=2)
    >>> cor(phrase)
    'How rich is taylor swift'
    """

    def __init__(self, voc, score_cutoff=20, min_length=3):
        self.voc = {k.lower() for w in voc for k in w.split() if len(k) >= min_length}
        self.cutoff = score_cutoff
        self.min_length = min_length
        self.p = Process()
        self.p.fit(list(self.voc))

    def correct_word(self, w):
        if len(w) < self.min_length or w.lower() in self.voc:
            return w
        ww = self.p.extractOne(w, score_cutoff=self.cutoff)
        return ww[0] if ww is not None else w

    def __call__(self, text):
        return " ".join(self.correct_word(w) for w in text.split())


def reduce_keywords(kws):
    """
    Remove redundant subparts.

    Parameters
    ----------
    kws: :class:`list`
        List of words / co-locations.

    Returns
    -------
    :class:`list`
        Reduced list

    Examples
    --------

    >>> reduce_keywords(['P2P', 'Millimeter Waves', 'Networks', 'P2P Networks', 'Waves'])
    ['Millimeter Waves', 'P2P Networks']
    """
    indices = []
    for i, kw1 in enumerate(kws):
        accept = True
        for j, kw2 in enumerate(kws):
            if j != i and kw1 in kw2:
                accept = False
                break
        if accept:
            indices.append(i)
    return [kws[i] for i in indices]


def clean_aliases(name, alias_list):
    """
    Parameters
    ----------
    name: :class:`str`
        Main name.
    alias_list: :class:`list` or :class:`set`
        Aliases.

    Returns
    -------
    :class:`list`
        Aliases deduped, sorted, and with main name removed.
    """
    return sorted(set(n for nn in alias_list for n in [nn, asciify(nn)] if n != name))


def asciify(text):
    """
    Parameters
    ----------
    text::class:`str`
        Some text (typically names) with annoying accents.

    Returns
    -------
    :class:`str`
        Same text simplified into ascii.

    Examples
    --------
    >>> asciify('Ana Bušić')
    'Ana Busic'
    >>> asciify("Thomas Deiß")
    'Thomas Deiss'
    """
    text = text.replace("ß", "ss")
    decomposed = unicodedata.normalize("NFD", text)
    no_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    ascii_text = no_accents.encode("ascii", "ignore").decode()
    return ascii_text


def normalized_name(txt):
    """
    Try to normalize names for facilitating comparisons. Name is lowered, split, asciified, sorted, and filtered.

    Parameters
    ----------
    txt: :class:`str`

    Returns
    -------
    :class:`str`

    Examples
    --------

    >>> normalized_name("Thomas Deiß")
    'deiss thomas'
    >>> normalized_name("Dario Rossi 001")
    'dario rossi'
    >>> normalized_name("James W. Roberts")
    'james roberts'
    """
    return " ".join(
        sorted(
            asciify(a)
            for a in txt.lower().replace("-", " ").split()
            if not (a.isdigit() or (len(a) < 3 and "." in a))
        )
    )


def auto_int(txt):
    try:
        return int(txt)
    except ValueError:
        return txt
