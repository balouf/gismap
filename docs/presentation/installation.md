# Installation

## Stable release

To install GisMap, run this command in your terminal:

```console
$ pip install gismap
```

This is the preferred method to install GisMap, as it will always install the most recent stable release.

If you don't have [pip] installed, this [Python installation guide] can guide
you through the process.

````{note}
If you want to use GisMap as a dependency in a UV-managed project, add it with
```console
$ uv add gismap
```
````

## From sources

The sources for GisMap can be downloaded from the [Github repo].

You can either clone the public repository:

```console
$ git clone git://github.com/balouf/gismap
```

Or download the [tarball]:

```console
$ curl -OJL https://github.com/balouf/gismap/tarball/main
```

Once you have a copy of the source, you can install it from the package directory with:

```console
$ pip install .
```

## LDB (Local DBLP) setup

GisMap includes LDB, a local mirror of the DBLP database that provides fast, accurate access
to Computer Science publications. LDB is automatically downloaded on first use (~1 GB compressed).

```{important}
After upgrading gismap to a new version, you may need to update your local LDB:

    from gismap.sources import LDB
    LDB.retrieve()

See the [FAQ](../faq) for more details on LDB management.
```

[github repo]: https://github.com/balouf/gismap
[pip]: https://pip.pypa.io
[python installation guide]: http://docs.python-guide.org/en/latest/starting/installation/
[tarball]: https://github.com/balouf/gismap/tarball/main
