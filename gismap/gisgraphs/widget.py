import re
import unicodedata
import base64
from IPython.display import display, HTML
import ipywidgets as widgets
from contextlib import contextmanager

from gismap.lab.egomap import EgoMap
from gismap.lab.labmap import ListMap


@contextmanager
def dummy_context():
    yield


def safe_filename(name):
    """
    Parameters
    ----------
    name: :class:`str`
        Pretty much anything.

    Returns
    -------
    :class:`str`
        GisMap filename.
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.replace(" ", "_")
    safe_str = re.sub(r"[^a-zA-Z0-9_]", "", ascii_only)
    return f"gismap-{safe_str[:60]}.html"


place_holder = "Diego Perino, The-Dang Huynh, François Durand (hal: fradurand, ldb: 38/11269), Rim Kaddah, Leonardo Linguaglossa, Céline Comte"


class GismapWidget:
    """
    A simple widget to test the production of LabMaps and EgoMaps.

    Examples
    --------

    This is a doctest example. Use a notebook to play with the widget.

    >>> gw = GismapWidget()  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    VBox(children=(HTML(value=''), Output(), HBox(children=(Textarea(value='', ...
    >>> gw.names.value = "Fabien Mathieu"
    >>> gw.dbs.value = "HAL"
    >>> gw.size.value = 3
    >>> gw.compute_function(gw.compute, show=False)
    >>> gw.save_link.value[:30]
    "<a href='data:text/html;base64"
    >>> gw.names.value = "Diego Perino, Laurent Viennot"
    >>> gw.compute_function(gw.compute, show=False)
    >>> gw.save_link.value[:30]
    "<a href='data:text/html;base64"
    """

    def __init__(self):
        self.names = widgets.Textarea(
            placeholder=place_holder,
            description="Name(s):",
            layout=widgets.Layout(width="50%", height="100px"),
        )
        self.dbs = widgets.RadioButtons(
            options=["HAL", "LDB", "Both"],
            description="DB(s):",
            layout=widgets.Layout(width="80px", max_width="20%"),
        )
        self.size = widgets.IntSlider(
            value=10,
            min=1,
            max=150,
            step=1,
            description="Size",
            layout=widgets.Layout(width="250px"),
        )
        self.compute = widgets.Button(
            description="Map!", layout=widgets.Layout(width="120px", max_width="140px")
        )
        self._col = widgets.VBox(
            [self.size, self.compute],
            layout=widgets.Layout(
                align_items="center", max_width="27%", overflow="hidden"
            ),
        )
        self.save_link = widgets.HTML(value="")
        self.compute.on_click(self.compute_function)
        self.out = widgets.Output()
        self.widget = widgets.VBox(
            [self.save_link, self.out, widgets.HBox([self.names, self._col, self.dbs])]
        )
        display(self.widget)
        self.show = True

    def html(self):
        dbs = (
            "hal"
            if self.dbs.value == "HAL"
            else "ldb"
            if self.dbs.value == "LDB"
            else ["hal", "ldb"]
        )
        name = self.names.value
        pattern = r",\s*(?![^()]*\))"
        names = [n.strip() for n in re.split(pattern, name)]
        self.save_link.value = ""
        ctx = self.out if self.show else dummy_context()
        if len(names) > 1:
            lab = ListMap(names, dbs=dbs, name="planet")
            if self.show:
                self.out.clear_output()
            with ctx:
                lab.update_authors()
                lab.update_publis()
                extra = self.size.value - len(lab.authors)
                if extra > 0:
                    lab.expand(target=extra)
        else:
            lab = EgoMap(names[0], dbs=dbs)
            if self.show:
                self.out.clear_output()
            with ctx:
                lab.build(target=self.size.value)
        return lab.html()

    def compute_function(self, b, show=True):
        self.show = show
        full = self.html()
        b64 = base64.b64encode(
            f"<html><body>{full}</body></html>".encode("utf8")
        ).decode("utf8")
        payload = f"data:text/html;base64,{b64}"
        savename = safe_filename(self.names.value)
        link_html = (
            f"<a href='{payload}' download='{savename}'>Download the Map!</a>"
        )
        self.save_link.value = link_html
        if show:
            self.out.clear_output()
            with self.out:
                display(HTML(full))
