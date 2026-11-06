# Urban data analytics with pyautark

Jupyter notebooks that teach [pyautark](https://github.com/urban-toolkit/pyautark), the Python API of
[Autark](https://autarkjs.org/), modeled after the [Autark tutorial](https://github.com/ctsilva/autark-tutorial)
(the SIBGRAPI 2026 notebooks). The tutorial follows the same six parts. Where the Autark tutorial calls
`autk-db`, `autk-map`, `autk-plot` and `autk-compute` from JavaScript, these notebooks describe the same work in
Python: you build a specification out of Python objects, and the widget draws it in the notebook, in the browser,
with WebGPU.

| Notebook | Autark tutorial | What it covers |
|---|---|---|
| `01-overview.ipynb` | 01 | What pyautark is, how a spec becomes a view, first map. |
| `02-formats.ipynb` | 02 | Vector and raster data; GeoJSON, WKT, GeoTIFF, OSM; pandas and GeoPandas. |
| `03-data.ipynb` | 03 | Loading each format as a table; spatial joins; heatmaps; what to do in pandas instead of SQL. |
| `04-maps.ipynb` | 04 | Layers, OSM base map, rasters, thematic color, picking and linking. |
| `05-plots.ipynb` | 05 | Scatter plots, histograms, tables, brushing, linked views, selections in Python. |
| `06-compute.ipynb` | 06 | Per-feature WGSL computation; render analysis (sky exposure). |

## Running it

You need [uv](https://docs.astral.sh/uv/), a sibling checkout of pyautark (`../pyautark`, branch with the UrbanSpec
builders) and a browser with WebGPU (Chrome or Edge 113+, recent Safari; Firefox Nightly with WebGPU enabled).

```sh
uv sync
uv run jupyter lab
```

Start Jupyter from this folder: the notebooks load the sample data from `/files/data/...`, which Jupyter serves
relative to the folder it was started in. No network is needed; the OpenStreetMap examples read a local extract.

After rebuilding pyautark's widget bundle, restart the notebook's kernel (Kernel → Restart) and reload the page: the kernel
keeps the bundle it loaded, so a running kernel shows the old one.

## Layout

| Path | Purpose |
|---|---|
| `*.ipynb` | The notebooks, in reading order. |
| `tutorial.py` | `url()` for the data files and `read_json()`; imported by every notebook. |
| `data/` | Sample data by notebook: `formats/`, `db/`, `map/`, `compute/`, and `osm/` (a lower Manhattan extract). |
| `scripts/check.py` | Executes every notebook and checks that each view draws (needs Chrome). |

## Differences from the JavaScript tutorial

pyautark is declarative: you describe the data, the derived tables, the maps and the plots, and the engine runs them.
So there is no map lifecycle to manage (`new AutkMap`, `init`, `draw`), no SQL and no workspaces in the API, and the
view is a widget, not a canvas you hold. Part 03 shows what replaces SQL filters and group-bys, and notebook 06 shows
render analysis through `Compute.render`.
