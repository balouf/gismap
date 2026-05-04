# History

## Pipeline

- anHALyze: tools to spot HAL issues (bad author metadata, DBLP comparison, widget)
- EgoConf: find your conferences/journals
- Easier access to graph customization
- Additional graph option (e.g. time filtering and coloring, default group checks...)
- Custom CSS (e.g. transparent background)
- Gismo integration

## 0.5.4 (2026-05-04): Some user requests

### Highlights

- BibTeX export everywhere: per-publication `[.bib]` toggle in the modal, per-author / per-pair "Download .bib" buttons, and a whole-lab download via the new menu (or programmatically via `LabMap.to_bib()`).
- Reorganized graph controls: a hamburger menu (top-left) groups Redraw, Full Screen, Show/Hide Legend, PNG export, and the lab-level `.bib` export. Full Screen becomes a YouTube-style icon at the bottom-right.
- Modal overlay is finally legible in Jupyter dark mode.
- HTML produced by `lab.html()` / `save_html()` is ~4× smaller for typical labs.
- New programmatic exports: `LabMap.to_bib()`, `LabMap.to_json()`, `LabMap.to_csv()`.
- New tutorial [HALTools](docs/tutorials/haltools.ipynb): walk-through of `diff_sources()` and `find_duplicates()` on four real-world researcher profiles, with an explicit "what to act on, what to ignore" wrap-up. Replaces and expands the former *Analyzing sources* section of the EgoMap tutorial.

### Visualization

- New hamburger menu (top-left) replacing the standalone Redraw button. Single entry point for: Redraw, Full Screen, Show/Hide Legend, Download `<lab>.bib` (whole-lab BibTeX), Download PNG, Copy PNG to clipboard. The `<lab>` label always matches the actual downloaded filename.
- PNG export of the collaboration graph (download or copy to clipboard). The legend is composited natively to canvas — no external dependency, no perceptible delay.
- Full Screen icon (bottom-right, expand/compress glyph in YouTube style) replaces the text button. Tooltip and the matching menu entry switch between "Full Screen" and "Exit Full Screen" automatically.
- Per-publication `[.bib]` toggle in the modal overlay reveals an inline `<pre>` with the BibTeX entry. A sphinx_copybutton-style copy button (revealed on hover) sits in the top-right of each `<pre>`.
- Per-publication `[abstract]` toggle for publications that carry an abstract (HAL).
- Per-list "Download .bib" button (author or author-pair) now sits right-aligned on the same line as the "Publications of …" / "Joint publications from …" header (used to wrap to a new line below).
- All overlay button handling uses event delegation on the modal body — no per-click listener attachment.

### New features

- Add `LabMap.to_bib(name=None, query=None)` to export a lab's publications as a BibTeX file. Optional `query` argument reuses `select_publications` to filter (string match, fuzzy title, or callable).
- Add `LabMap.to_json(name=None)` and `LabMap.to_csv(name=None)`. CSV produces two files (`<name>_authors.csv`, `<name>_publications.csv`).
- Add `pub_to_bibtex(pub)` in `gismap.sources.bibtex` for per-publication BibTeX rendering (handles all `Publication` subclasses including `SourcedPublication` with `note = {Also at: …}` for non-primary source URLs).
- Add `to_dict()` on `Author`, `Publication`, `SourcedAuthor`, `SourcedPublication`, and `LabAuthor` for JSON-friendly serialization.
- Tuning kwargs on `LabMap.__init__`: `max_co_authors`, `min_title_words`, `taboo_words`, `taboo_authors`. Subclasses can adjust default filters without mutating `publication_selectors` by index.
- `LaasMap`/`LaasFull` (`gismap.lab_examples.toulouse`) gain `department_level` to label authors by parent department; `LaasFull` gains `with_support` to include LAAS support services and deduplicates authors appearing in multiple teams.

### Documentation

