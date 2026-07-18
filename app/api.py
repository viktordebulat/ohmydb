"""FastAPI app: graph + entity detail JSON, static visualization page."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.config import AppConfig
from app.store.db import EdgeRow, EntityRow, make_session_factory

WEB_DIR = Path(__file__).parent / "web"


def create_app(cfg: AppConfig) -> FastAPI:
    factory = make_session_factory(cfg.storage_url)
    app = FastAPI(title="oh-my-db")

    @app.get("/graph")
    def graph() -> dict:
        with factory() as s:
            entities = s.scalars(select(EntityRow)).all()
            edges = s.scalars(select(EdgeRow)).all()
        return {
            "nodes": [
                {
                    "id": e.id,
                    "cluster": e.cluster,
                    "database": e.database,
                    "name": e.name,
                    "kind": e.kind,
                    "engine": e.engine,
                    "refreshable": bool((e.attrs or {}).get("refreshable")),
                    "synced_at": e.synced_at.isoformat() if e.synced_at else None,
                }
                for e in entities
            ],
            "edges": [{"src": e.src_id, "dst": e.dst_id, "kind": e.kind} for e in edges],
        }

    @app.get("/entities/{cluster}/{database}/{name}")
    def entity(cluster: str, database: str, name: str) -> dict:
        with factory() as s:
            row = s.scalar(
                select(EntityRow).where(
                    EntityRow.cluster == cluster,
                    EntityRow.database == database,
                    EntityRow.name == name,
                )
            )
        if row is None:
            raise HTTPException(status_code=404, detail="entity not found")
        return {
            "cluster": row.cluster,
            "database": row.database,
            "name": row.name,
            "kind": row.kind,
            "engine": row.engine,
            "ddl": row.ddl,
            "columns": row.columns,
            "attrs": row.attrs,
            "synced_at": row.synced_at.isoformat() if row.synced_at else None,
        }

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/vendor", StaticFiles(directory=WEB_DIR / "vendor"), name="vendor")
    return app
