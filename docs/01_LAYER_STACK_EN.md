# HBM_System Layer Stack

> Korean: [01_LAYER_STACK.md](01_LAYER_STACK.md)

## Layer 0 — Contracts

- `HBMConfig`
- `HBMInput`
- `HBMObservation`
- `EdgePolicyDecision`

## Layer 1 — Physics

- bandwidth estimation
- thermal gradient estimation
- TSV failure risk estimation
- power density estimation

## Layer 2 — Controller

- channel arbitration
- contention ratio

## Layer 3 — Edge Policy

- SAFE/BALANCED/PERF mode decision
- workload scaling
- power-cap scaling

## Layer 4 — Protection

- thermal/TSV guard checks
- hysteresis-based stack-power clamp (separate trip/recover thresholds)

## Layer 5 — Integration Runtime

- multi-engine snapshot -> `HBMInput`
- runtime tick (`policy -> observe -> protect -> re-observe`)

## Layer 6 — Audit Bridge

- `append_observation_to_chain()` to write HBM ticks into external audit chains (SYD_DRIFT-compatible API)

## Layer 7 — Temporal Dynamics

- `simulate_hbm_trajectory()` for multi-tick thermal/protection interaction
- first-order thermal lag model for accumulated edge burst risk analysis
