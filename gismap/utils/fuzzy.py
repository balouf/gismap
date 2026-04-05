from bof.feature_extraction import CountVectorizer
from bof.fuzz import Process, jit_square_factors


def similarity_matrix(references, candidates=None, n_range=4, length_impact=0.05, key=None, key2=None):
    """
    Compute a similarity matrix between objects using fuzzy n-gram matching.

    When ``candidates`` is None, computes pairwise similarities within ``references``
    (self-comparison). When ``candidates`` is provided, computes cross-similarities
    between ``references`` and ``candidates``.

    Parameters
    ----------
    references : :class:`list`
        Reference objects.
    candidates : :class:`list`, optional
        Candidate objects to compare against references. If None, references
        are compared against themselves.
    n_range : :class:`int`, default=4
        N-gram range for the vectorizer.
    length_impact : :class:`float`, default=0.05
        Impact of length difference on similarity scores.
    key : callable, optional
        Fingerprint extractor for references. Defaults to identity.
    key2 : callable, optional
        Fingerprint extractor for candidates. Defaults to ``key``.

    Returns
    -------
    :class:`~numpy.ndarray`
        Similarity matrix. Shape is ``(len(references), len(references))`` for
        self-comparison, or ``(len(candidates), len(references))`` for cross-comparison.

    Examples
    --------

    >>> m = similarity_matrix(["abc def", "abc deg", "xyz"])
    >>> m.shape
    (3, 3)
    >>> m[0, 1] > 50
    True
    >>> m[0, 2] < 50
    True
    """
    if key is None:
        key = lambda x: x  # noqa: E731
    if key2 is None:
        key2 = key
    if candidates is None:
        vectorizer = CountVectorizer(n_range=n_range)
        x = vectorizer.fit_transform([key(r) for r in references])
        y = x.T.tocsr()
        return jit_square_factors(x.indices, x.indptr, y.indices, y.indptr, len(references), length_impact)
    else:
        p = Process(length_impact=length_impact, n_range=n_range)
        p.allow_updates = False
        p.fit([key(r) for r in references])
        return p.transform([key2(c) for c in candidates])
