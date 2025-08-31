def taboos(txt, words):
    if isinstance(words, str):
        return words not in txt
    else:
        return all(w not in txt for w in words)

def publication_size_filter(n_max=10):
    return lambda p: len(p.authors) < n_max

def publication_taboo_filter(w=None):
    if w is None:
        w = ["Editorial", "Foreword"]
    return lambda p: taboos(p.title, w)

def author_taboo_filter(w=None):
    if w is None:
        w = ["Buob", "Kofman"]
    return lambda a: taboos(a.name, w)
