"""CLI for reproducible fixture creation, demo workflow and local server."""

import argparse
import csv
import json
import os
from pathlib import Path

from .api import serve
from .core import Action, RequestInput
from .store import Store
from .synthetic import generate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fictional access workflow; never use real accounts")
    parser.add_argument("--db", default=os.getenv("ACCESS_DB_PATH", "output/demo.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Create deterministic synthetic requests")
    gen.add_argument("--output", default="data/synthetic_requests.csv")
    gen.add_argument("--count", type=int, default=20)
    gen.add_argument("--seed", type=int, default=42)
    run = sub.add_parser("demo", help="Run fictional account activation workflow")
    run.add_argument("--request-id", default="REQ-EXAMPLE")
    server = sub.add_parser("serve", help="Start local-only demo HTTP API")
    server.add_argument("--port", type=int, default=int(os.getenv("ACCESS_API_PORT", "8765")))
    report = sub.add_parser("audit", help="Export audit history")
    report.add_argument("--output", default="output/audit.csv")
    args = parser.parse_args(argv)
    if args.command == "generate":
        print(generate(args.output, args.count, args.seed))
        return 0
    store = Store(args.db)
    if args.command == "serve":
        print(f"Local fictional API on http://127.0.0.1:{args.port}")
        serve(store, port=args.port)
    elif args.command == "demo":
        request = store.create(RequestInput(args.request_id, "DEMO-EXAMPLE", Action.ACTIVATE, "demo-requester"))
        if request["status"] == "PENDING":
            request = store.review(args.request_id, "demo-reviewer", True)
        if request["status"] in ("APPROVED", "FAILED"):
            request = store.execute(args.request_id)
        print(json.dumps(request, indent=2))
    elif args.command == "audit":
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        events = store.events()
        with dest.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["sequence", "request_id", "event", "actor", "recorded_at"])
            writer.writeheader()
            writer.writerows(events)
        print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
