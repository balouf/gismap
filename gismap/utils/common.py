HIDDEN_KEYS = {'sources', 'aliases', 'abstract'}

class LazyRepr:
    """
    MixIn that hides empty fields in dataclasses repr's.
    """
    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.__dict__.items() if value and key not in HIDDEN_KEYS]
        return f"{type(self).__name__}({', '.join(kws)})"


def unlist(x):
    """
    Parameters
    ----------
    x: :class:`str` or :class:`list` or :class:`int`
        Something.

    Returns
    -------
    x: :class:`str` or :class:`int`
        If it's a list, make it flat.
    """
    return x[0] if (isinstance(x, list) and x) else x


def get_classes(root, key='name'):
    """
    Parameters
    ----------
    root: :class:`class`
        Starting class (can be abstract).
    key: :class:`str`, default='name'
        Attribute to look-up

    Returns
    -------
    :class:`dict`
        Dictionaries of all subclasses that have a key attribute (as in class attribute `key`).

    Examples
    --------

    >>> from gismap.database.blueprint import DBAuthor
    >>> subclasses = get_classes(DBAuthor, key='db_name')
    >>> dict(sorted(subclasses.items())) # doctest: +NORMALIZE_WHITESPACE
    {'dblp': <class 'gismap.database.dblp.DBLPAuthor'>,
    'hal': <class 'gismap.database.hal.HALAuthor'>}
    """
    result = {getattr(c, key): c for c in root.__subclasses__() if getattr(c, key)}
    for c in root.__subclasses__():
        result.update(get_classes(c))
    return result
