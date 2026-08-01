"""FastAPI app: graph + entity detail + relations JSON, labels CRUD, sync trigger,
static frontend."""

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
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

    @api.put("/labels/{cluster}/{database}/{table}")
    def put_label(cluster: str, database: str, table: str, body: LabelBody) -> dict:
        with factory() as s:
            set_label(s, cluster, database, table, body.key, body.value)
        return {"ok": True}

    @api.delete("/labels/{cluster}/{database}/{table}/{key}")
    def remove_label(cluster: str, database: str, table: str, key: str) -> dict:
        with factory() as s:
            if not delete_label(s, cluster, database, table, key):
                raise HTTPException(status_code=404, detail="label not found")
        return {"ok": True}

    @api.post("/sync")
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

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/vendor", StaticFiles(directory=WEB_DIR / "vendor"), name="vendor")
    return app
