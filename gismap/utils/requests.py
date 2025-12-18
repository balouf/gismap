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


def get(url, params=None, n_trials=10, verify=True):
    """
    Parameters
    ----------
    url: :class:`str`
        Entry point to fetch.
    params: :class:`dict`, optional
        Get arguments (appended to URL).
    n_trials: :class:`int`, default=10
        Number of attempts to fetch URL.
    verify: :class:`bool`, default=True
        Verify certificates.

    Returns
    -------
    :class:`str`
        Result.
    """
    for attempt in range(n_trials):
        try:
            r = session.get(url, params=params, verify=verify)
            if r.status_code == 429:
                try:
                    t = int(r.headers["Retry-After"])
                except KeyError:
                    t = 60
                logger.warning(f"Too many requests. Auto-retry in {t} seconds.")
                sleep(t)
            else:
                return r.text
        except requests.exceptions.ConnectionError:
            t = 6
            logger.warning(f"Connection error. Auto-retry in {t} seconds.")
            sleep(t)
    raise requests.exceptions.ConnectionError(f"Unable to retrieve {url}")
