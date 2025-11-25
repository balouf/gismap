# Generic Information Search: Mapping and Analysis of Publications


[![PyPI Status](https://img.shields.io/pypi/v/gismap.svg)](https://pypi.python.org/pypi/gismap)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/balouf/gismap/HEAD?urlpath=%2Fdoc%2Ftree%2Fbinder%2Finteractive.ipynb)
[![Build Status](https://github.com/balouf/gismap/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/balouf/gismap/actions?query=workflow%3Abuild)
[![Documentation Status](https://github.com/balouf/gismap/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/balouf/gismap/actions?query=workflow%3Adocs)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Coverage](https://codecov.io/gh/balouf/gismap/branch/main/graphs/badge.svg)](https://codecov.io/gh/balouf/gismap/tree/main)

GisMap leverages DBLP and HAL databases to provide cartography tools for you and your lab.

- Free software: MIT
- Documentation: <https://balouf.github.io/gismap/>.
- Github: <https://github.com/balouf/gismap>

## Features

- Can be used by all researchers in Computer Science (DBLP endpoint) or based in France (HAL endpoint).
- Aggregate publications from multiple databases, including multiple author keys inside the same database.
- Automatically keeps track of a Lab/Department members and publications.
- Builds interactive collaboration graphs.

## Test GisMap online!

Don't want to install GisMap on your computer (yet)? No worries, you can play with it using https://mybinder.org/.

For example:

- [A simple interface to display and save collaboration graphs](https://mybinder.org/v2/gh/balouf/gismap/HEAD?urlpath=%2Fdoc%2Ftree%2Fbinder%2Finteractive.ipynb)
- [Tutorial: Making LabMaps](https://mybinder.org/v2/gh/balouf/gismap/HEAD?urlpath=%2Fdoc%2Ftree%2Fdocs%2Ftutorials%2Flab_tutorial.ipynb)
- [Tutorial: Making EgoMaps](https://mybinder.org/v2/gh/balouf/gismap/HEAD?urlpath=%2Fdoc%2Ftree%2Fdocs%2Ftutorials%2Fegomap.ipynb)
- [Jupyter Lab instance with GisMap installed](https://mybinder.org/v2/gh/balouf/gismap/HEAD)


## Quickstart

Install GisMap:

```console
$ pip install gismap
```

Use GisMap to produce a collaboration graph (HTML):

```pycon
>>> from gismap.sources.hal import HAL
>>> from gismap.lab import ListLab
>>> lab = ListLab(["Fabien Mathieu", "François Baccelli", "Ludovic Noirie", "Céline Comte", "Sébastien Tixeuil"], dbs="hal")
>>> lab.update_authors()
>>> lab.update_publis()
>>> lab.show_html()
```

## Credits

This package was created with [Cookiecutter][CC] and the [Package Helper 3][PH3] project template.

[CC]: <https://github.com/audreyr/cookiecutter>
[PH3]: <https://balouf.github.io/package-helper-3/>
