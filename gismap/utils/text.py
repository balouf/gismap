from bof.fuzz import Process


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
    >>> cor = Corrector(vocabulary)
    >>> cor('May Tailor Swyft ise Riche')
    'May taylor swift ise rich'
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
    return sorted(set(n for n in alias_list if n != name))

