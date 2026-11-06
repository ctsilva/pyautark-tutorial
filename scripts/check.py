"""Executes every notebook, then draws every spec the notebooks build in Chrome and checks that it renders.

    uv run python scripts/check.py [notebook-prefix ...]

Needs Google Chrome (WebGPU). Screenshots go to ``.check/``.
"""

from __future__ import annotations

import http.server
import io
import json
import sys
import threading
from pathlib import Path

import autark
import nbformat
from nbclient import NotebookClient
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(autark.__file__).parent / "static"
OUT = ROOT / ".check"

# Added as the first cell of every notebook: record each spec that a notebook shows as a widget.
RECORDER = """
import json, os
import autark.spec as _s
_orig = _s.AutarkSpec.widget
def _widget(self, *a, **k):
    with open(os.environ["CHECK_SPECS"], "a") as f:
        f.write(json.dumps(self.to_dict()) + "\\n")
    return _orig(self, *a, **k)
_s.AutarkSpec.widget = _widget
"""

HARNESS = """<!doctype html><meta charset=utf-8><body style="margin:0;width:1000px">
<script type=module>
// Every widget of a notebook lives in one page. Each one loads the bundle for itself, as anywidget does, and
// that is what exposed ids that were only unique within one widget.
window.runWidget = async (spec, index) => {
  const el = document.createElement('div');
  el.id = 'w' + index;
  el.style.cssText = 'width:1000px;height:760px';
  document.body.appendChild(el);
  const mod = await import('/autark-widget.js?widget=' + index);
  const values = new Map([['spec', spec], ['height', '760px']]);
  await mod.default.render({ model: { get: n => values.get(n), on(){}, off(){} }, el });
  return { canvases: el.querySelectorAll('canvas').length, svgs: el.querySelectorAll('svg').length,
           error: el.querySelector('pre')?.textContent.slice(0, 400) ?? null };
};
window.ready = true;
</script>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = path.split("?")[0]
        if path.startswith("/files/"):
            return str(ROOT / path[len("/files/"):])
        return str(STATIC / path.lstrip("/"))

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if self.path.split("?")[0] == "/harness.html":
            body = HARNESS.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args) -> None:
        pass


def drawn_fraction(png: bytes) -> float:
    """Share of pixels that differ from the map background, outside the menu button and the legend."""
    image = Image.open(io.BytesIO(png)).convert("RGB")
    width, height = image.size
    pixels = image.load()
    background = max(image.getcolors(maxcolors=width * height), key=lambda c: c[0])[1]
    other = total = 0
    for y in range(height):
        for x in range(width):
            if (x < 70 and y < 70) or (x > width - 280 and y > height - 100):
                continue
            total += 1
            other += pixels[x, y] != background
    return other / total


def execute(notebook: Path, specs_file: Path) -> None:
    nb = nbformat.read(notebook, as_version=4)
    nb.cells.insert(0, nbformat.v4.new_code_cell(RECORDER))
    import os

    os.environ["CHECK_SPECS"] = str(specs_file)
    NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()


def main(prefixes: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", args=["--enable-unsafe-webgpu"])
        for notebook in sorted(ROOT.glob("[0-9][0-9]-*.ipynb")):
            if prefixes and not any(notebook.name.startswith(x) for x in prefixes):
                continue
            specs_file = OUT / f"{notebook.stem}.jsonl"
            specs_file.unlink(missing_ok=True)
            try:
                execute(notebook, specs_file)
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL {notebook.name}: kernel: {str(exc)[-400:]}")
                failures += 1
                continue
            specs = [json.loads(line) for line in specs_file.read_text().splitlines()] if specs_file.exists() else []
            print(f"ok   {notebook.name}: {len(specs)} widget(s)")
            page = browser.new_page(viewport={"width": 1000, "height": 760})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)[:200]))
            page.on("console", lambda m: m.type == "error" and errors.append(m.text[:200]))
            page.goto(f"{base}/harness.html")
            page.wait_for_function("window.ready")
            infos = [page.evaluate("([s, i]) => window.runWidget(s, i)", [spec, index]) for index, spec in enumerate(specs)]
            page.wait_for_timeout(3000)
            for index, info in enumerate(infos):
                element = page.locator(f"#w{index}")
                element.scroll_into_view_if_needed()
                png = element.screenshot(path=str(OUT / f"{notebook.stem}-{index + 1}.png"))
                blank = info["canvases"] > 0 and drawn_fraction(png) < 0.00005
                bad = info["error"] or blank
                failures += bool(bad)
                note = info["error"] or ("the map is blank" if blank else "")
                print(f"  {'FAIL' if bad else 'ok  '} #{index + 1} canvases={info['canvases']} svgs={info['svgs']} {note}")
            if errors:
                failures += 1
                print(f"  FAIL page errors: {errors[:3]}")
            page.close()
        browser.close()
    server.shutdown()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
