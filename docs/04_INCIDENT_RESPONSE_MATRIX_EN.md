# 04_INCIDENT_RESPONSE_MATRIX_EN

This document is an **incident response matrix**: alert codes, health verdicts, severity, recommended SLAs, functional roles, and automation hooks.

Replace role names with your org’s titles; here roles are **functional only**.

## 1) Severity Levels

| Severity | Meaning | Target response (recommended) | Notes |
|----------|---------|----------------------------------|-------|
| P0 | Direct threat to service/safety | within 15 minutes | integrity failure, sustained CRITICAL verdict |
| P1 | Degradation or latent risk | within 1 hour | sustained FRAGILE, repeated alerts |
| P2 | Anomaly or possible policy drift | within 4 hours | INFO/WARN class |
| P3 | Informational | next business day | logging/monitoring only |

## 2) Alert Code Matrix (Journal / Integrity)

| Code | Alert Severity | P | SLA (recommended) | Primary | Secondary | Automation (recommended) | Manual (required) |
|------|----------------|---|-------------------|---------|-----------|----------------------------|-------------------|
| `JOURNAL_REPLAY_INTEGRITY_FAIL` | CRITICAL | P0 | 15m | On-call Ops | Security/Platform | block ingestion or safe-mode | backup journal/store, classify root cause, restore trusted segment |
| `JOURNAL_REPLAY_VERIFIED` | OK | P3 | N/A | Ops | — | log only | periodic archival |
| `JOURNAL_REPLAY_NOT_ACTIVE` | INFO | P2 | 4h | Platform | Ops | none (policy decision) | decide whether journal is mandatory in prod |

**Extra guidance by `journal_verify_report.reason`**

| reason | P | Recommended action |
|--------|---|---------------------|
| `hash_chain_mismatch` | P0 | treat as tamper/corruption → stop ingestion + preserve evidence + define recovery boundary |
| `invalid_json` | P1 | partial write/corruption → truncate to last good line + re-verify |
| `invalid_row_schema` | P1 | schema mismatch → check sender/version alignment |
| `journal_read_exception` | P1 | disk/permission/OS → inspect I/O |
| `journal_not_found` | P2 | first boot or wrong path → validate configuration |

## 3) Verdict Matrix

| Verdict | P | SLA (recommended) | Primary | Automation (recommended) | Manual |
|---------|---|-------------------|---------|----------------------------|--------|
| `HEALTHY` | P3 | N/A | Ops | none | periodic reporting |
| `STABLE` | P2 | 4h | Ops | stronger observability logging | trend monitoring |
| `FRAGILE` | P1 | 1h | Ops + SRE | workload reduction, pin `SAFE` policy | request upstream throttling |
| `CRITICAL` | P0 | 15m | On-call Ops | keep protection clamp, restrict inputs | evaluate emergency stop / failover |

## 4) Chain Events (SYD_DRIFT-compatible)

| Event | Condition | P | Recommended action |
|-------|-----------|---|-------------------|
| `HBM_ALERT_CRITICAL` | journal replay `CRITICAL` | P0 | export chain backup + ops escalation |
| normal HBM tick blocks | healthy observation | P3 | routine archival |

## 5) Automation Hooks (Optional)

Forward these JSON fields to webhooks/ticketing:

- `journal_alert.json`: `severity`, `code`, `actionable`, `status`, `reason`
- `journal_verify_report.json`: `status`, `stopped_at_line`, `verified_entries`, `head_hash`

## 6) Related Docs

- `docs/03_OPERATIONS_RUNBOOK_EN.md` — procedural runbook
- `docs/02_FORMULAS_EN.md` — formula reference
