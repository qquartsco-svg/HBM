# HBM_System

> Korean: [README.md](README.md)

HBM_System is an independent package/system-level engine for semiconductor stacks, focused on **HBM, TSV, interposer links, channels, and memory controller arbitration**.

## Why this is independent (not inside Fabless)

- `Fabless` focuses on device-level physics and pre-layout design checks (Level A).
- `Memory_Engine` focuses on cell/circuit behavior such as retention, SNM, and row-hammer (Level B).
- `HBM_System` models package/system concerns such as thermal stacking, TSV risk, and controller/channel behavior (Level C).

HBM is an upper-layer system domain that consumes lower-layer health metrics, so it should be a standalone engine.

## MVP modules

```text
hbm_system/
├── contracts.py
├── physics.py
├── controller.py
├── observer.py
└── bridge.py
```

Extended layers:

- `presets.py` - HBM2E/HBM3/HBM3E/edge_low_power presets
- `edge_policy.py` - SAFE/BALANCED/PERF policy
- `protection.py` - thermal/TSV guard power clamp
- `integration.py` - multi-engine snapshot ingestion
- `runtime.py` - policy->observe->protect tick
- `audit_bridge.py` - SYD_DRIFT-compatible audit chain adapter
- `dynamics.py` - temporal multi-tick thermal dynamics simulator
- `memory_adapter.py` - formal Memory_Engine observation adapter

## Key outputs

- `bandwidth_gbps`
- `thermal_gradient_c`
- `tsv_failure_risk`
- `power_density_w_per_stack`
- `Omega_hbm` and verdict (`HEALTHY/STABLE/FRAGILE/CRITICAL`)

## Run tests

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
python -m pytest -q
```

Notes:
- Current test suite baseline: **`32 passed`**.
- On some hosts, TCP socket tests may fail if `socket.bind(...)` is restricted; re-run those tests in an environment that allows local binding.

## High-Load Thermal Stress report

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
python scripts/high_load_thermal_stress_report.py
python scripts/run_hbm_audit_loop.py
python scripts/run_hbm_stream_loop.py
```

Generated file:
- `reports/HIGH_LOAD_THERMAL_STRESS_REPORT.md`
- `reports/HBM_AUDIT_CHAIN.json`
- `reports/HBM_STREAM_AUDIT_CHAIN.json`

Input example:
- `examples/hbm_stream_input.jsonl`

Stream source modes:

```bash
# file (default)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl

# stdin (pipe)
cat examples/hbm_stream_input.jsonl | python scripts/run_hbm_stream_loop.py --source stdin

# tcp (socket)
python scripts/run_hbm_stream_loop.py --source tcp --tcp-host 127.0.0.1 --tcp-port 18081 --max-packets 100

# tcp_server (HBM listens directly)
python scripts/run_hbm_stream_loop.py --source tcp_server --tcp-host 0.0.0.0 --tcp-port 18081 --max-packets 100

# strict schema + auth token
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --strict-schema --auth-token secret

# HMAC signature verify (payload + t_s replay window)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --hmac-secret topsecret --hmac-field hmac_sha256 --clock-t-s 100.0 --hmac-max-age-s 5.0

# nonce anti-replay (drop duplicate nonce)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-field nonce --nonce-cache-size 4096

# nonce persistence + TTL (block replay across restarts)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-store reports/nonce_store.json --nonce-ttl-s 30.0 --clock-t-s 100.0

# append-only nonce journal + compact
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-store reports/nonce_store.json --nonce-journal reports/nonce_journal.jsonl --nonce-journal-compact

# export nonce journal replay verification report
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-journal reports/nonce_journal.jsonl --journal-verify-report reports/journal_verify_report.json

# export operational alert event derived from replay result
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-journal reports/nonce_journal.jsonl --journal-alert-output reports/journal_alert.json
```

Note:
- nonce journal records are hash-linked (`prev_hash`, `hash`) for integrity chaining.
- each record includes `payload_digest` so processed packet identity remains traceable.
- with `--journal-verify-report`, startup replay verification is exported as JSON (`status`, `verified_entries`, `stopped_at_line`, `reason`).
- with `--journal-alert-output`, the replay result is mapped to an operational alert event (`severity`, `code`, `actionable`) and exported as JSON.
- `status=stopped|error` maps to `CRITICAL/JOURNAL_REPLAY_INTEGRITY_FAIL` for immediate operations response.
- when `status=stopped|error`, the alert is also appended to the SYD_DRIFT chain as an `HBM_ALERT_CRITICAL` block.

