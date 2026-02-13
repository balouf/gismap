from dataclasses import dataclass, field
from functools import lru_cache
from importlib.metadata import version as pkg_version
from typing import ClassVar
from platformdirs import user_data_dir
from pathlib import Path
from datetime import datetime, timezone
import errno
import json
import os

import zstandard as zstd
import dill as pickle
import numpy as np
import numba as nb
from bof.fuzz import Process
from gismo.common import safe_write
from tqdm.auto import tqdm
import requests

from gismap.sources.dblp_ttl import publis_streamer
from gismap.sources.models import DB, Author, Publication
from gismap.utils.common import Data
from gismap.utils.logger import logger
from gismap.utils.text import normalized_name
from gismap.utils.zlist import ZList


DATA_DIR = Path(
    user_data_dir(
        appname="gismap",
        appauthor=False,
    )
)
LDB_STEM = "ldb"
GITHUB_REPO = "balouf/gismap"

LDB_PARAMETERS = Data(
    {
        "search": {"limit": 3, "cutoff": 87.0, "slack": 1.0},
        "bof": {"n_range": 2, "length_impact": 0.1},
        "frame_size": {"authors": 512, "publis": 256},
        "io": {
            "source": "https://dblp.org/rdf/dblp.ttl.gz",
            "destination": DATA_DIR / f"{LDB_STEM}.pkl.zst",
            "metadata": DATA_DIR / f"{LDB_STEM}.json",
            "gh_api": f"https://api.github.com/repos/{GITHUB_REPO}/releases",
        },
    }
)
"""
Global configuration parameters for the Local DBLP (LDB) pipeline.

Structure:
- search:
    - limit: maximum number of candidates retrieved per query.
    - cutoff: minimal similarity score required to keep a candidate.
    - slack: tolerance around the cutoff for borderline matches.
- bof (Bag-of-Factors):
    - n_range: max factor size (higher is better but more expensive).
    - length_impact: how to compare two inputs of different size.
- frame_size:
    - authors: maximum number of authors kept in a single frame/batch.
    - publis: maximum number of publications kept in a single frame/batch.
- io:
    - source: URL/file location of the DBLP RDF dump used as raw input.
    - destination: local path where the compressed preprocessed dataset is / will be stored.
    - gh_api: GitHub API endpoint used to fetch release information for the project.

LDB_PARAMETERS is a Data (RecursiveDict) instance, so nested fields can be
accessed with attribute notation, e.g.:
    LDB_PARAMETERS.search.limit
    LDB_PARAMETERS.io.destination
"""


def _compatible_tag(tag: str) -> bool:
    """Check that release tag is compatible with the installed package (same major.minor)."""
    v = pkg_version("gismap")
    pkg_minor = ".".join(v.split(".")[:2])
    tag_clean = tag.lstrip("v")
    tag_minor = ".".join(tag_clean.split(".")[:2])
    return pkg_minor == tag_minor


