# History

## Pipeline

- anHALyze: tools to spot HAL issues (bad author metadata, DBLP comparison, widget)
- EgoConf: find your conferences/journals
- Easier access to graph customization
- Additional graph option (e.g. time filtering and coloring, default group checks...)
- Custom CSS (e.g. transparent background)
- Gismo integration

## 0.5.3 (2026-04-XX)

### Bug fixes

- Fix comets (singletons) legend: checkbox visibility is now fully dynamic, appearing only when singletons exist for the current group selection
- Fix `HALAuthor.check_cv()`: adapt CV page detection to current HAL markup (`soup.main.section` instead of `soup.form`), and catch `AttributeError` in image extraction

### New features

- Add `select_publications()` method for querying publications by fuzzy title match, key, or callable filter
- Add `del_publication()` method for removing publications from a lab with optional confirmation

### Improvements

- Add `__str__` and `__repr__` to `LabMap`, `EgoMap`, `Author`, and `Publication` for human-readable display
- `EgoMap` automatically uses the star's name when no name is provided
- Fix `Publication.__str__` to avoid double period when title ends with "."
- Fix misleading tqdm progress in `expand()`: progress bar now reflects actual work (network calls) instead of completing instantly
- Add `format_authors()` utility with Oxford comma formatting (`sources/models.py`)
- Use `format_authors()` in publication overlays (`gisgraphs/graph.py`)
- `auto_sources` now completes missing DBs instead of being all-or-nothing: specifying a HAL key no longer prevents automatic LDB discovery
- Add `hal:fullname` shorthand to force HAL name-based search (useful when pid is too restrictive)
- Add `no_auto` flag in parentheses notation to disable automatic source completion

## 0.5.2 (2026-04-06)

### New features

- Add `add_publication()` method to manually add publications to a lab with fuzzy author matching
- New `Manual` database backend with `Outsider` and `Informal` classes (`sources/manual.py`)
- New `similarity_matrix()` utility for unified fuzzy matching (`utils/fuzzy.py`)

### Improvements

- Replace domonic with f-strings in `gisgraphs/`, removing domonic + 4 transitive dependencies
- Fix slow import (~4.1s → ~0.2s): lazy imports for `bof.fuzz`, `GismapWidget`, `LDB`, `gismo`
- Refactor expansion: `proper_prospects()` returns a simple list, `labify_publications` replaced by `regroup_authors`
- Add version compatibility warning when loading an LDB built for a different gismap version

### CI/CD

- Parallelize notebook execution in docs CI (matrix strategy, per-notebook cache, shared LDB cache)
- Add LDB cache to build CI (per Python version), simplify workflows (remove setup-python, enable uv cache)

### Tests

- Add parametrized tests for lab_examples `_author_iterator()` (6 labs)
- Improve test coverage (81% → 83% lines, 61% → 64% branches)
- Fix lazy import regression: `db_dict()` forces backend imports before discovery

### Documentation

- Document LDB management workflow in FAQ
- Simplify "Adding publications" tutorial with `add_publication()`

## 0.5.1 (2026-03-30)

- Fix publication deduplication: fingerprint now combines title and authors (normalized) instead of title only, preventing incorrect merges of different papers with similar titles
- Switch vis-network CDN from unpkg to jsDelivr (CORS fix for JupyterLab)
- Enable Light-themed full screen (previously, full screen was always dark)
- Slight adjustment in legend alignment
- IRIF added to the gallery
- Adapt Lamsade authors retrieval to new webpage format
- Add ruff linter configuration and pre-commit hooks
- Fix all existing ruff findings (import sorting, pyupgrade, line length)
- Consolidate coverage configuration into `pyproject.toml`
- Bump ipykernel minimum to 7.x
- Upgrade CI tooling: uv 0.11.0, Codecov v5, Pandoc 3.9
- Fix potential circular import in `lab_author.py` (lazy `db_dict` lookup)
- GH actions: cached gallery (tricky)

## 0.5.0 (2026-02-14)

- **BREAKING CHANGE** LDB now supports aliases (old assets not compatible)
- Algotel/Cores added to the gallery
- Add throttling to HAL requests, as they apparently started to limit the traffic

## 0.4.1 (2026-02-02): Python 3.14 support

- Add Python 3.14 compatibility (requires gismo>=0.5.4).
- Drop Python 3.10 support (now requires 3.11+).
- LDB search engine fine-tuned.
- Various typo fixes.

## 0.4.0 (2026-01-27): Local DB

New DB: LDB (Local DB). All the strengths of DBLP, None of its weaknesses.

- Convert the whole DBLP relational DB into a Gismap compatible local object.
- Introduces new compressed list format (Zlist) to keep the DB in memory.
- Use Bag-of-Factors to enable approximate search.
- You can build your own dataset or just rely on the one we provide and update.

Also, Lamsade added to the gallery.

## 0.3.1 (2025-11-27): Bug fixes

- Fix BS4 dependency issue.
- Errors in readme

## 0.3.0 (2025-11-25): Bigger, faster, prettier

- VisJS integration has been fully revamped to reduce JS errors and resource consumption.
- A gallery is now available in the documentation to showcase the possibilities:
  - Lip6 (Sorbonne university CS lab, single team / whole lab);
  - Laas (Toulouse university CS lab, single team / whole lab) + Solace (collab team);
  - Cédric (CNAM, whole CS Lab);
  - LINCS (legacy Paris-based collaboration project).
- Binder integration: you can now play with GisMap directly in your browser, no local Python required!
- A FAQ, because when the developer (me) starts to forget some how-tos, you know it’s time for a FAQ.
- GisGraphs can now have groups with automatic color selection and a selectable legend.
- Gradient-based coloring for inter-group edges (that one was no picnic).
- Lots of minor improvements here and there.

## 0.2.2 (2025-09-08): Various upgrades

- Breaking change: renaming some methods/attributes (e.g. *sun* is now *star* in EgoMap)
- Graphs now include unconnected non-empty nodes (their display will be an option in the next version)
- Typos here and there
- New Lab class: LINCS

## 0.2.1 (2025-09-01): Minor VisJS enhancements

- Better handling of dark/light mode (should be compatible with Pydata, Jupyter, and System).
- Responsive size

## 0.2.0 (2025-08-31): EgoMaps!

- New lab structure: EgoMap shows the people that revolve around you!
- New lab method: expansion, which adds *moons* (neighbor researchers).
- Add filters when building authors and publications.
- Physics engine changed for better visualization.
- Multi-source handling fine-tuned.
- Better display (size and theme).


## 0.1.0 (2025-07-24): First release

- First release on PyPI.
- Online DBLP and HAL DB implemented.
- Lab structures implemented.
- Early version of collaboration graph available.
