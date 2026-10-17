# Publication review checklist

- [x] Independent source implementation for a fictional scenario.
- [x] Local-only mock service; no external company integration.
- [x] Synthetic generator and synthetic sample dataset.
- [x] Unit/functional tests executed locally.
- [x] English README and documented boundaries.
- [x] Exclude databases, environment secrets and output artifacts from Git.
- [ ] Run dependency/license review on target machine.
- [ ] Run secret scanning on final Git tree **and full new Git history**.
- [ ] Review source and documentation for corporate identifiers and accidental personal information.
- [ ] Confirm GitHub Actions results after pushing.
- [ ] Confirm publication rights and any applicable restrictions.
- [ ] Manually review visibility, repository settings and committed file list.

**Current decision: REQUIRES REVIEW.** Passing tests and a static scan cannot guarantee security, licensing rights or publication authorization. Never upload original corporate archives.
