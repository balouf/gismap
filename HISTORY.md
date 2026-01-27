# History

## Pipeline

- anHALyze: tools to spot HAL issues (bad author metadata, DBLP comparison, widget)
- EgoConf: find your conferences journals
- Easier access to graph customization
- Additional graph option (e.g. time filtering and coloring, default group checks...)
- Custom CSS (e.g. transparent background)
- Gismo integration

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

- New lab structure: EgoMap shows the people that revolves around you!
- New lab method: expansion, which adds *moons* (neighbor researchers).
- Add filters when building authors and publications.
- Physic engine changed for better visualization.
- Multi-source handling fine-tuned.
- Better display (size and theme).


## 0.1.0 (2025-07-24): First release

- First release on PyPI.
- Online DBLP and HAL DB implemented.
- Lab structures implemented.
- Early version of collaboration graph available.
