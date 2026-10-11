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
from app.config import AnnotationsConfig, AppConfig, ClusterConfig
from app.core.models import Edge, EdgeKind, Entity, EntityKind
from app.store.db import make_session_factory
from app.store.queries import set_label
from app.store.repo import replace_annotations, sync_cluster


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

# Deliberately arbitrary — the frontend doesn't special-case any label key,
# so the fixture shouldn't look tied to one either.
LABEL_KEY = "zzz-test-key"
LABEL_VALUE = "zzz-test-value"
ANNOTATION_DESC = "<b>raw</b> events"  # markup must render as text, not HTML


@pytest.fixture
def live_server(tmp_path):
    """A real HTTP server (browsers can't navigate to TestClient) seeded
    with a chain: table events -> materialized view mv -> table agg."""
    url = f"sqlite:///{tmp_path}/test.sqlite"
    factory = make_session_factory(url)
    with factory() as s:
        sync_cluster(
            s,
            "c1",
            [
                Entity(cluster="c1", database="app", name="events", kind=EntityKind.TABLE, engine="MergeTree"),
                Entity(cluster="c1", database="analytics", name="mv", kind=EntityKind.MAT_VIEW),
                Entity(cluster="c1", database="analytics", name="agg", kind=EntityKind.TABLE),
            ],
            [
                Edge(("c1", "analytics", "mv"), ("c1", "app", "events"), EdgeKind.READS_FROM),
                Edge(("c1", "analytics", "mv"), ("c1", "analytics", "agg"), EdgeKind.WRITES_TO),
            ],
        )
        set_label(s, "c1", "app", "events", LABEL_KEY, LABEL_VALUE)
        replace_annotations(s, [{
            "cluster": "c1", "database": "app", "table_name": "events",
            "doc": {"description": ANNOTATION_DESC, "status": "deprecated"},
            "summary": ANNOTATION_DESC, "status": "deprecated", "path": "app/events.yaml",
        }], sha="x")
    # pull_interval=0: no poller (nothing to pull — rows are seeded above)
    cfg = AppConfig(
        storage_url=url, clusters=[ClusterConfig(name="c1", host="localhost")],
        annotations=AnnotationsConfig(enabled=True, repo="unused", pull_interval=0),
    )

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
        assert set(names) == {"events", "mv", "agg"}
        browser.close()



def test_failed_initial_load_shows_error_and_reload_recovers(live_server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/api/clusters", lambda route: route.fulfill(status=500))
        page.goto(live_server)
        page.wait_for_selector("#status:has-text('failed to load clusters')")
        assert page.locator("#rows tr").count() == 0

        page.unroute("**/api/clusters")
        page.click("#reload")
        page.wait_for_selector("#rows tr")
        assert page.locator("#cluster").input_value() == "c1"
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

        # topic is HTML now (name / database·engine / one line per label,
        # see nodeTopicHtml in app.js) — check the structured divs, not a
        # flattened text_content() (M18: labels on the graph)
        root_name = page.text_content("#mindmap me-root me-tpc .text > div:nth-child(1)")
        root_sub = page.text_content("#mindmap me-root me-tpc .text > div:nth-child(2)")
        assert (root_name, root_sub) == ("mv", "analytics")  # database, not kind (M15)
        assert page.locator("#mindmap me-root .tpc-label").count() == 0  # mv has no labels

        branch_topics = page.locator(
            "#mindmap me-main > me-wrapper > me-parent > me-tpc .text"
        ).all_text_contents()
        assert branch_topics == ["Upstream (1)", "Downstream (1)"]

        # "events" (the upstream leaf) shows the label's value only (key is
        # conveyed by the swatch color / legend, not repeated on the node)
        events_label = page.locator("#mindmap me-children .tpc-label")
        assert events_label.count() == 1  # agg (downstream) has no labels
        assert events_label.text_content().strip() == LABEL_VALUE
        assert events_label.get_attribute("title") == LABEL_KEY

        # legend lists every label key present in the rendered tree
        assert page.text_content("#legend").strip() == LABEL_KEY
        browser.close()


def test_schema_panel_renders_annotation(live_server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(live_server)
        page.wait_for_selector("#rows tr")
        page.click('#rows tr:has(td:text-is("events"))')
        page.click("#mindmap me-root me-tpc")
        page.wait_for_selector("#schema-body .annotation")
        assert page.text_content("#schema-body .ann-desc") == ANNOTATION_DESC
        assert page.text_content("#schema-body .ann-badge") == "deprecated"
        # grain/owner not declared in the fixture's doc -> not rendered at all
        assert page.locator("#schema-body .ann-key").count() == 0
        assert "grain" not in page.text_content("#schema-body")
        browser.close()


def test_label_filter_and_relations_through_hops(live_server):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(live_server)
        page.wait_for_selector("#rows tr")
        names = lambda: sorted(page.locator("#rows tr td:first-child").all_text_contents())  # noqa: E731

        page.click("#label-add")
        page.select_option(".label-row select", LABEL_KEY)
        assert names() == ["events"]  # self only (default)
        page.select_option("#f-label-hops", "1")  # direction defaults to upstream
        assert names() == ["events", "mv"]
        page.select_option("#f-label-hops", "all")
        assert names() == ["agg", "events", "mv"]
        via = page.locator('#rows tr:has(td:text-is("agg")) .chip-via')
        assert via.text_content() == f"{LABEL_KEY}:{LABEL_VALUE}"
        assert via.get_attribute("title") == "via app.events"
        page.select_option("#f-label-dir", "down")  # nothing downstream of agg/mv carries it
        assert names() == ["events"]

        page.click("#filters-clear")
        page.click('#rows tr:has(td:text-is("agg"))')
        page.wait_for_selector("#mindmap me-root")
        branches = "#mindmap me-main > me-wrapper > me-parent > me-tpc .text"
        assert page.locator(branches).all_text_contents() == ["Upstream (1)", "Downstream (0)"]
        page.click('#hops-switch button[data-hops="all"]')
        page.wait_for_function(
            "document.querySelector('#mindmap me-main me-parent me-tpc .text').textContent === 'Upstream (2)'")
        assert page.locator("#mindmap .tpc-dim").all_text_contents() == ["events"]  # indirect
        assert "via mv" in page.locator("#mindmap me-children").first.text_content()
        browser.close()
