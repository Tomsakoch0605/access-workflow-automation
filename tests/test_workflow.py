import csv

import pytest

from access_workflow.core import Action, RequestInput, WorkflowError
from access_workflow.store import Store
from access_workflow.synthetic import generate


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "demo.db")


def request(identifier="REQ-001", action=Action.ACTIVATE, account="DEMO-001"):
    return RequestInput(identifier, account, action, "requester")


def test_approval_execution_and_audit(store):
    store.create(request())
    store.review("REQ-001", "reviewer", True)
    assert store.execute("REQ-001")["status"] == "COMPLETED"
    assert store.account("DEMO-001")["enabled"] == 1
    assert [e["event"] for e in store.events()] == ["CREATED", "APPROVED", "COMPLETED"]


def test_separation_of_duties(store):
    store.create(request())
    with pytest.raises(WorkflowError, match="Requester cannot"):
        store.review("REQ-001", "requester", True)


def test_rejected_cannot_execute(store):
    store.create(request())
    store.review("REQ-001", "reviewer", False)
    with pytest.raises(WorkflowError, match="Only approved"):
        store.execute("REQ-001")


def test_idempotency_and_conflicting_reuse(store):
    store.create(request())
    store.create(request())
    assert len(store.events()) == 1
    store.review("REQ-001", "reviewer", True)
    store.execute("REQ-001")
    store.execute("REQ-001")
    assert len(store.events()) == 3
    with pytest.raises(WorkflowError, match="different content"):
        store.create(request(account="DEMO-OTHER"))


def test_retries_bounded(store):
    store.create(request())
    store.review("REQ-001", "reviewer", True)
    assert store.execute("REQ-001", simulate_failure=True)["status"] == "FAILED"
    assert store.execute("REQ-001", simulate_failure=True)["attempts"] == 2
    assert store.execute("REQ-001")["attempts"] == 3
    assert store.account("DEMO-001")["enabled"] == 1


def test_retries_exhausted(store):
    store.create(request())
    store.review("REQ-001", "reviewer", True)
    for _ in range(3):
        store.execute("REQ-001", simulate_failure=True)
    with pytest.raises(WorkflowError, match="Maximum"):
        store.execute("REQ-001")


def test_suspend_and_reactivate(store):
    store.create(request())
    store.review("REQ-001", "reviewer", True)
    store.execute("REQ-001")
    for rid, action, expected in (("REQ-002", Action.SUSPEND, 0), ("REQ-003", Action.REACTIVATE, 1)):
        store.create(request(rid, action))
        store.review(rid, "reviewer", True)
        store.execute(rid)
        assert store.account("DEMO-001")["enabled"] == expected


def test_invalid_identifiers_and_unapproved(store):
    with pytest.raises(WorkflowError):
        store.create(request(account="real-account"))
    store.create(request())
    with pytest.raises(WorkflowError):
        store.execute("REQ-001")


def test_synthetic_reproducibility(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    generate(a, count=10, seed=7)
    generate(b, count=10, seed=7)
    assert a.read_bytes() == b.read_bytes()
    with a.open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 10


def test_no_external_bind(store):
    from access_workflow.api import serve
    with pytest.raises(WorkflowError, match="loopback"):
        serve(store, host="0.0.0.0")
