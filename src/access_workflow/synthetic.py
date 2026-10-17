"""Synthetic-only fixtures; not derived from actual business statistics or records."""

import csv
import random
from pathlib import Path


def generate(destination: str | Path, count: int = 20, seed: int = 42) -> Path:
    if count < 1 or count > 10000:
        raise ValueError("count must be between 1 and 10000")
    rng = random.Random(seed)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    actions = ("ACTIVATE", "SUSPEND", "REACTIVATE")
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["request_id", "account_id", "action", "requester"])
        writer.writeheader()
        for index in range(count):
            writer.writerow({
                "request_id": f"REQ-{index + 1:06d}",
                "account_id": f"DEMO-{index + 1:06d}",
                "action": rng.choice(actions),
                "requester": f"synthetic_user_{rng.randint(1, 5)}",
            })
    return destination
