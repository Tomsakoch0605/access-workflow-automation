"""Domain validation and transitions for a local, fictional account service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowError(ValueError):
    """A rejected workflow command (safe, non-sensitive message)."""


class Status(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Action(str, Enum):
    ACTIVATE = "ACTIVATE"
    SUSPEND = "SUSPEND"
    REACTIVATE = "REACTIVATE"


@dataclass(frozen=True)
class RequestInput:
    request_id: str
    account_id: str
    action: Action
    requester: str


def validate_identifier(value: str, prefix: str) -> str:
    """Accept only fictional identifiers; prevent arbitrary external account references."""
    if not isinstance(value, str) or not value.startswith(prefix):
        raise WorkflowError(f"Identifier must begin with {prefix}")
    suffix = value[len(prefix) :]
    if not (1 <= len(suffix) <= 24 and suffix.isascii() and suffix.isalnum()):
        raise WorkflowError("Identifier suffix must be 1-24 ASCII letters or digits")
    return value


def validate_actor(actor: str) -> str:
    if not isinstance(actor, str) or not 3 <= len(actor) <= 32:
        raise WorkflowError("Actor must have 3-32 characters")
    if not actor.isascii() or not all(c.isalnum() or c in "_-" for c in actor):
        raise WorkflowError("Actor may contain only ASCII letters, numbers, '_' and '-'")
    return actor


def validate_request(value: RequestInput) -> RequestInput:
    validate_identifier(value.request_id, "REQ-")
    validate_identifier(value.account_id, "DEMO-")
    validate_actor(value.requester)
    if not isinstance(value.action, Action):
        raise WorkflowError("Unsupported action")
    return value
