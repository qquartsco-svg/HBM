# Changelog

## 1.10.0
- Added operations runbook docs (`03_OPERATIONS_RUNBOOK.md`, `03_OPERATIONS_RUNBOOK_EN.md`).
- Defined alert-code-based response playbooks for replay integrity and health verdict escalation.
- Linked runbook docs from KR/EN README for faster newcomer onboarding.

## 1.9.1
- Hardened report/audit scripts to auto-create output parent directories before writing files.
- Improved clean-clone operability where `reports/` does not pre-exist.

## 1.9.0
- Added blockchain-style integrity artifacts (`SIGNATURE.sha256`, `BLOCKCHAIN_INFO.md`, `PHAM_BLOCKCHAIN_LOG.md`).
- Expanded README/README_EN for concept onboarding, formula summary, 4-level assessment, limits, and roadmap.
- Documented integrity verification workflow using signature + test suite.

## 1.8.0
- Added audit bridge function to append journal replay alert events into SYD_DRIFT-compatible chains.
- Updated stream runner to append `HBM_ALERT_CRITICAL` chain block when replay verification is `stopped|error`.
- Added tests for journal alert chain append behavior and updated tamper replay block-count expectations.

## 1.7.0
- Added operational alert mapping for startup nonce-journal replay verification.
- Added `--journal-alert-output` to export replay-derived alert event JSON.
- Added runtime alert line output (`Journal replay alert: <severity> <code> ...`) for immediate visibility.
- Added tests for CRITICAL alert on tamper and OK alert on clean replay.

## 1.6.0
- Added `--journal-verify-report` option to export startup nonce-journal replay verification as JSON.
- Added structured verification status fields (`status`, `verified_entries`, `stopped_at_line`, `reason`, `head_hash`).
- Added tests for normal verification report and tamper-stop verification report paths.

## 1.5.0
- Added `payload_digest` to nonce journal records (SHA-256 over canonical packet JSON).
- Updated journal hash-link formula to include payload digest.
- Added replay validation for payload digest integrity in journal chain.
- Added tests for payload-digest field and tamper-stop behavior.

## 1.4.0
- Added hash-linked nonce journal records (`prev_hash`, `hash`) for tamper-evident durability.
- Added chain-verified journal replay that stops on first invalid/tampered record.
- Added tests for journal hash-link fields and tamper replay behavior.

## 1.3.0
- Added append-only nonce journal (`--nonce-journal`) for durable replay evidence.
- Added layered nonce bootstrap (snapshot store + journal replay).
- Added journal compaction switch (`--nonce-journal-compact`) after snapshot save.
- Added tests for journal append behavior and compaction truncation.

## 1.2.0
- Added nonce TTL enforcement (`--nonce-ttl-s`) for bounded replay memory.
- Added persistent nonce store (`--nonce-store`) to survive process restarts.
- Added tests for restart-time replay blocking and TTL-based nonce reuse.

## 1.1.0
- Added nonce-based anti-replay cache (`--enforce-nonce`, `--nonce-field`, `--nonce-cache-size`).
- Added duplicate nonce rejection during ingestion.
- Added HMAC coupling rule requiring nonce presence when HMAC verification is enabled.
- Added tests for duplicate nonce drop and HMAC-without-nonce rejection.

## 1.0.0
- Added HMAC-SHA256 packet signature verification (`--hmac-secret`, `--hmac-field`) over canonical JSON payload.
- Added replay-window validation based on `t_s` (`--clock-t-s`, `--hmac-max-age-s`).
- Added tests for valid/invalid HMAC and replay-window expiration behavior.

## 0.9.0
- Added optional shared-token authentication (`--auth-token`) for stream packet acceptance.
- Added strict packet schema/type validation mode (`--strict-schema`) with invalid-packet drop behavior.
- Added ingestion accepted/dropped counters in runtime output.
- Added tests for strict-schema and auth-token filtering.

## 0.8.0
- Added `tcp_server` source mode so HBM runner can listen as a push endpoint.
- Added server idle-timeout control and packet cap for bounded operational runs.
- Added tcp_server end-to-end test (runner server + client packet push).

## 0.7.0
- Expanded stream runner to multi-source realtime ingestion (`file`, `stdin`, `tcp`) with CLI controls.
- Added TCP socket ingestion test using a local in-test stream server.
- Updated docs with explicit commands for file/pipe/socket operational modes.

## 0.6.0
- Added stream ingestion runner (`run_hbm_stream_loop.py`) for JSONL-based external engine state packets.
- Added sample stream input file (`examples/hbm_stream_input.jsonl`).
- Added stream chain output (`HBM_STREAM_AUDIT_CHAIN.json`) integrated with SYD_DRIFT CommandChain.
- Added test for stream runner output generation.

## 0.5.0
- Added mode-dependent controller latency dynamics in temporal simulation.
- Added dedicated `memory_adapter.py` for formal Memory_Engine observation normalization.
- Added continuous HBM audit loop script (`run_hbm_audit_loop.py`) integrated with SYD_DRIFT command chain export.
- Added tests for memory adapter normalization, latency trajectory state, and audit loop output generation.

## 0.4.0
- Added typed inter-engine state DTOs (`FablessState`, `MemoryState`, `BatteryState`, `VectorState`, `RuntimeState`).
- Added typed builder path (`build_input_from_typed_states`) to reduce ad-hoc mapping and hardcoded field handling.
- Added temporal dynamics layer with first-order thermal state simulation (`simulate_hbm_trajectory`).
- Added SYD_DRIFT roundtrip bridge test for real command-chain integrity flow.

## 0.3.0
- Replaced hard-coded observer/protection constants with configurable dynamics parameters in `HBMConfig`.
- Added hysteresis protection state machine (`trip/recover`) to avoid clamp chattering.
- Added typed integration helpers for Fabless/Memory observations and multi-engine snapshot merging.
- Added external audit bridge adapter for SYD_DRIFT-compatible command chains.
- Expanded tests for hysteresis behavior, configurable weighting, and adapter paths.

## 0.2.0
- Added edge policy layer (`SAFE/BALANCED/PERF`) for edge AI workload control.
- Added protection layer with thermal/TSV guard and power clamp.
- Added runtime tick pipeline (`policy -> observe -> protect -> re-observe`).
- Added preset layer (`HBM2E`, `HBM3`, `HBM3E`, `edge_low_power`).
- Added multi-engine integration layer for Fabless/Memory/Battery/VectorSpace snapshots.
- Added design docs for concept, layer stack, and core formulas (KR/EN).

## 0.1.0
- Initial HBM system MVP.
- Added package-level contracts for stack/channel/controller health modeling.
- Added thermal gradient, TSV risk, bandwidth, and power density estimators.
- Added arbitration and integrated observer with `Omega_hbm` verdict.
- Added bridge helper to ingest lower-layer Fabless/Memory metrics.
