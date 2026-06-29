import pickle

import pytest

from gismap.utils.zlist import ZList, train_dict


def _records(n):
    """LDB-like items: (key, [names], [pub indices])."""
    return [(f"{i % 97}/{i}", [f"Author {i}", f"A. {i}"], [i, i + 1]) for i in range(n)]


class TestRoundTrip:
    def test_from_iterable_random_access(self):
        data = _records(250)
        z = ZList.from_iterable(data, frame_size=16)
        assert len(z) == 250
        assert z[0] == data[0]
        assert z[123] == data[123]
        assert z[-1] == data[-1]
        assert list(z) == data

    def test_context_manager_append(self):
        data = _records(100)
        with ZList(frame_size=7) as z:
            for item in data:
                z.append(item)
        assert list(z) == data

    def test_out_of_bounds_raises_indexerror(self):
        z = ZList.from_iterable(list("abcde"), frame_size=2)
        assert z[-1] == "e"
        with pytest.raises(IndexError):
            _ = z[5]
        with pytest.raises(IndexError):
            _ = z[-6]


class TestPickling:
    def test_pickle_roundtrip(self):
        # LDB persists ZLists by pickling them inside its state dict.
        z = ZList.from_iterable(_records(120), frame_size=11)
        z2 = pickle.loads(pickle.dumps(z))
        assert len(z2) == 120
        assert z2[42] == z[42]
        assert list(z2) == list(z)


class TestDictionary:
    def test_dict_compression_roundtrip(self):
        data = [f"publication {i} about networks graphs and distributed systems {i % 13}" for i in range(3000)]
        d = train_dict(data, dict_size=8192, max_samples=2000)
        z = ZList.from_iterable(data, frame_size=5, level=19, dict_data=d)
        assert z[1234] == data[1234]
        assert list(z) == data
        # The dictionary must survive pickling (it travels with the LDB dump).
        z2 = pickle.loads(pickle.dumps(z))
        assert z2[1234] == data[1234]

    def test_train_dict_is_deterministic(self):
        data = [f"item {i} text payload {i % 7}" for i in range(3000)]
        assert train_dict(data, dict_size=8192).as_bytes() == train_dict(data, dict_size=8192).as_bytes()


class TestOptimize:
    def test_small_source_becomes_plain_list(self):
        z = ZList.from_iterable(_records(100), frame_size=10)
        out = z.optimize()
        assert isinstance(out, list)
        assert out == _records(100)

    def test_tight_budget_stays_zlist(self):
        z = ZList.from_iterable(_records(100), frame_size=10)
        out = z.optimize(max_bytes=1)
        assert isinstance(out, ZList)
        assert list(out) == _records(100)

    def test_estimated_size_positive(self):
        z = ZList.from_iterable([("x" * 100,) for _ in range(50)], frame_size=10)
        assert z.estimated_uncompressed_size() > 0
