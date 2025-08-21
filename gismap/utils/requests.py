from time import sleep
import requests
from importlib.metadata import metadata
from gismap.utils.logger import logger


infos = metadata("gismap")
session = requests.Session()
session.headers.update(
    {
        "User-Agent": f"{infos['name']}/{infos['Version']} ({'; '.join(infos.get_all('Project-URL'))}; Contact, {infos['author-email']}"
    }
)


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
