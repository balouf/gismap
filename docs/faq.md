# FAQ

## Stars, planets, moons, comets?

The *Maps*, i.e., the graphical representation of the collaboration graph, use vocabulary borrowed from astronomy.

- **Stars** and **Planets**: For EgoMaps, you are the *star*, e.g., the center of your own universe. *Planets* are people that revolve around you, i.e., your co-authors.
- **Moons**: A *moon* is a researcher connected to a planet or a lab.
- **Comets**: A comet has no direct link with other displayed entities.

## How to embed a Map on my website?

- For a simple and static embedding, you can use [Binder to manually generate the Map](https://mybinder.org/v2/gh/balouf/gismap/HEAD?urlpath=%2Fdoc%2Ftree%2Fbinder%2Finteractive.ipynb).
- For something more advanced, it is recommended to write a Python script that generates the Map.

## What databases are available, and what are their advantages?

| Database   | Pros                                         | Cons                                        |
|------------|----------------------------------------------|---------------------------------------------|
| HAL        | - Fast<br>- Rich metadata                     | - France-based research only<br>- Errors and gaps exist |
| DBLP       | - Highly accurate<br>- Unified venue names   | - Computer Science only<br>- Very slow      |
| Local DBLP | - Ultra-fast                                 | - Not integrated yet<br>- DBLP cons<br>- No unique search keys |

## Why doesn’t GisMap use database X?

I wanted to rely on publication databases that:

- have a public API;
- are relatively clean and up to date;
- do not require an API key.

To date, only HAL and DBLP seem to meet these specifications.

That said, GisMap is designed to be multi-source, so if a contributor wants to add an interface to another database (Google Scholar, ORCID, ...), they are encouraged to write it and make a PR!
