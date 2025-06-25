from time import sleep

import requests


from gismap.utils.logger import logger


def autosession(s):
    """
    Parameters
    ----------
    s: :class:`~requests.Session`, optional
        A session (may be None).

    Returns
    -------
    :class:`~requests.Session`
        A session.
    """
    if s is None:
        s = requests.Session()
    return s


def auto_retry_get(s, url, params=None):
    """
    Parameters
    ----------
    s: :class:`~requests.Session`
        HTTP session.
    url: :class:`str`
        Entry point to fetch.
    params: :class:`dict`, optional
        Get arguments (appended to URL).

    Returns
    -------
    :class:`~requests.models.Response`
        Result.
    """
    while True:
        r = s.get(url, params=params)
        if r.status_code == 429:
            try:
                t = int(r.headers['Retry-After'])
            except KeyError:
                t = 60
            logger.warning(f'Too many requests. Auto-retry in {t} seconds.')
            sleep(t)
        else:
            return r
