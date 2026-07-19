"""CLI: `ohmydb sync [--cluster NAME]` and `ohmydb serve`."""

import argparse
import sys

from app.config import load_config
from app.core.sync import run_sync


def main() -> None:
    parser = argparse.ArgumentParser(prog="ohmydb")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_p = sub.add_parser("sync", help="introspect clusters and refresh stored state")
    sync_p.add_argument("--config", default="config.yaml")
    sync_p.add_argument("--cluster", default=None, help="sync only this cluster")
    serve_p = sub.add_parser("serve", help="serve HTTP API")
    serve_p.add_argument("--config", default="config.yaml")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8080)
    mcp_p = sub.add_parser("mcp", help="run MCP server for AI agents (stdio)")
    mcp_p.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.command == "sync":
        results = run_sync(cfg, only_cluster=args.cluster)
        if not results:
            print(f"no cluster matched {args.cluster!r}", file=sys.stderr)
            sys.exit(1)
        for name, summary in results.items():
            print(f"{name}: {summary}")
    elif args.command == "serve":
        import uvicorn

        from app.api import create_app

        uvicorn.run(create_app(cfg), host=args.host, port=args.port)
    elif args.command == "mcp":
        from app.mcp import create_mcp

        create_mcp(cfg).run()


if __name__ == "__main__":
    main()
