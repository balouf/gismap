"""
Build script for creating the LDB (Local DBLP) database.

Run as a module to download and process the DBLP dataset:

    python -m gismap.build

This will fetch the DBLP RDF dump from the website and create a compressed local database.
"""

if __name__ == "__main__":
    import argparse
    from gismap.sources.ldb import LDB

    parser = argparse.ArgumentParser(
        description="Build LDB database from DBLP TTL dump."
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Exclude search engine from output (for GitHub assets).",
    )
    args = parser.parse_args()

    LDB.build_db()
    LDB.dump_db(include_search=not args.no_search)
