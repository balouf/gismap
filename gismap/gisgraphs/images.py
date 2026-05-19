import base64
from concurrent.futures import ThreadPoolExecutor

import requests

from gismap.gisgraphs.graph import initials
from gismap.utils.logger import logger
from gismap.utils.requests import session


def fetch_data_uri(url, *, max_bytes, timeout):
    """
    Fetch an image and return its ``data:`` URI, or ``None`` on failure.

    Streams the response and aborts as soon as ``max_bytes`` is exceeded, so
    a 30 MB LDAP portrait never lands in memory.

    Parameters
    ----------
    url : :class:`str`
        Image URL.
    max_bytes : :class:`int`
        Hard cap on the downloaded payload. URLs exceeding this are skipped.
    timeout : :class:`float`
        Per-request timeout (connect + read), seconds.

    Returns
    -------
    :class:`str` or None
        ``data:<mime>;base64,...`` on success, ``None`` if the image is
        unreachable, too large, or returns a non-2xx status.
    """
    try:
        with session.get(url, stream=True, timeout=timeout) as r:
            if r.status_code != 200:
                return None
            content_length = r.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                return None
            mime = (r.headers.get("Content-Type") or "image/jpeg").split(";", 1)[0].strip()
            buf = bytearray()
            for chunk in r.iter_content(chunk_size=8192):
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    return None
    except (requests.RequestException, ValueError):
        return None
    return f"data:{mime};base64,{base64.b64encode(bytes(buf)).decode('ascii')}"


def inline_node_images(nodes, *, max_bytes=200_000, timeout=5, max_workers=8):
    """
    Replace each node's ``image`` URL with an inlined ``data:`` URI, demoting
    failures to the initials fallback.

    Mutates ``nodes`` in place. Post-condition: no node carries an ``image``
    that is still a URL — every remaining ``image`` is a ``data:`` URI, which
    guarantees the canvas is exportable to PNG. Nodes whose image could not
    be inlined (network error, non-200, or above ``max_bytes``) lose their
    ``image``/``shape`` keys and fall back to a two-letter initials label,
    matching the default rendering when ``metadata.img`` was unset.

    Parameters
    ----------
    nodes : :class:`list` of :class:`dict`
        Node payloads as produced by :func:`~gismap.gisgraphs.graph.lab_to_graph`.
    max_bytes : :class:`int`, default=200_000
        Skip inlining if the image is larger than this. Large source images
        (e.g. uncropped LDAP portraits) are demoted to initials.
    timeout : :class:`float`, default=5
        Per-image fetch timeout.
    max_workers : :class:`int`, default=8
        Parallel download workers.

    Returns
    -------
    None
    """
    urls = list(
        {
            n["image"]
            for n in nodes
            if isinstance(n.get("image"), str) and n["image"].startswith(("http://", "https://"))
        }
    )
    if urls:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            cache = dict(zip(urls, ex.map(lambda u: fetch_data_uri(u, max_bytes=max_bytes, timeout=timeout), urls)))
    else:
        cache = {}
    n_inlined = 0
    n_demoted = 0
    for n in nodes:
        img = n.get("image")
        if not isinstance(img, str) or img.startswith("data:"):
            continue
        uri = cache.get(img)
        if uri:
            n["image"] = uri
            n_inlined += 1
        else:
            del n["image"]
            if n.get("shape") == "circularImage":
                del n["shape"]
            name = n.get("name")
            if name:
                n["label"] = initials(name)
            n_demoted += 1
    if n_demoted:
        logger.info(f"inline_node_images: {n_inlined} inlined, {n_demoted} demoted to initials")
