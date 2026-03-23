# 03_OPERATIONS_RUNBOOK_EN

This runbook defines **actionable operations procedures** for HBM_System using security/integrity/performance signals.

## 1) Signal Priority

1. Integrity/Security (`journal replay alert`)
2. System health (`Omega_hbm`, verdict)
3. Performance (`bandwidth_gbps`, `contention_ratio`)

If integrity is `CRITICAL`, it overrides performance optimization.

## 2) Alert Codes and Actions

### `JOURNAL_REPLAY_INTEGRITY_FAIL` (CRITICAL)

- Meaning: nonce journal replay verification failed (`status=stopped|error`)
- Immediate actions:
  - stop ingestion (or switch to safe mode)
  - back up nonce store/journal files
  - capture last valid `head_hash` and `stopped_at_line`
- Follow-up:
  - classify root cause: `hash_chain_mismatch`, `invalid_json`, `invalid_row_schema`, `journal_read_exception`
  - separate security incident vs operational corruption
  - recover from last trusted segment and restart with verification enabled

### `JOURNAL_REPLAY_VERIFIED` (OK)

- Meaning: startup replay verification passed
- Action:
  - continue operations
  - periodically log `verified_entries` and `head_hash`

### `JOURNAL_REPLAY_NOT_ACTIVE` (INFO)

- Meaning: journal is not configured or absent
- Action:
  - decide policy by environment
  - production recommendation: enable journal + verify report + alert output

## 3) Verdict-Driven Actions

### `HEALTHY`
- normal operations

### `STABLE`
- increase observability; no immediate throttle

### `FRAGILE`
- tighten protection policy, reduce workload, increase thermal margin
- optionally force `SAFE` policy mode

### `CRITICAL`
- prioritize protection actions (power clamp, load restriction)
- immediately escalate to upstream orchestrator/ops layer

## 4) Operational Command Template

```bash
python scripts/run_hbm_stream_loop.py \
  --source file \
  --input examples/hbm_stream_input.jsonl \
  --strict-schema \
  --hmac-secret topsecret \
  --clock-t-s 100.0 \
  --hmac-max-age-s 5.0 \
  --enforce-nonce \
  --nonce-store reports/nonce_store.json \
  --nonce-journal reports/nonce_journal.jsonl \
  --journal-verify-report reports/journal_verify_report.json \
  --journal-alert-output reports/journal_alert.json \
  --output reports/HBM_STREAM_AUDIT_CHAIN.json
```

### Checklist

- Is `journal_alert.severity` equal to `CRITICAL`?
- Is `journal_verify_report.status` equal to `ok`?
- Is `Omega_hbm` trending down?
- Are `thermal_gradient_c` and `tsv_failure_risk` approaching critical ranges?

## 5) Recovery Procedure

1. Preserve evidence (`journal_verify_report.json`, `journal_alert.json`, chain export)
2. Pause suspect ingestion path
3. Define trusted replay boundary using last valid `head_hash`
4. Restart with safe flags enabled
5. Resume load gradually only after replay verification returns to `ok`

## 6) Next Operations Upgrades

- Bridge alert codes directly into incident automation
- Add fleet-level runbook for multi-node aggregation
- Document periodic threshold/weight recalibration loop