@dataclass(repr=False)
class LDB(DB):
    """
    Browse DBLP from a local copy of the database.

    LDB is a class-only database - it should not be instantiated.
    All methods are classmethods and state is stored in class variables.

    Examples
    --------

    Public DB methods ensure that the DB is loaded but if you need to use a specific LDB method, prepare the DB first.

    >>> LDB._ensure_loaded()
    >>> LDB.author_by_key("66/2077")
    LDBAuthor(name='Fabien Mathieu', key='66/2077')
    >>> pubs = sorted(LDB.author_publications('66/2077'), key = lambda p: p.year)
    >>> pub = pubs[0]
    >>> pub.metadata
    {'url': 'http://www2003.org/cdrom/papers/poster/p102/p102-mathieu.htm', 'streams': ['conf/www']}
    >>> christelle = LDB.search_author("Christelle Caillouet")
    >>> christelle
    [LDBAuthor(name='Christelle Caillouet', key='10/8725')]
    >>> christelle[0].aliases
    ['Christelle Molle']
    >>> LDB.db_info()  # doctest: +SKIP
    {'tag': 'v0...', 'downloaded_at': '...', 'size': ..., 'path': ...}
    >>> LDB.check_update()
    >>> ldb = LDB()
    Traceback (most recent call last):
    ...
    TypeError: LDB should not be instantiated. Use class methods directly, e.g., LDB.search_author(name)
    """

    db_name: ClassVar[str] = LDB_STEM
    parameters: ClassVar[Data] = LDB_PARAMETERS

    # Class-level state (replaces instance attributes)
    authors: ClassVar[ZList | None] = None
    publis: ClassVar[ZList | None] = None
    keys: ClassVar[dict | None] = None
    search_engine: ClassVar[Process | None] = None
    _initialized: ClassVar[bool] = False

    __hash__ = object.__hash__

    def __init__(self):
        raise TypeError(
            "LDB should not be instantiated. Use class methods directly, e.g., LDB.search_author(name)"
        )

    @classmethod
    def _ensure_loaded(cls):
        """Lazy-load the database if not already loaded."""
        if cls._initialized:
            return
        if not cls.parameters.io.destination.exists():
            logger.info("LDB not found locally. Attempting to retrieve from GitHub...")
            try:
                cls.retrieve()
            except RuntimeError as e:
                logger.warning(f"Could not auto-retrieve LDB: {e}")
        cls.load_db()

    @classmethod
    def build_db(cls, limit=None):
        """
        Build the LDB database from a DBLP TTL dump.

        Parses the DBLP RDF/TTL file to extract publications and authors,
        stores them in compressed ZList structures, and builds a fuzzy
        search engine for author name lookups.

        Parameters
        ----------
        limit: :class:`int`, optional
            Maximum number of publications to process. If None, processes
            the entire database. Useful for testing with a subset.

        Notes
        -----
        This method populates the class-level attributes:

        - ``authors``: ZList of (key, name, publication_indices) tuples
        - ``publis``: ZList of publication records
        - ``keys``: dict mapping author keys to indices
        - ``search_engine``: fuzzy search Process for author lookups

        After building, call :meth:`dump_db` to persist the database.

        Examples
        --------
        Build from the default DBLP source:

        >>> LDB.build_db()  # doctest: +SKIP
        >>> LDB.dump_db()   # doctest: +SKIP

        Build a small test database:

        >>> LDB.build_db(limit=1000)
        >>> LDB.authors[0]
        ('78/459-1', ['Manish Singh'], [0])

        Save your build in a non-default file:

        >>> from tempfile import TemporaryDirectory
        >>> from pathlib import Path
        >>> with TemporaryDirectory() as tmpdirname:
        ...     LDB.dump(filename="test.zst", path=tmpdirname)
        ...     [file.name for file in Path(tmpdirname).glob("*")]
        ['test.zst']

        In case you don't like your build and want to reload your local database from disk:

        >>> LDB.load_db()
        """
        source = cls.parameters.io.source
        authors_dict = dict()
        logger.info("Retrieve publications")
        with ZList(frame_size=cls.parameters.frame_size.publis) as publis:
            for i, (
                key,
                title,
                typ,
                authors,
                url,
                streams,
                pages,
                venue,
                year,
            ) in enumerate(publis_streamer(source)):
                auth_indices = []
                for auth_key, auth_name in authors.items():
                    if auth_key not in authors_dict:
                        authors_dict[auth_key] = (len(authors_dict), {auth_name}, [i])
                    else:
                        authors_dict[auth_key][1].add(auth_name)
                        authors_dict[auth_key][2].append(i)
                    auth_indices.append(authors_dict[auth_key][0])
                publis.append(
                    (key, title, typ, auth_indices, url, streams, pages, venue, year)
                )
                if i == limit:
                    break
        cls.publis = publis
        logger.info(f"{len(publis)} publications retrieved.")
        logger.info("Compact authors")
        with ZList(frame_size=cls.parameters.frame_size.authors) as authors:
            for key, (_, names, pubs) in tqdm(authors_dict.items()):
                authors.append((key, list(names), pubs))
        cls.authors = authors
        cls.keys = {k: v[0] for k, v in authors_dict.items()}
        del authors_dict
        cls._build_search_engine()
        cls._invalidate_cache()
        cls._initialized = True

    @classmethod
    def _build_search_engine(cls):
        cls.search_engine = Process(
            n_range=cls.parameters.bof.n_range,
            length_impact=cls.parameters.bof.length_impact,
        )
        main_names = []
        aliases = []
        aliases_indices = []
        for i, a in enumerate(cls.authors):
            main_names.append(normalized_name(a[1][0]))
            for alias in a[1][1:]:
                aliases_indices.append(i)
                aliases.append(normalized_name(alias))
        cls.search_engine.fit(main_names+aliases)
        aliases_indices = np.array(aliases_indices)
        cls.search_engine.choices = np.concatenate((np.arange(len(cls.authors)), aliases_indices))
        # cls.search_engine.fit([normalized_name(a[1]) for a in cls.authors])
        # cls.search_engine.choices = np.arange(len(cls.authors))
        cls.search_engine.vectorizer.features_ = cls.numbify_dict(
            cls.search_engine.vectorizer.features_
        )
        logger.info(f"{len(cls.authors)} authors indexed.")

    @classmethod
    @lru_cache(maxsize=50000)
    def author_by_index(cls, i):
        key, names, _ = cls.authors[i]
        names = sorted(names)
        return LDBAuthor(key=key, name=names[0], aliases=names[1:])

    @classmethod
    def author_by_key(cls, key):
        return cls.author_by_index(cls.keys[key])

    @classmethod
    @lru_cache(maxsize=50000)
    def publication_by_index(cls, i):
        key, title, typ, authors, url, streams, pages, venue, year = cls.publis[i]
        if venue is None:
            venue = "unpublished"
        return {
            "key": key,
            "title": title,
            "type": typ,
            "authors": authors,
            "url": url,
            "streams": streams,
            "pages": pages,
            "venue": venue,
            "year": year,
        }

    @classmethod
    def author_publications(cls, key):
        cls._ensure_loaded()
        _, name, pubs = cls.authors[cls.keys[key]]
        pubs = [cls.publication_by_index(k).copy() for k in pubs]
        auth_ids = sorted({k for p in pubs for k in p["authors"]})
        auths = {k: cls.author_by_index(k) for k in auth_ids}
        for pub in pubs:
            pub["authors"] = [auths[k] for k in pub["authors"]]
            metadata = dict()
            for k in ["url", "streams", "pages"]:
                v = pub.pop(k)
                if v is not None:
                    metadata[k] = v
            pub["metadata"] = metadata
        return [LDBPublication(**pub) for pub in pubs]

    @classmethod
    @lru_cache(maxsize=1000)
    def search_author(cls, name):
        cls._ensure_loaded()
        res = cls.search_engine.extract(
            normalized_name(name),
            limit=cls.parameters.search.limit,
        )
        if not res:
            return []
        target = max(cls.parameters.search.cutoff, res[0][1] - cls.parameters.search.slack)
        res = [r[0] for r in res if r[1] > target]
        sorted_ids = {i: cls.author_by_index(i) for i in sorted(res)}
        return [sorted_ids[i] for i in res]

    @classmethod
    def _invalidate_cache(cls):
        cls.search_author.cache_clear()
        cls.publication_by_index.cache_clear()
        cls.author_by_index.cache_clear()

    @classmethod
    def from_author(cls, a):
        return cls.author_publications(a.key)

    @classmethod
    def _get_release_info(cls, tag: str | None = None) -> dict:
        """
        Fetch release metadata from GitHub API.

        Parameters
        ----------
        tag: :class:`str`, optional
            Specific release tag (e.g., "v0.4.0"). If None, fetches latest.

        Returns
        -------
        :class:`dict`
            Release metadata including tag_name and assets.

        Raises
        ------
        :class:`RuntimeError`
            If release not found or API request fails.
        """
        api_url = cls.parameters.io.gh_api
        if tag is None:
            url = f"{api_url}/latest"
        else:
            url = f"{api_url}/tags/{tag}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise RuntimeError(f"Release not found: {tag or 'latest'}") from e
            raise RuntimeError(f"GitHub API error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error fetching release info: {e}") from e

    @classmethod
    def _download_file(cls, url: str, dest: Path, desc: str = "Downloading"):
        """
        Download file with progress bar.

        Parameters
        ----------
        url : str
            URL to download from.
        dest : Path
            Destination file path.
        desc : str
            Description for progress bar.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))

        with (
            open(dest, "wb") as f,
            tqdm(
                desc=desc,
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar,
        ):
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

    @classmethod
    def _save_meta(cls, tag: str, url: str, size: int):
        """Save version metadata to JSON file."""
        meta = {
            "tag": tag,
            "url": url,
            "size": size,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path = cls.parameters.io.metadata
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    @classmethod
    def _load_meta(cls) -> dict | None:
        """Load version metadata from JSON file."""
        meta_path = cls.parameters.io.metadata
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    @classmethod
    def retrieve(cls, version: str | None = None, force: bool = False):
        """
        Download LDB database from GitHub releases.

        Parameters
        ----------
        version: :class:`str`, optional
            Specific release version (e.g., "v0.4.0" or "0.4.0").
            If None, downloads from latest release.
        force: :class:`bool`, default=False
            Download even if same version is installed.

        Examples
        --------

        The following will get you a LDB if you do not have one.

        >>> LDB.retrieve()           # Latest compatible release  # doctest: +SKIP
        >>> LDB.retrieve("v0.5.0")   # Specific version  # doctest: +SKIP
        >>> LDB.retrieve("0.5.0")    # Also works without 'v' prefix  # doctest: +SKIP

        Of course, the tag/version must be LDB-ready.

        >>> LDB.retrieve("v0.3.0")   # Too old for LDB
        Traceback (most recent call last):
        ...
        RuntimeError: Asset 'ldb.pkl.zst' not found in release v0.3.0. Available assets: []

        Raises
        ------
        RuntimeError
            If release or asset not found, download fails, or version is incompatible.
        """
        # Normalize version string (add "v" prefix if missing)
        tag = None
        if version is not None:
            tag = version if version.startswith("v") else f"v{version}"

        # Fetch release info
        logger.info(f"Fetching release info for: {tag or 'latest'}")
        release_info = cls._get_release_info(tag)
        release_tag = release_info["tag_name"]

        # Check version compatibility (only when no explicit version requested)
        if tag is None and not _compatible_tag(release_tag):
            raise RuntimeError(
                f"Latest release {release_tag} is not compatible with installed gismap {pkg_version('gismap')}. "
                f"Use retrieve(version='v...') to force a specific version."
            )

        destination = cls.parameters.io.destination

        # Check if already installed (unless force=True)
        if not force:
            meta = cls._load_meta()
            if meta and meta.get("tag") == release_tag and destination.exists():
                logger.info(
                    f"LDB version {release_tag} already installed. Use force=True to re-download."
                )
                return

        # Find ldb.pkl.zst asset in release
        assets = release_info.get("assets", [])
        ldb_asset = None
        for asset in assets:
            if asset["name"] == destination.name:
                ldb_asset = asset
                break

        if ldb_asset is None:
            raise RuntimeError(
                f"Asset '{destination.name}' not found in release {release_tag}. "
                f"Available assets: {[a['name'] for a in assets[:3]]}"
            )

        download_url = ldb_asset["browser_download_url"]
        asset_size = ldb_asset["size"]

        logger.info(
            f"Downloading LDB from release {release_tag} ({asset_size / 1e9:.2f} GB)"
        )

        # Download with progress bar
        cls._download_file(download_url, destination, desc=f"LDB {release_tag}")

        # Save version metadata
        cls._save_meta(release_tag, download_url, asset_size)

        # Load database and rebuild search engine locally
        cls.load_db(restore_search=True)

        logger.info(f"LDB {release_tag} successfully installed to {destination}")

    @classmethod
    def db_info(cls) -> dict | None:
        """
        Return installed version info.

        Returns
        -------
        :class:`dict` or :class:`None`
            Dictionary with tag, date, size, path; or None if not installed.
        """
        meta = cls._load_meta()
        destination = cls.parameters.io.destination
        if meta is None or not destination.exists():
            return None

        return {
            "tag": meta.get("tag"),
            "downloaded_at": meta.get("downloaded_at"),
            "size": meta.get("size"),
            "path": str(destination),
        }

    @classmethod
    def check_update(cls) -> dict | None:
        """
        Check if a newer version is available on GitHub.

        Returns
        -------
        :class:`dict` or None
            Dictionary with update info if available, None if up to date.
        """
        try:
            release_info = cls._get_release_info()
            latest_tag = release_info["tag_name"]

            if not _compatible_tag(latest_tag):
                logger.info(f"Latest release {latest_tag} is not compatible with gismap {pkg_version('gismap')}.")
                return None

            meta = cls._load_meta()
            current_tag = meta.get("tag") if meta else None

            if current_tag == latest_tag:
                logger.info(f"LDB is up to date: {current_tag}")
                return None

            return {
                "current": current_tag,
                "latest": latest_tag,
                "message": f"Update available: {current_tag or 'not installed'} -> {latest_tag}",
            }
        except RuntimeError as e:
            logger.warning(f"Could not check for updates: {e}")
            return None

    @classmethod
    def dump(cls, filename: str, path=".", overwrite=False, include_search=True):
        """Save class state to file."""
        # Convert numba dict to regular dict for pickling
        nb_dict = None
        if include_search and cls.search_engine is not None:
            nb_dict = cls.search_engine.vectorizer.features_
            cls.search_engine.vectorizer.features_ = dict(nb_dict)

        state = {
            "authors": cls.authors,
            "publis": cls.publis,
            "keys": cls.keys,
            "search_engine": cls.search_engine if include_search else None,
        }

        # Use safe_write pattern from gismo.common
        destination = Path(path) / filename
        if destination.exists() and not overwrite:
            print(
                f"File {destination} already exists! Use overwrite option to overwrite."
            )
        else:
            with safe_write(destination) as f:
                cctx = zstd.ZstdCompressor(level=3)
                with cctx.stream_writer(f) as z:
                    pickle.dump(state, z, protocol=5)

        # Restore numba dict
        if include_search and cls.search_engine is not None:
            cls.search_engine.vectorizer.features_ = nb_dict

    @classmethod
    def load(cls, filename: str, path=".", restore_search=False):
        """Load class state from file."""
        dest = Path(path) / filename
        if not dest.exists():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), dest)

        dctx = zstd.ZstdDecompressor()
        with open(dest, "rb") as f, dctx.stream_reader(f) as z:
            state = pickle.load(z)

        cls.authors = state["authors"]
        cls.publis = state["publis"]
        cls.keys = state["keys"]
        cls.search_engine = state["search_engine"]

        if restore_search:
            cls._build_search_engine()
            cls.dump(filename=filename, path=path, overwrite=True, include_search=True)
        elif cls.search_engine is not None:
            cls.search_engine.vectorizer.features_ = cls.numbify_dict(
                cls.search_engine.vectorizer.features_
            )

        cls._invalidate_cache()
        cls._initialized = True

    @classmethod
    def dump_db(cls, include_search=True):
        destination = cls.parameters.io.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        cls.dump(
            destination.name,
            path=destination.parent,
            overwrite=True,
            include_search=include_search,
        )

    @classmethod
    def load_db(cls, restore_search=False):
        destination = cls.parameters.io.destination
        try:
            cls.load(
                destination.name, path=destination.parent, restore_search=restore_search
            )
        except FileNotFoundError:
            logger.warning("No LDB found. Building from source...")
            cls.build_db()
            cls.dump_db()
        except TypeError as e:
            if "code expected at most" in str(e):
                logger.warning(
                    "LDB file incompatible with this Python version. Rebuilding from source..."
                )
                cls.build_db()
                cls.dump_db()
            else:
                raise

    @classmethod
    def delete_db(cls):
        destination = cls.parameters.io.destination
        if destination.exists():
            destination.unlink()

    @staticmethod
    def numbify_dict(input_dict):
        nb_dict = nb.typed.Dict.empty(
            key_type=nb.types.unicode_type, value_type=nb.types.int64
        )
        for k, v in input_dict.items():
            nb_dict[k] = v
        return nb_dict


@dataclass(repr=False)
class LDBAuthor(Author, LDB):
    """
    Author from the LDB (Local DBLP) database.

    LDB provides local access to DBLP data without rate limiting.

    Parameters
    ----------
    name: :class:`str`
        The author's name.
    key: :class:`str`
        DBLP person identifier (pid).
    aliases: :class:`list`
        Alternative names for the author.
    """

    key: str
    aliases: list = field(default_factory=list)

    @property
    def url(self):
        return f"https://dblp.org/pid/{self.key}.html"

    def get_publications(self):
        return LDB.from_author(self)


@dataclass(repr=False)
class LDBPublication(Publication, LDB):
    """
    Publication from the LDB (Local DBLP) database.

    Parameters
    ----------
    title: :class:`str`
        Publication title.
    authors: :class:`list`
        List of :class:`LDBAuthor` objects.
    venue: :class:`str`
        Publication venue.
    type: :class:`str`
        Publication type.
    year: :class:`int`
        Publication year.
    key: :class:`str`
        DBLP record key.
    metadata: :class:`dict`
        Additional metadata (URL, streams, pages).
    """

    key: str
    metadata: dict = field(default_factory=dict)

    @property
    def url(self):
        return self.metadata.get("url", f"https://dblp.org/rec/{self.key}.html")

    @property
    def stream(self):
        if "streams" in self.metadata:
            return f"https://dblp.org/streams/{self.metadata['streams'][0]}"
        return None
