from gismap.gisgraphs.graph import initials, node_labels


class TestInitials:
    def test_simple_first_last(self):
        assert initials("Fabien Mathieu") == "FM"

    def test_composite_first_name_hyphen(self):
        assert initials("Jean-François Laslier") == "JFL"

    def test_composite_first_name_spaces(self):
        # Two separate given names also expand to three initials.
        assert initials("Jean François Laslier") == "JFL"

    def test_particle_is_skipped(self):
        # A lowercase particle ("de") does not contribute an initial.
        assert initials("Élie de Panafieu") == "ÉP"

    def test_single_token_name(self):
        assert initials("Madonna") == "M"

    def test_two_letters_for_common_case(self):
        assert initials("Jérôme Lang") == "JL"


class TestNodeLabels:
    def test_disambiguates_shared_initials(self):
        labels = node_labels(
            {
                "lang": "Jérôme Lang",
                "lesca": "Julien Lesca",
                "laslier": "Jean-François Laslier",
            }
        )
        assert labels["lang"] == "JLa"
        assert labels["lesca"] == "JLe"
        # Composite first name already distinct: untouched.
        assert labels["laslier"] == "JFL"

    def test_no_collision_keeps_base_initials(self):
        labels = node_labels({"fm": "Fabien Mathieu", "cc": "Céline Comte"})
        assert labels == {"fm": "FM", "cc": "CC"}

    def test_disambiguation_extends_until_distinct(self):
        # Same first initial and surname starting with the same letters:
        # the labels grow until they differ.
        labels = node_labels({"a": "Marie Leblanc", "b": "Marie Lebrun"})
        assert labels["a"] != labels["b"]
        assert labels["a"].startswith("ML")
        assert labels["b"].startswith("ML")

    def test_true_homonyms_do_not_loop(self):
        # Identical names cannot be distinguished by the surname tail; the
        # function must terminate and return equal labels rather than hang.
        labels = node_labels({"a": "Jean Dupont", "b": "Jean Dupont"})
        assert labels["a"] == labels["b"]

    def test_disambiguation_is_length_capped(self):
        # A "Surname Firstname" source makes a shared first name look like a
        # shared surname; labels must stay bounded instead of growing into
        # "MAntoine" / "MAntoine".
        labels = node_labels({"a": "Miné Antoine", "b": "Mirri Antoine"})
        assert all(len(v) <= 5 for v in labels.values())

    def test_max_len_is_tunable(self):
        labels = node_labels({"a": "Miné Antoine", "b": "Mirri Antoine"}, max_len=3)
        assert all(len(v) <= 3 for v in labels.values())
