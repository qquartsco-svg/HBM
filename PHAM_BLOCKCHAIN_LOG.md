# PHAM_BLOCKCHAIN_LOG

## Scope

`HBM_System` standalone package release log.

---

## Version 1.11.1

- Package version: `1.11.1`
- Documentation audit: README test count + external portfolio notes aligned with current release.

## Version 1.11.0

- Package version: `1.11.0`
- Added incident response matrix (KR/EN) for alert/verdict escalation and SLAs.

### New in v1.11.0

- Added:
  - `docs/04_INCIDENT_RESPONSE_MATRIX.md`
  - `docs/04_INCIDENT_RESPONSE_MATRIX_EN.md`

## Version 1.10.0

- Package version: `1.10.0`
- Added dedicated operations runbook in KR/EN for incident-ready operations.

### New in v1.10.0

- Added:
  - `docs/03_OPERATIONS_RUNBOOK.md`
  - `docs/03_OPERATIONS_RUNBOOK_EN.md`
- Documented:
  - alert-code response policy
  - verdict-driven escalation
  - security replay recovery flow

## Version 1.9.1

- Package version: `1.9.1`
- Stability hardening: scripts now auto-create output parent directories.

### New in v1.9.1

- Prevented fresh-clone `FileNotFoundError` by ensuring `reports/` path creation before writes in:
  - `high_load_thermal_stress_report.py`
  - `run_hbm_audit_loop.py`
  - `run_hbm_stream_loop.py`

## Version 1.9.0

- Package version: `1.9.0`
- Signature authority: `SIGNATURE.sha256`
- Integrity docs: `BLOCKCHAIN_INFO.md`, `PHAM_BLOCKCHAIN_LOG.md`

### New in v1.9.0

- Added blockchain-style integrity artifacts for HBM_System release validation.
- Expanded README/README_EN with:
  - concept primer for unfamiliar users
  - formula snapshot
  - 4-level assessment (Positive/Neutral/Conservative/Negative)
  - extensibility/usefulness/limits and expansion roadmap
- Preserved ops security chain:
  - journal replay verification
  - replay-derived alert mapping
  - CRITICAL replay-failure chain append path

### Verification

- `python -m pytest -q` passed
- `shasum -a 256 -c SIGNATURE.sha256` used as release integrity check

## Version 1.8.0

- Added `append_journal_alert_to_chain()` and CRITICAL replay-alert chain append integration.
- Added tests and docs for alert-to-chain linkage.
