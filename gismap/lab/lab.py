from bof.fuzz import Process
from collections import defaultdict
import numpy as np

from gismap.lab.member import Member
from gismap.lab.publication import Publication
from gismap.utils.common import get_classes
from gismap.utils.logger import logger
from gismap.utils.mixinio import MixInIO
from gismap.utils.requests import autosession
from gismap.database.blueprint import DBAuthor


class Lab(MixInIO):
    """
    Parameters
    ----------
    members: :class:`list` of `str`
        Names of the lab members.
    db_dict: :class:`dict`
        Publication DBs to use. Default to all available.


    Examples
    --------

    Use a two-people lab for example.

    >>> mini_lab = Lab(['Fabien Mathieu', 'François Baccelli'])

    Get DB ids

    >>> from gismap import HALAuthor, DBLPAuthor
    >>> mini_lab.manual_update([HALAuthor(name='François Baccelli', id='francois-baccelli',
    ...                                                     aliases=['Francois Baccelli']),
    ... DBLPAuthor(name='François Baccelli', id='b/FrancoisBaccelli'),
    ... DBLPAuthor(name='Fabien Mathieu', id='66/2077')])


    >>> mini_lab.get_ids()
    >>> mini_lab.member_list # doctest: +NORMALIZE_WHITESPACE
    [Member(name='Fabien Mathieu'),
    Member(name='François Baccelli')]

    There is one entry missing (it was in the warnings). Let us manually set it.

    Now we fetch publications:

    >>> mini_lab.get_publications()

    How many publications per member?

    >>> production = [len(a.publications) for a in mini_lab.member_list]
    >>> [p >= 100 for p in production]
    [True, True]
    >>> [p >= 250 for p in production]
    [False, True]

    Consider one publication.

    >>> key = mini_lab.members['Fabien Mathieu'].publications[0]
    >>> publi = mini_lab.publications[key]

    Use the string property to have a simple bibliography entry:

    >>> publi.string # doctest: +NORMALIZE_WHITESPACE
    'Making most voting systems meet the Condorcet criterion reduces their manipulability,
    by François Durand, Fabien Mathieu, Ludovic Noirie. unpublished, 2014.'

    Use publi_to_text for something more content-oriented:

    >>> mini_lab.publi_to_text(key) # doctest: +NORMALIZE_WHITESPACE
    'Making most voting systems meet the Condorcet criterion reduces their manipulability\\nSince any non-trivial voting
    system is susceptible to manipulation, we investigate how it is possible to reduce the set of situations where it is
    manipulable, that is, such that a coalition of voters, by casting an insincere ballot, may secure an outcome that is
    better from their point of view. We prove that, for a large class of voting systems, a simple modiﬁcation allows to
    reduce manipulability. This modiﬁcation is Condorciﬁcation: when there is a Condorcet winner, designate her;
    otherwise, use the original rule. Our very general framework allows to do this for any voting system, whatever the
    form of the original ballots. Hence, when searching for a voting system whose manipulability is minimal, one can
    restrict to those that meet the Condorcet criterion.'

    Use member_to_text to get the content of a member:

    >>> mini_lab.member_to_text("Fabien Mathieu")[:100]
    'Making most voting systems meet the Condorcet criterion reduces their manipulability\\nSince any non-t'

    >>> from collections import Counter
    >>> copublis = [k for k, v in Counter(p for m in mini_lab.members.values() for p in m.publications).items() if v>1]
    >>> print("\\n".join(mini_lab.publications[p].string for p in copublis)) # doctest: +NORMALIZE_WHITESPACE
    On Spatial Point Processes with Uniform Births and Deaths by Random Connection,
    by François Baccelli, Fabien Mathieu, Ilkka Norros. unpublished, 2014.
    Mutual Service Processes in Euclidean Spaces: Existence and Ergodicity,
    by François Baccelli, Fabien Mathieu, Ilkka Norros. Queueing Systems, 2017.
    Spatial Interactions of Peers and Performance of File Sharing Systems,
    by François Baccelli, Fabien Mathieu, Ilkka Norros. unpublished, 2012.
    Can P2P Networks be Super-Scalable?,
    by François Baccelli, Fabien Mathieu, Ilkka Norros, Rémi Varloot. IEEE Infocom 2013 - 32nd IEEE International
    Conference on Computer Communications, 2013.
    Supra-extensibilité des réseaux P2P,
    by François Baccelli, Fabien Mathieu, Ilkka Norros, Rémi Varloot. 15èmes Rencontres Francophones sur les Aspects
    Algorithmiques des Télécommunications (AlgoTel), 2013.
    Performance of P2P Networks with Spatial Interactions of Peers,
    by François Baccelli, Fabien Mathieu, Ilkka Norros. CoRR, 2011.
    """
    constructor = Member
    """Class attribute: constructor for members of the lab."""

    def __init__(self, members, db_dict=None):
        self.members = dict()
        self.member_keys = None
        if db_dict is None:
            db_dict = get_classes(DBAuthor, key='db_name')
        for name in members:
            member = self.constructor(name, db_dict=db_dict)
            self.members[member.key] = member
        self.publications = None
        self.s = autosession(None)

    @property
    def member_list(self):
        """
        :class:`list`
            List of lab members.
        """
        return [m for m in self.members.values()]

    def manual_update(self, up_list):
        """
        Inject some populated DBAuthors in the lab.

        Parameters
        ----------
        up_list: :class:`list` of :class:`~gismap.database.blueprint.DBAuthor`
            Info to inject.

        Returns
        -------
        None
        """
        for db_auth in up_list:
            name = db_auth.name
            if name not in self.members:
                logger.warning(f"{name} is not a registered team author.")
                continue
            member = self.members[name]
            db = db_auth.db_name
            member.sources[db].update_values(db_auth)

    def get_ids(self, rewrite=False):
        """
        Get DB identifiers.

        Parameters
        ----------
        rewrite: :class:`bool`, default=False
            Update even if identifiers are already set.

        Returns
        -------
        None
        """
        for member in self.members.values():
            member.prepare(s=self.s, backoff=True, rewrite=rewrite)

    def compute_keys(self):
        """
        Makes a key dictionary so that any name, alias, or db identifier of a member can be linked to her key.

        Returns
        -------
        None
        """
        self.member_keys = dict()
        for member in self.members.values():
            target = member.key
            for db_author in member.sources.values():
                for key in db_author.iter_keys():
                    self.member_keys[key] = target

    def get_publications(self, threshold=.9, length_impact=.2):
        """
        * Retrieve all publications from members in their databases
        * Remove full duplicates
        * Gather pseudo-duplicates and populate publications
        * Populate each member's publication list with her publications' keys.

        Returns
        -------
        None
        """
        self.publications = dict()
        self.compute_keys()
        raw = []
        for member in self.members.values():
            raw += member.get_papers(s=self.s, backoff=True)

        raw = [p for p in {a['key']: a for a in raw}.values()]

        p = Process(length_impact=length_impact)
        p.fit([p['title'] for p in raw])

        done = np.zeros(len(raw), dtype=bool)
        for i, paper in enumerate(raw):
            if done[i]:
                continue
            locs = np.where(p.transform([paper['title']], threshold=threshold)[0, :] > threshold)[0]
            article = Publication([raw[i] for i in locs])
            self.publications[article.key] = article
            done[locs] = True

        aut2pap = defaultdict(set)
        for k, paper in self.publications.items():
            for a in paper.authors:
                for author_id in a.iter_keys():
                    if author_id in self.member_keys:
                        aut2pap[self.member_keys[author_id]].add(k)

        for author, papers in aut2pap.items():
            self.members[author].publications = sorted(papers)

    def publi_to_text(self, key):
        """
        Simple texter that gives title and abstract (if any) from a publication key.

        Parameters
        ----------
        key: :class:`str`
            Identifier of a publication.

        Returns
        -------
        :class:`str`
            Publication description.
        """
        paper = self.publications[key]
        res = paper.title
        if paper.abstract:
            res = f"{res}\n{paper.abstract}"
        return res

    def member_to_text(self, key):
        """
        Simple texter that concatenates all publications of a member (titles and possibly abstracts).

        Parameters
        ----------
        key: :class:`str`
            Identifier of a member.

        Returns
        -------
        :class:`str`
            Member description.
        """
        member = self.members[self.member_keys[key]]
        return "\n".join(self.publi_to_text(k) for k in member.publications)
