# Portfolio positioning

**GitHub description (under 160 characters):** Auditable Python access workflow demo with synthetic requests, SQLite transactions, local API, approval controls, retries, and CI.

**Topics:** `python`, `workflow-automation`, `sqlite`, `rest-api`, `pytest`, `github-actions`, `backend-development`, `synthetic-data`

**Resume bullets (demonstration only; no unverifiable business outcomes):**

- Designed an independent Python workflow demonstration for fictional account requests, approval transitions and simulated execution.
- Implemented transactional SQLite persistence, idempotent request processing and structured audit events in a reproducible local environment.
- Added automated Python tests and CI validation across multiple interpreter versions using GitHub Actions.

## 60-second interview pitch

"During my professional experience, I developed skills in process automation, API integration and operational reliability. To demonstrate those skills without sharing internal code or data, I independently built Access Workflow Automation. It runs entirely locally and manages fictitious account requests through validation, separate review and simulated execution. SQLite transactions keep state changes and audit records together; request identifiers provide idempotency; and tests exercise failure handling and state transitions. The API has no real authorization or production connection by design. The repository demonstrates my engineering approach, not the original internal implementation or its business metrics."

## Likely interview questions

- Why is SQLite sufficient for this example? What changes would you make with multiple workers?
- How does a transaction prevent partially applied execution?
- Why is a requester/reviewer string comparison insufficient for production security?
- What does idempotency mean at the request and execution levels?
- How do bounded retries affect failed requests?
- How did you ensure the dataset was independently generated?
