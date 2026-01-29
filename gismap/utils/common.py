from dataclasses import dataclass

HIDDEN_KEYS = {"sources", "aliases", "abstract", "metadata"}


class LazyRepr:
    """
    MixIn that provides a clean repr for dataclasses.

    Hides empty fields and fields in HIDDEN_KEYS from the repr string.
    Private attributes (starting with '_') are also hidden.
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


def get_classes(root, key="name", recurse=False):
    """
    Parameters
    ----------
    root: :class:`class`
        Starting class (can be abstract).
    key: :class:`str`, default='name'
        Attribute to look-up
    recurse: bool, default=False
        Recursively traverse subclasses.

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
    if recurse:
        for c in root.__subclasses__():
            result.update(get_classes(c, key=key, recurse=True))
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
    >>> from gismap import HAL, DBLP, LDB
    >>> list_of_objects([HAL, 'ldb'], subclasses)
    [<class 'gismap.sources.hal.HAL'>, <class 'gismap.sources.ldb.LDB'>]
    >>> list_of_objects(None, subclasses, [DBLP])
    [<class 'gismap.sources.dblp.DBLP'>]
    >>> list_of_objects(LDB, subclasses)
    [<class 'gismap.sources.ldb.LDB'>]
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


@dataclass(repr=False)
class Data(LazyRepr):
    """
    Easy-going converter of dict to dataclass. Useful when you want to use attribute access
    and do not care about giving a full description.

    Examples
    --------

    >>> data = Data({
    ... 'name': 'Alice',
    ... 'age': 30,
    ... 'address': {'street': '123 Main', 'city': 'Paris'},
    ... 'hobbies': [{'name': 'jazz', 'level': 5}, {'name': 'code'}]})
    >>> data # doctest: +NORMALIZE_WHITESPACE
    Data(name='Alice', age=30, address=Data(street='123 Main', city='Paris'),
    hobbies=[Data(name='jazz', level=5), Data(name='code')])
    >>> data.hobbies[0].name
    'jazz'
    >>> data.todict()  # doctest: +NORMALIZE_WHITESPACE
    {'name': 'Alice', 'age': 30, 'address': {'street': '123 Main', 'city': 'Paris'},
    'hobbies': [{'name': 'jazz', 'level': 5}, {'name': 'code'}]}
    """

    def __init__(self, data):
        self._wrap(data)

    def _wrap(self, d):
        for key, value in d.items():
            wrapped = self._wrap_item(value)
            setattr(self, key, wrapped)

    def _wrap_item(self, item):
        if isinstance(item, dict):
            return Data(item)
        elif isinstance(item, list):
            return [self._wrap_item(subitem) for subitem in item]
        return item

    def todict(self):
        res = {}
        for key in self.__dict__:
            value = getattr(self, key)
            if hasattr(value, "todict"):
                res[key] = value.todict()
            elif isinstance(value, list):
                res[key] = [v.todict() if hasattr(v, "todict") else v for v in value]
            else:
                res[key] = value
        return res
