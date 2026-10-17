"""SQLite persistence and append-only (at application level) audit events."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .core import Action, RequestInput, Status, WorkflowError, validate_actor, validate_request


class Store:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    reviewer TEXT,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                """
            )

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        with sqlite3.connect(self.path, timeout=10) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout = 10000")
            yield db

    def create(self, item: RequestInput) -> dict:
        validate_request(item)
        with self._db() as db:
            existing = db.execute("SELECT * FROM requests WHERE request_id=?", (item.request_id,)).fetchone()
            if existing:
                if (existing["account_id"], existing["action"], existing["requester"]) != (
                    item.account_id, item.action.value, item.requester
                ):
                    raise WorkflowError("Request ID already used with different content")
                return dict(existing)
            db.execute(
                "INSERT INTO requests (request_id, account_id, action, requester, status) VALUES (?, ?, ?, ?, ?)",
                (item.request_id, item.account_id, item.action.value, item.requester, Status.PENDING.value),
            )
            self._audit(db, item.request_id, "CREATED", item.requester)
        return self.get(item.request_id)

    def get(self, request_id: str) -> dict:
        with self._db() as db:
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            raise WorkflowError("Request not found")
        return dict(row)

    @staticmethod
    def _audit(db: sqlite3.Connection, request_id: str, event: str, actor: str) -> None:
        db.execute("INSERT INTO audit (request_id,event,actor) VALUES (?,?,?)", (request_id, event, actor))

    def review(self, request_id: str, actor: str, approve: bool) -> dict:
        validate_actor(actor)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                raise WorkflowError("Request not found")
            target = Status.APPROVED if approve else Status.REJECTED
            if row["status"] == target.value and row["reviewer"] == actor:
                return dict(row)
            if row["status"] != Status.PENDING.value:
                raise WorkflowError("Only pending requests can be reviewed")
            if actor == row["requester"]:
                raise WorkflowError("Requester cannot approve or reject their own request")
            db.execute(
                "UPDATE requests SET reviewer=?,status=? WHERE request_id=?",
                (actor, target.value, request_id),
            )
            self._audit(db, request_id, target.value, actor)
        return self.get(request_id)

    def execute(self, request_id: str, actor: str = "demo-worker", simulate_failure: bool = False) -> dict:
        """Apply to mock local accounts only, atomically with the request status."""
        validate_actor(actor)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                raise WorkflowError("Request not found")
            if row["status"] == Status.COMPLETED.value:
                return dict(row)
            if row["status"] not in (Status.APPROVED.value, Status.FAILED.value):
                raise WorkflowError("Only approved or failed requests can execute")
            attempts = row["attempts"] + 1
            if attempts > 3:
                raise WorkflowError("Maximum three execution attempts")
            if simulate_failure:
                db.execute(
                    "UPDATE requests SET status=?,error_code=?,attempts=? WHERE request_id=?",
                    (Status.FAILED.value, "SIMULATED_FAILURE", attempts, request_id),
                )
                self._audit(db, request_id, "FAILED_SIMULATED", actor)
            else:
                action = Action(row["action"])
                old = db.execute("SELECT enabled FROM accounts WHERE account_id=?", (row["account_id"],)).fetchone()
                if action == Action.ACTIVATE and old is not None:
                    raise WorkflowError("Account already exists")
                if action != Action.ACTIVATE and old is None:
                    raise WorkflowError("Account does not exist")
                if action == Action.SUSPEND and old["enabled"] == 0:
                    raise WorkflowError("Account already suspended")
                if action == Action.REACTIVATE and old["enabled"] == 1:
                    raise WorkflowError("Account already active")
                if action == Action.ACTIVATE:
                    db.execute("INSERT INTO accounts VALUES (?,1)", (row["account_id"],))
                else:
                    db.execute(
                        "UPDATE accounts SET enabled=? WHERE account_id=?",
                        (int(action == Action.REACTIVATE), row["account_id"]),
                    )
                db.execute(
                    "UPDATE requests SET status=?,error_code=NULL,attempts=? WHERE request_id=?",
                    (Status.COMPLETED.value, attempts, request_id),
                )
                self._audit(db, request_id, "COMPLETED", actor)
        return self.get(request_id)

    def events(self, request_id: str | None = None) -> list[dict]:
        with self._db() as db:
            if request_id:
                rows = db.execute("SELECT * FROM audit WHERE request_id=? ORDER BY sequence", (request_id,))
            else:
                rows = db.execute("SELECT * FROM audit ORDER BY sequence")
            return [dict(row) for row in rows]

    def account(self, account_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM accounts WHERE account_id=?", (account_id,)).fetchone()
            return dict(row) if row else None
