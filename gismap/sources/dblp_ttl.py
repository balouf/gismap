import re
import zlib
from contextlib import contextmanager
from pathlib import Path

from tqdm.auto import tqdm

from gismap.utils.requests import session
from gismap.sources.dblp import DBLP_TYPES

key_re = r'<https://dblp.org/rec/([^>]+)>'
title_re = r'.*?dblp:title\s+"([^"]+)"'
type_re = r'.*?dblp:bibtexType\s+bibtex:(\w+)'
authors_re = r'.*?dblp:hasSignature\s+(\[.*\])\s*;'
url_re = r'(?:.*?dblp:primaryDocumentPage <([^>]+)>)?'
stream_re = r'(?:.*?dblp:publishedInStream ([^;]+) ;)?'
pages_re = r'(?:.*?dblp:pagination "([^"]+)")?'
venue_re = r'(?:.*?dblp:publishedIn\s+"([^"]+?)")?'
year_re = r'.*?"(\d{4})"\^\^<http://www.w3.org/2001/XMLSchema#gYear>'

pub_re = re.compile("".join([key_re, title_re, type_re, authors_re,
                             url_re, stream_re, pages_re, venue_re, year_re]), flags=re.S)

streams_re = re.compile(r'<https://dblp.org/streams/((?:conf|journals)/[^>]+)>')

authid_re = re.compile(
    r'\[.*?signatureDblpName\s*?"([^"]+?)(?:\s+\d+)?".*?signatureCreator\s*<https://dblp.org/pid/([^>]+?)>.*?]',
    flags=re.S)


def parse_block(dblp_block):
    """
    Parameters
    ----------
    dblp_block: :class:`str`
        A DBLP publication, turtle format.

    Returns
    -------
    key: :class:`str`
        DBLP key.
    title: :class:`str`
        Publication title.
    type: :class:`str`
        Type of publication.
    authors: :class:`dict`
        Publication authors (key -> name)
    url: :class:`str` or :class:`NoneType`
        Publication URL.
    stream: :class:`list` or :class:`NoneType`
        Publication streams (normalized journal/conf).
    pages: :class:`str` or :class:`NoneType`
        Publication pages.
    venue: :class:`str` or :class:`NoneType`
        Publication venue (conf/journal).
    year: :class:`int`
        Year of publication.
    """
    items = pub_re.search(dblp_block)
    if items is None:
        return None
    key, title, typ, authors, url, stream, pages, venue, year = items.groups()
    typ = typ.lower()
    typ = DBLP_TYPES.get(typ, typ)
    if stream:
        stream = streams_re.findall(stream)
    authors = {i: n for n, i in authid_re.findall(authors)}
    if authors:
        return key, title, typ, authors, url, stream, pages, venue, int(year)
    return None


@contextmanager
def get_stream(source, chunk_size=1024 * 64):
    """
    Parameters
    ----------
    source: :class:`str` or :class:`~pathlib.Path`
        Where the content. Can be on a local file or on the Internet.
    chunk_size: :class:`int`, optional
        Desired chunk size. For streaming gz content, must be a multiple of 32kB.

    Yields
    -------
    iterable
        Chunk iterator that streams the content.
    :class:`int`
        Source size (used later to compute ETA).
    """
    if isinstance(source, str) and source.startswith("https://"):
        # URL HTTP
        with session.get(source, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0)) or None
            yield r.iter_content(chunk_size=chunk_size), total
    else:
        source = Path(source)
        if not source.exists():
            yield [], 0
            return None
        total = source.stat().st_size
        with source.open("rb") as file_handle:
            def read_chunks():
                while True:
                    chunk = file_handle.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            yield read_chunks(), total


def publis_streamer(source, chunk_size=1024 * 64, encoding="unicode_escape"):
    """
    Parameters
    ----------
    source: :class:`str` or :class:`~pathlib.Path`
        Where the DBLP turtle content is. Can be on a local file or on the Internet.
    chunk_size: :class:`int`, optional
        Desired chunk size. Must be a multiple of 32kB.
    encoding: :class:`str`, default=unicode_escape
        Encoding of stream.

    Yields
    -------
    key: :class:`str`
        DBLP key.
    title: :class:`str`
        Publication title.
    type: :class:`str`
        Type of publication.
    authors: :class:`dict`
        Publication authors (key -> name).
    venue: :class:`str`
        Publication venue (conf/journal).
    year: :class:`int`
        Year of publication.
    """
    with get_stream(source, chunk_size=chunk_size) as (stream, total):
        with tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc="Processing") as pbar:
            decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
            text_buffer = ""
            for chunk in stream:
                if not chunk:
                    continue

                pbar.update(len(chunk))
                data = decomp.decompress(chunk)
                if not data:
                    continue
                text_buffer += data.decode(encoding, errors="replace")

                blocks = text_buffer.split("\n\n")
                text_buffer = blocks[-1]
                for block in blocks[:-1]:
                    pub = parse_block(block)
                    if pub:
                        yield pub

        data = decomp.flush()
        if data:
            text_buffer += data.decode(encoding, errors="replace")

        if text_buffer:
            blocks = text_buffer.split("\n\n")
            for block in blocks:
                pub = parse_block(block)
                if pub:
                    yield pub
