"""FastAPI app: graph + entity detail + relations JSON, labels CRUD, sync trigger,
static frontend."""

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import AppConfig
from app.core.sync import run_sync
from app.mcp import create_mcp
from app.store.db import make_session_factory
from app.store.queries import (
    delete_label,
    get_entity,
    get_relations,
    graph_payload,
    set_label,
)

WEB_DIR = Path(__file__).parent / "web"


class RevalidatedStaticFiles(StaticFiles):
    """StaticFiles sends Last-Modified/ETag but no Cache-Control, so browsers
    cache heuristically (~10% of the file's age) — a stale index.html paired
    with a newer app.js (or vice versa) after a deploy breaks the page until a
    reload. no-cache = always revalidate; unchanged files are a cheap 304."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


class LabelBody(BaseModel):
    key: str
    value: str = ""


def create_app(cfg: AppConfig) -> FastAPI:
    factory = make_session_factory(cfg.storage_url)
    # MCP served over HTTP at /mcp; its lifespan must be handed to the parent
    # app or the streamable-http session manager never starts.
    mcp_app = create_mcp(cfg).http_app(path="/")
    app = FastAPI(title="ohmydb", lifespan=mcp_app.lifespan)
    app.mount("/mcp", mcp_app)

    api = APIRouter(prefix="/api")

    def require_token(authorization: str | None = Header(default=None)) -> None:
        """Guards mutating routes only (POST /sync, PUT/DELETE /labels) — a
        dependency, not global middleware, so reads stay open even when a
        token is configured. No-op (auth off) when cfg.auth_token is unset,
        which is the default — this is opt-in for deployments exposed past
        localhost, not a requirement for local dev."""
        if cfg.auth_token is None:
            return
        if authorization != f"Bearer {cfg.auth_token}":
            raise HTTPException(status_code=401, detail="missing or invalid bearer token")

    @api.get("/clusters")
    def clusters() -> list[str]:
        return [c.name for c in cfg.clusters]

    @api.get("/graph/{cluster}")
    def graph(cluster: str, q: str | None = None) -> dict:
        with factory() as s:
            return graph_payload(s, cluster, q)

    @api.get("/entities/{cluster}/{database}/{name}")
    def entity(cluster: str, database: str, name: str) -> dict:
        with factory() as s:
            payload = get_entity(s, cluster, database, name)
        if payload is None:
            raise HTTPException(status_code=404, detail="entity not found")
        return payload

    @api.get("/entities/{cluster}/{database}/{name}/relations")
    def relations(cluster: str, database: str, name: str, direct: bool = False) -> dict:
        with factory() as s:
            payload = get_relations(s, cluster, database, name, direct_only=direct)
        if payload is None:
            raise HTTPException(status_code=404, detail="entity not found")
        return payload

    @api.put("/labels/{cluster}/{database}/{table}", dependencies=[Depends(require_token)])
    def put_label(cluster: str, database: str, table: str, body: LabelBody) -> dict:
        with factory() as s:
            set_label(s, cluster, database, table, body.key, body.value)
        return {"ok": True}

    @api.delete("/labels/{cluster}/{database}/{table}/{key}", dependencies=[Depends(require_token)])
    def remove_label(cluster: str, database: str, table: str, key: str) -> dict:
        with factory() as s:
            if not delete_label(s, cluster, database, table, key):
                raise HTTPException(status_code=404, detail="label not found")
        return {"ok": True}

    @api.post("/sync", dependencies=[Depends(require_token)])
    def sync(cluster: str | None = None) -> dict:
        try:
            results = run_sync(cfg, only_cluster=cluster)
        except Exception as e:  # introspection failed (cluster down, auth, ...)
            raise HTTPException(status_code=502, detail=str(e))
        if not results:
            raise HTTPException(
                status_code=404, detail=f"no cluster matched {cluster!r}"
            )
        return results

    app.include_router(api)

    # Single mount covers index.html at "/" (html=True), app.css/app.js, and
    # vendor/* (StaticFiles serves nested dirs) — no separate index route needed.
    app.mount("/", RevalidatedStaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
