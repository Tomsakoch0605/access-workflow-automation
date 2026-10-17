"""Exercise the actual loopback HTTP interface without external services."""

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from access_workflow.api import build_handler
from access_workflow.store import Store


def test_http_end_to_end(tmp_path):
    service = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(Store(tmp_path / "api.db")))
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{service.server_port}"

    def call(route, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(base + route, data=data, headers={"Content-Type": "application/json"} if data else {})
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    try:
        assert call("/health")["status"] == "ok"
        assert call("/requests", {
            "request_id": "REQ-WEB1", "account_id": "DEMO-WEB1",
            "action": "ACTIVATE", "requester": "requester1"
        })["status"] == "PENDING"
        assert call("/requests/REQ-WEB1/approve", {"actor": "reviewer1"})["status"] == "APPROVED"
        assert call("/requests/REQ-WEB1/execute", {"actor": "worker1"})["status"] == "COMPLETED"
        assert call("/accounts/DEMO-WEB1")["account"]["enabled"] == 1
        assert len(call("/audit")["events"]) == 3
    finally:
        service.shutdown()
        service.server_close()
        thread.join(timeout=3)
