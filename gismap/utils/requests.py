from time import sleep
import requests
from gismap.utils.logger import logger


session = requests.Session()


def get(url, params=None):
    """
    Parameters
    ----------
    url: :class:`str`
        Entry point to fetch.
    params: :class:`dict`, optional
        Get arguments (appended to URL).

    Returns
    -------
    :class:`str`
        Result.
    """
    while True:
        r = session.get(url, params=params)
        if r.status_code == 429:
            try:
                t = int(r.headers["Retry-After"])
            except KeyError:
                t = 60
            logger.warning(f"Too many requests. Auto-retry in {t} seconds.")
            sleep(t)
        else:
            return r.text
