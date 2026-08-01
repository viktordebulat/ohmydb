"""Builds a static, read-only demo snapshot of the frontend into docs/demo/
for GitHub Pages: copies app/web/ verbatim and pre-renders the JSON the
frontend fetches at runtime into files at the same paths, so app.js's
fetch('/api/...') calls resolve against plain static files (query strings are
ignored by static hosting, which is all `?direct=true` needs).

Requires a populated catalog (run `task sync` first) — see `task demo:build`.
"""

import shutil
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.api import WEB_DIR, create_app
from app.config import load_config

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.example.yaml"
OUT_DIR = REPO_ROOT / "docs" / "demo"


def _write_json(path: Path, response) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)


def build() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    client = TestClient(create_app(load_config(CONFIG_PATH)))
    api_dir = OUT_DIR / "api"

    clusters_res = client.get("/api/clusters")
    clusters_res.raise_for_status()
    _write_json(api_dir / "clusters", clusters_res)
    clusters = clusters_res.json()

    entity_count = 0
    for cluster in clusters:
        c = quote(cluster, safe="")
        graph_res = client.get(f"/api/graph/{c}")
        graph_res.raise_for_status()
        _write_json(api_dir / "graph" / c, graph_res)

        for node in graph_res.json()["nodes"]:
            d = quote(node["database"], safe="")
            n = quote(node["name"], safe="")
            rel_res = client.get(f"/api/entities/{c}/{d}/{n}/relations", params={"direct": "true"})
            if rel_res.status_code != 200:
                continue
            _write_json(api_dir / "entities" / c / d / n / "relations", rel_res)
            entity_count += 1

    shutil.copy(WEB_DIR / "index.html", OUT_DIR / "index.html")
    shutil.copy(WEB_DIR / "app.css", OUT_DIR / "app.css")
    shutil.copy(WEB_DIR / "app.js", OUT_DIR / "app.js")
    shutil.copytree(WEB_DIR / "vendor", OUT_DIR / "vendor")

    print(f"demo snapshot: {len(clusters)} cluster(s), {entity_count} entit(y/ies) -> {OUT_DIR}")


if __name__ == "__main__":
    build()