- New tutorial `docs/tutorials/haltools.ipynb` covering `diff_sources()` and `find_duplicates()` end-to-end (clean profile, messy profile, duplicate-heavy profile, and `pid`-vs-fullname diagnosis). Wired into `docs/tutorials/index.md` and the FAQ Binder list.
- The haltools notebook is shipped with stored outputs on purpose: the analysis text references specific HAL/LDB items, so a stale narrative would be worse than a slightly stale snapshot. Re-execute locally before each release.
- Removed the *Analyzing sources* section from `docs/tutorials/egomap.ipynb` (now superseded by the dedicated tutorial).
- New `## Exporting a lab` section in `docs/tutorials/lab_tutorial.ipynb` showing `to_bib()` (whole-lab and `query=`-filtered), `to_json()`, and `to_csv()`.
- Updated lab_tutorial's "Few things about the generated graph" enumeration to describe the hamburger menu, the bottom-right Full Screen icon, and the in-modal `[.bib]` / `[abstract]` / "Download .bib" affordances.
- Refreshed the FAQ: the *graph is spinning* and *it's too small* recipes now refer to the new menu and icon (`Redraw` is now a menu entry, not a standalone button); the *publication should be there in my LabMap* section leads with the new constructor kwargs (`max_co_authors`, `min_title_words`, `taboo_words`, `taboo_authors`) and keeps `publication_selectors` as the advanced escape hatch.

### Improvements

- HTML output is ~4× smaller for typical labs. Each publication is now shipped once in a shared JS dict and referenced by key from nodes and edges; the modal is rendered on click from that dict, instead of inlining the full publication HTML once per author and once per author-pair. Internal refactor of `gismap.gisgraphs.graph` and `gismap.gisgraphs.js`.
- `LAAS_TABOO` now extends `editorials` instead of duplicating it.
- Docstrings completed on `LaasMap`, `LaasFull`, and `LabMap` (full Parameters sections).
- `LabMap.save_html()` and the new export methods raise `ValueError` if neither `name=` nor `self.name` is set, instead of crashing on `Path(None)`.
- LDB cache is now stored under a Python-version-specific subdirectory (`<user_data_dir>/gismap/py{X.Y}/ldb.pkl.zst`) so that running gismap from multiple Python interpreters on the same machine no longer leads to mutually corrupted dumps. Users with several Python versions will pay one (re-)`retrieve` per interpreter; mono-Python users see no change other than the new path.

### Bug fixes

- Modal overlay was unreadable in Jupyter dark mode (fixed-light card on dark canvas). Modal colors now resolve through `var(--pst-color-…, var(--jp-…, fallback))` chains so the modal follows the host theme.
- Harden JSON embedded inside `<script>`: any `</` (e.g. `</script>` inside a publication title) is rewritten to `<\/`, neutralizing a tag-breakout vector.
- Fix `LaasMap._author_iterator` department-level scraping: `find("p", {"class", "font11"})` (a set) was silently wrong; replaced by `{"class": "font11"}` (a dict).
- Fix `LDB._initialized = True` being set even when `search_engine` was `None` (e.g. interrupted download leaving the GitHub release pickle as-is, or pre-existing dump from a previous build). Subsequent `search_author()` calls then crashed with `AttributeError: 'NoneType' object has no attribute 'extract'`. `LDB.load()` now rebuilds and re-dumps the search engine whenever the loaded state has none.
- `LDB._download_file` now writes through `safe_write` (temp file + atomic rename) so an interrupted download no longer leaves a partial `ldb.pkl.zst` that the next run would try to load.

## 0.5.3 (2026-04-09): HALTools v1

### New features

- Add `diff_sources()` to compare publications between two databases or search strategies
- Add `find_duplicates()` to find duplicate publications within a single database
- Add `select_publications()` method for querying publications of a lab by fuzzy title match, key, or callable filter
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
- Add `Publication.short_str()` for compact one-line display with URL
- Add `SourcedPublication.url` property (delegates to first source with a URL)

### Bug fixes

- Fix comets (singletons) legend: checkbox visibility is now fully dynamic, appearing only when singletons exist for the current group selection
- Fix `HALAuthor.check_cv()`: adapt CV page detection to current HAL markup (`soup.main.section` instead of `soup.form`), and catch `AttributeError` in image extraction
- Fix `LDB.search_author()` returning duplicate entries when aliases normalize to the same name; deduplicate at index build time and at query time
- Fix `regroup_publications()` partition bug: a publication matching two groups could appear in both instead of just the first

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
