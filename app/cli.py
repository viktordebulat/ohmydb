"""CLI: `ohmydb sync [--cluster NAME] [--config PATH]`."""

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
    args = parser.parse_args()

    cfg = load_config(args.config)
    results = run_sync(cfg, only_cluster=args.cluster)
    if not results:
        print(f"no cluster matched {args.cluster!r}", file=sys.stderr)
        sys.exit(1)
    for name, summary in results.items():
        print(f"{name}: {summary}")


if __name__ == "__main__":
    main()