## Design docs

- `docs/00_CONCEPT_EN.md`
- `docs/01_LAYER_STACK_EN.md`
- `docs/02_FORMULAS_EN.md`
- `docs/03_OPERATIONS_RUNBOOK_EN.md`
- `docs/04_INCIDENT_RESPONSE_MATRIX_EN.md`

## Organic engine integration points

- `integration.merge_engine_snapshots()` - compose Fabless/Memory/Battery/VectorSpace/Runtime states
- `integration.build_input_from_engine_snapshots()` - convert multi-engine state into `HBMInput`
- `integration.build_input_from_typed_states()` - convert typed DTO states into `HBMInput`
- `audit_bridge.append_observation_to_chain()` - export HBM runtime results to external audit chains

## Concept Primer

HBM_System is not a full PHY/sign-off simulator.  
It is a **package/system-level health and operations-risk observer** for HBM stacks.

- Level A (`Fabless`): device physics viability
- Level B (`Memory_Engine`): cell/circuit stability
- Level C (`HBM_System`): thermal stacking, TSV risk, channel/controller behavior, and ops integrity

The core role is to fuse lower-layer signals and runtime pressure into `Omega_hbm` and clear operational verdicts.

## Formula Snapshot

Detailed equations are in `docs/02_FORMULAS_EN.md`. Operational summary:

1. `bandwidth_gbps ~= f(stack_count, channels_per_stack, io_rate, contention_ratio, controller_efficiency)`
2. `power_density_w_per_stack = total_power_w / stack_count`
3. `thermal_gradient_c ~= g(power_density, cooling_coeff, ambient_temp_c)`
4. `tsv_failure_risk ~= h(tsv_density, thermal_gradient_c)`
5. `Omega_hbm = weighted(thermal, tsv, contention, lower_layer_health, runtime_pressure)`
6. Security integrity ops signal:
   - replay verification `status/reason`
   - derived alert `severity/code/actionable`
   - `stopped|error -> CRITICAL/JOURNAL_REPLAY_INTEGRITY_FAIL`

## 4-Level Assessment (Positive/Neutral/Conservative/Negative)

### Positive

- Clean A/B/C layering prevents role collision across semiconductor abstraction levels.
- Stable runtime flow (`policy -> observe -> protect -> re-observe`) with deterministic contracts.
- Multi-source stream ingestion with hardened anti-replay path (HMAC + nonce + journal).
- Tamper detection escalates to `CRITICAL` and is appended to SYD_DRIFT-compatible chain events.

### Neutral

- Current scope is a system-health estimator, not a full physical sign-off simulator.
- Controller logic is arbitration-centric MVP; advanced QoS and refresh-interference models remain future work.
- `Omega_hbm` is highly practical for operations, but not a direct replacement for formal certification frameworks.

### Conservative

- External observability schema standardization (dashboards/incident systems) should be formalized next.
- Lower-layer signal quality handling (delay/missing/scale mismatch) needs stronger normalization policies.
- Continuous field calibration loop should tune thresholds/weights from real-world traces.

### Negative (Current hard limits)

- Not suitable as a tape-out sign-off tool by itself.
- Detailed SI/PI, EM lifetime, and full thermal FEM are outside the current model scope.
- Long-horizon process-variation and supply-chain drift statistics are still shallow.

## Extensibility, Usefulness, and Limits

- Works as a common contract layer between design-facing engines and runtime operations.
- Converts fragmented multi-engine state into one operational decision surface (`Omega_hbm` + verdict + alerts).
- Enables dual-track auditing: performance/health and integrity/security in one chain timeline.

Current limitations:
- Approximation-first model (for runtime decision support) over high-fidelity physical simulation.
- External NOC/incident workflow integration remains partial.
- Fleet-level (multi-node) HBM orchestration is still early.

## Expansion Roadmap

1. Controller expansion: QoS classes, refresh-interference, burst-aware scheduling  
2. Calibration loop: data-driven threshold and weight adaptation  
3. Fleet mode: cluster-level `Omega_hbm` aggregation and rollout guardrails  
4. Audit integration: direct bridge to incident automation pipelines  
5. Documentation growth: synchronized KR/EN concept, formulas, and operations runbooks

## Blockchain Signature and Integrity

- Canonical manifest: `SIGNATURE.sha256`
- Integrity guide: `BLOCKCHAIN_INFO.md`
- Release chain log: `PHAM_BLOCKCHAIN_LOG.md`

Verification:

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
shasum -a 256 -c SIGNATURE.sha256
python -m pytest -q
```
