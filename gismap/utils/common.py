HIDDEN_KEYS = {"sources", "aliases", "abstract", "metadata"}


class LazyRepr:
    """
    MixIn that hides empty fields in dataclasses repr's.
    """

    def __repr__(self):
        kws = [
            f"{key}={value!r}"
            for key, value in self.__dict__.items()
            if value and key not in HIDDEN_KEYS and not key.startswith("_")
        ]
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


def get_classes(root, key="name"):
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

    >>> from gismap.sources.models import DB
    >>> subclasses = get_classes(DB, key='db_name')
    >>> dict(sorted(subclasses.items())) # doctest: +NORMALIZE_WHITESPACE
    {'dblp': <class 'gismap.sources.dblp.DBLP'>,
    'hal': <class 'gismap.sources.hal.HAL'>,
    'ldb': <class 'gismap.sources.ldb.LDB'>}
    """
    result = {
        getattr(c, key): c for c in root.__subclasses__() if getattr(c, key, None)
    }
    for c in root.__subclasses__():
        result.update(get_classes(c))
    return result


def list_of_objects(clss, dico, default=None):
    """
    Versatile way to enter a list of objects referenced by a dico.

    Parameters
    ----------
    clss: :class:`object`
        Object or reference to an object or list of objects / references to objects.
    dico: :class:`dict`
        Dictionary of references to objects.
    default: :class:`list`, optional
        Default list to return if `clss` is None.

    Returns
    -------
    :class:`list`
        Proper list of objects.

    Examples
    ________

    >>> from gismap.sources.models import DB
    >>> subclasses = get_classes(DB, key='db_name')
    >>> from gismap import HAL, DBLP
    >>> list_of_objects([HAL, 'dblp'], subclasses)
    [<class 'gismap.sources.hal.HAL'>, <class 'gismap.sources.dblp.DBLP'>]
    >>> list_of_objects(None, subclasses, [DBLP])
    [<class 'gismap.sources.dblp.DBLP'>]
    >>> list_of_objects(DBLP, subclasses)
    [<class 'gismap.sources.dblp.DBLP'>]
    >>> list_of_objects('hal', subclasses)
    [<class 'gismap.sources.hal.HAL'>]
    """
    if default is None:
        default = []
    if clss is None:
        return list_of_objects(clss=default, dico=dico)
    elif isinstance(clss, str):
        return [dico[clss]]
    elif isinstance(clss, list):
        return [cls for lcls in clss for cls in list_of_objects(lcls, dico, default)]
    else:
        return [clss]
