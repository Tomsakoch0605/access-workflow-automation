"""Local-only JSON HTTP API. No real identity integration or authentication."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .core import Action, RequestInput, WorkflowError
from .store import Store


def build_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: object):
            data = json.dumps(body, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict:
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise WorkflowError("Content-Type must be application/json")
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 4096:
                raise WorkflowError("JSON body must be 1-4096 bytes")
            value = json.loads(self.rfile.read(size))
            if not isinstance(value, dict):
                raise WorkflowError("Expected a JSON object")
            return value

        def _dispatch(self, operation: str):
            path = urlsplit(self.path).path
            parts = [p for p in path.split("/") if p]
            try:
                if operation == "GET" and parts == ["health"]:
                    return self._send(200, {"status": "ok", "mode": "demo-local-only"})
                if operation == "GET" and parts == ["audit"]:
                    return self._send(200, {"events": store.events()})
                if operation == "GET" and len(parts) == 2 and parts[0] == "requests":
                    return self._send(200, store.get(parts[1]))
                if operation == "GET" and len(parts) == 2 and parts[0] == "accounts":
                    return self._send(200, {"account": store.account(parts[1])})
                if operation == "POST" and parts == ["requests"]:
                    body = self._body()
                    request = RequestInput(body["request_id"], body["account_id"], Action(body["action"]), body["requester"])
                    return self._send(201, store.create(request))
                if operation == "POST" and len(parts) == 3 and parts[0] == "requests":
                    body = self._body()
                    if parts[2] in ("approve", "reject"):
                        return self._send(200, store.review(parts[1], body["actor"], parts[2] == "approve"))
                    if parts[2] == "execute":
                        return self._send(200, store.execute(parts[1], body.get("actor", "demo-worker"), body.get("simulate_failure") is True))
                return self._send(404, {"error": "Route not found"})
            except (WorkflowError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
                return self._send(400, {"error": str(error) if isinstance(error, WorkflowError) else "Invalid request"})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def log_message(self, format, *args):
            # Avoid request payloads, paths and identifiers in HTTP logs.
            pass

    return Handler


def serve(store: Store, host: str = "127.0.0.1", port: int = 8765):
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise WorkflowError("Only loopback binding is allowed")
    server = ThreadingHTTPServer((host, port), build_handler(store))
    try:
        server.serve_forever()
    finally:
        server.server_close()
