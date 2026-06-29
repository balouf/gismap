from gismap.lab_examples.lip6 import given_name_first


def test_two_tokens_surname_first():
    assert given_name_first("Miné Antoine") == "Antoine Miné"


def test_multi_token_given_name():
    # Surname is the first token; the rest is the given name.
    assert given_name_first("Lieu Choun Tong") == "Choun Tong Lieu"


def test_single_token_unchanged():
    assert given_name_first("Madonna") == "Madonna"


def test_empty_unchanged():
    assert given_name_first("") == ""
