"""Headless-browser smoke tests for the static frontend (app/web/).

Auto-skips when Playwright's Chromium isn't installed
(`uv run playwright install chromium`) — mirrors
test_clickhouse_integration.py's auto-skip pattern.
"""

import threading
import time

import pytest
import uvicorn

from app.api import create_app
from app.config import AppConfig, ClusterConfig
from app.core.models import Edge, EdgeKind, Entity, EntityKind
from app.store.db import make_session_factory
from app.store.repo import sync_cluster


def _browser_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _browser_available(),
    reason="playwright chromium not installed (uv run playwright install chromium)",
)


@pytest.fixture
def live_server(tmp_path):
    """A real HTTP server (browsers can't navigate to TestClient) seeded
    with one table read by one materialized view."""
    url = f"sqlite:///{tmp_path}/test.sqlite"
    factory = make_session_factory(url)
    with factory() as s:
        sync_cluster(
            s,
            "c1",
            [
                Entity(cluster="c1", database="app", name="events", kind=EntityKind.TABLE, engine="MergeTree"),
                Entity(cluster="c1", database="analytics", name="mv", kind=EntityKind.MAT_VIEW),
            ],
            [Edge(("c1", "analytics", "mv"), ("c1", "app", "events"), EdgeKind.READS_FROM)],
        )
    cfg = AppConfig(storage_url=url, clusters=[ClusterConfig(name="c1", host="localhost")])

    config = uvicorn.Config(create_app(cfg), host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_table_renders_seeded_entities(live_server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(live_server)
        page.wait_for_selector("#rows tr")
        names = page.locator("#rows tr td:first-child").all_text_contents()
        assert set(names) == {"events", "mv"}
        browser.close()


def test_row_click_renders_relations_tree(live_server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(live_server)
        page.wait_for_selector("#rows tr")
        page.click('#rows tr:has(td:text-is("mv"))')
        page.wait_for_selector("#mindmap me-root")

        root_topic = page.text_content("#mindmap me-root me-tpc .text")
        assert root_topic == "mv\nanalytics"  # database, not kind (M15)

        branch_topics = page.locator(
            "#mindmap me-main > me-wrapper > me-parent > me-tpc .text"
        ).all_text_contents()
        assert branch_topics == ["Upstream (1)", "Downstream (0)"]
        browser.close()
