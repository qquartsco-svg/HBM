# HBM_System 레이어 스택

> English: [01_LAYER_STACK_EN.md](01_LAYER_STACK_EN.md)

## Layer 0 — Contracts

- `HBMConfig`
- `HBMInput`
- `HBMObservation`
- `EdgePolicyDecision`

## Layer 1 — Physics

- bandwidth estimate
- thermal gradient estimate
- TSV failure risk estimate
- power density estimate

## Layer 2 — Controller

- channel arbitration
- contention ratio

## Layer 3 — Edge Policy

- SAFE/BALANCED/PERF 정책 결정
- workload scaling
- power-cap scaling

## Layer 4 — Protection

- thermal/TSV guard 검사
- 히스테리시스 기반 stack power clamp (trip/recover 분리)

## Layer 5 — Integration Runtime

- multi-engine snapshot -> `HBMInput`
- runtime tick (`policy -> observe -> protect -> re-observe`)

## Layer 6 — Audit Bridge

- `append_observation_to_chain()`를 통해 외부 감사체인(SYD_DRIFT 호환 인터페이스)에 기록

## Layer 7 — Temporal Dynamics

- `simulate_hbm_trajectory()`로 다중 tick 열-보호 상호작용 시뮬레이션
- 1차 열 동역학(thermal lag)으로 edge burst workload의 시간 누적 리스크 분석
