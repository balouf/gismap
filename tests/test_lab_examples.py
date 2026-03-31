"""Tests that lab_examples _author_iterator() returns a reasonable number of authors."""

from time import time

import pytest

from gismap.lab_examples.cotel import AlgoRes2016, AlgoRes2026
from gismap.lab_examples.irif import IrifMap
from gismap.lab_examples.lamsade import Lamsade
from gismap.lab_examples.lincs import LINCS
from gismap.lab_examples.toulouse import LaasMap

TIME_BUDGET = 10.0


@pytest.mark.parametrize(
    "lab_cls, min_authors",
    [
        (IrifMap, 13),
        (Lamsade, 36),
        (LINCS, 57),
        (LaasMap, 37),
        (AlgoRes2026, 36),
        (AlgoRes2016, 31),
    ],
    ids=["graphes", "Lamsade", "LINCS", "sara", "AlgoRes2026", "AlgoRes2016"],
)
def test_author_iterator(lab_cls, min_authors):
    lab = lab_cls()
    count = 0
    start = time()
    for _ in lab._author_iterator():
        count += 1
        if time() - start > TIME_BUDGET:
            break
    assert count >= min_authors, f"{lab_cls.__name__}: got {count}, expected >= {min_authors}"
