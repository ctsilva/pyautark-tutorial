"""Small helpers shared by the notebooks."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# The notebooks are served by Jupyter from this folder, so the browser can fetch the sample data from /files/....
# autark warns about root-relative URLs because the widget normally has no server; here there is one.
warnings.filterwarnings("ignore", message=".*root-relative.*")


def url(path: str) -> str:
    """URL, as the browser sees it, of a file under this folder (for example ``data/map/mnt_neighs.geojson``)."""
    return f"/files/{path}"


def read_json(path: str):
    """A JSON or GeoJSON file under this folder, as Python objects."""
    return json.loads((ROOT / path).read_text(encoding="utf-8"))
