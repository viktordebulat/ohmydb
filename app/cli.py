"""CLI: `ohmydb sync [--cluster NAME]`, `ohmydb serve`, `ohmydb mcp`,
`ohmydb annotations pull|validate|schema`."""

import argparse
import json
import os
import sys
from pathlib import Path

from app.config import load_config
from app.core.sync import run_sync

# Config path: --config flag > OHMYDB_CONFIG env > local dev default. In prod
# mount the config (k8s configmap) and point OHMYDB_CONFIG at it.
DEFAULT_CONFIG = os.environ.get("OHMYDB_CONFIG", "config.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ohmydb")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_p = sub.add_parser("sync", help="introspect clusters and refresh stored state")
    sync_p.add_argument("--config", default=DEFAULT_CONFIG)
    sync_p.add_argument("--cluster", default=None, help="sync only this cluster")
    serve_p = sub.add_parser("serve", help="serve HTTP API")
    serve_p.add_argument("--config", default=DEFAULT_CONFIG)
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8080)
    mcp_p = sub.add_parser("mcp", help="run MCP server for AI agents (stdio)")
    mcp_p.add_argument("--config", default=DEFAULT_CONFIG)
    ann_p = sub.add_parser("annotations", help="annotation repo tools (see docs/ANNOTATIONS.md)")
    ann_sub = ann_p.add_subparsers(dest="annotations_command", required=True)
    pull_p = ann_sub.add_parser("pull", help="fetch the annotation repo into the catalog now")
    pull_p.add_argument("--config", default=DEFAULT_CONFIG)
    validate_p = ann_sub.add_parser("validate", help="check an annotation tree (no config needed; for the repo's CI)")
    validate_p.add_argument("dir")
    validate_p.add_argument(
        "--exclude", action="append", default=[], metavar="NAME",
        help="top-level dir that holds per-cluster override roots, not a database (repeatable); "
             "validate each override root with its own run",
    )
    schema_p = ann_sub.add_parser("schema", help="print the JSON Schema of an annotation file (editor support)")
    schema_p.add_argument("kind", nargs="?", default="table", choices=["table", "database", "global"])
    args = parser.parse_args()

    if args.command == "annotations" and args.annotations_command != "pull":
        _annotations_offline(args)  # validate/schema need no config
        return

    cfg = load_config(args.config)
    if args.command == "sync":
        results = run_sync(cfg, only_cluster=args.cluster)
        if not results:
            print(f"no cluster matched {args.cluster!r}", file=sys.stderr)
            sys.exit(1)
        for name, summary in results.items():
            print(f"{name}: {summary}")
        if cfg.annotations.enabled:
            # Schema sync already succeeded — an annotation failure is
            # reported but doesn't fail the command.
            try:
                _pull_annotations(cfg)
            except Exception as e:
                print(f"annotations: pull failed: {e}", file=sys.stderr)
    elif args.command == "serve":
        import uvicorn

        from app.api import create_app

        uvicorn.run(create_app(cfg), host=args.host, port=args.port)
    elif args.command == "mcp":
        from app.mcp import create_mcp

        create_mcp(cfg).run()
    elif args.command == "annotations":  # pull
        if not cfg.annotations.enabled:
            print("annotations.enabled is false in config", file=sys.stderr)
            sys.exit(1)
        try:
            _pull_annotations(cfg)
        except Exception as e:
            print(f"annotations: pull failed: {e}", file=sys.stderr)
            sys.exit(1)


def _pull_annotations(cfg) -> None:
    from app.annotations.service import format_result, sync_annotations
    from app.store.db import make_session_factory

    result = sync_annotations(cfg, make_session_factory(cfg.storage_url))
    print(format_result(result))
    for e in result["errors"]:
        print(f"annotations: {e}", file=sys.stderr)


def _annotations_offline(args) -> None:
    from app.annotations import model

    if args.annotations_command == "schema":
        cls = {"table": model.TableAnnotation, "database": model.DatabaseAnnotation,
               "global": model.GlobalAnnotation}[args.kind]
        print(json.dumps(cls.model_json_schema(), indent=2))
        return
    try:
        tree, errors = model.load_tree(Path(args.dir), frozenset(args.exclude))
    except model.FatalTreeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    for e in errors:
        print(e, file=sys.stderr)
    files = len(tree.tables) + len(tree.databases) + bool(tree.global_)
    print(f"{files} file(s) ok, {len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
