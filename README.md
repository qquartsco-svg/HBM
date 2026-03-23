# HBM_System

> English: [README_EN.md](README_EN.md)

HBM_System은 반도체 스택에서 **패키지/시스템 레벨(HBM, TSV, 인터포저, 채널, 컨트롤러)**을 다루는 독립 엔진이다.

## 왜 Fabless 내부가 아니라 독립 엔진인가

- `Fabless`는 소자 물리/설계 평가(레벨 A)에 최적화됨
- `Memory_Engine`은 셀/센스앰프/row hammer(레벨 B)에 최적화됨
- `HBM_System`은 적층 열, TSV 리스크, 채널 병렬성, 컨트롤러 중재(레벨 C)를 다룸

즉 HBM은 하위 물리를 소비하는 **상위 시스템 레이어**이므로 독립 엔진이 맞다.

## MVP 구성

```text
hbm_system/
├── contracts.py     # HBM 구성/입력/출력 계약
├── physics.py       # bandwidth, thermal gradient, TSV risk, power density
├── controller.py    # channel arbitration, contention 지표
├── observer.py      # Omega_hbm 통합 판정
└── bridge.py        # Fabless/Memory 지표 -> HBM 입력 변환
```

확장 레이어:

- `presets.py` — HBM2E/HBM3/HBM3E/edge_low_power preset
- `edge_policy.py` — SAFE/BALANCED/PERF 정책
- `protection.py` — thermal/TSV guard 기반 power clamp
- `integration.py` — multi-engine snapshot ingestion
- `runtime.py` — policy->observe->protect tick
- `audit_bridge.py` — SYD_DRIFT 호환 감사체인 어댑터
- `dynamics.py` — 시간축 열 동역학 기반 다중 tick 시뮬레이터
- `memory_adapter.py` — Memory_Engine 관측값 정식 어댑터

## 핵심 지표

- `bandwidth_gbps`: 스택/채널 병렬성과 컨트롤러 효율 기반 대역폭 추정
- `thermal_gradient_c`: 적층 열밀도 기반 온도 기울기 추정
- `tsv_failure_risk`: TSV 밀도 + 열 조건 기반 실패 리스크
- `power_density_w_per_stack`: 스택당 전력 밀도
- `Omega_hbm`: 위 지표와 하위 레이어 건강도를 결합한 통합 건강도

## 실행

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
python -m pytest -q
```

참고:
- 기본 논리/통합 경로는 현재 `30 passed`로 확인됨
- TCP 소켓 기반 스트림 테스트 2개는 `socket.bind(...)` 권한이 허용된 환경에서만 통과
- 즉 로컬 샌드박스/제한 환경에서는 `30 passed, 2 deselected(or permission-blocked)`가 정상 판정일 수 있음

## High-Load Thermal Stress 리포트

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
python scripts/high_load_thermal_stress_report.py
python scripts/run_hbm_audit_loop.py
python scripts/run_hbm_stream_loop.py
```

출력 파일:
- `reports/HIGH_LOAD_THERMAL_STRESS_REPORT.md`
- `reports/HBM_AUDIT_CHAIN.json`
- `reports/HBM_STREAM_AUDIT_CHAIN.json`

입력 예시:
- `examples/hbm_stream_input.jsonl`

스트림 소스 선택:

```bash
# file (default)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl

# stdin (pipe)
cat examples/hbm_stream_input.jsonl | python scripts/run_hbm_stream_loop.py --source stdin

# tcp (socket)
python scripts/run_hbm_stream_loop.py --source tcp --tcp-host 127.0.0.1 --tcp-port 18081 --max-packets 100

# tcp_server (HBM이 직접 listen)
python scripts/run_hbm_stream_loop.py --source tcp_server --tcp-host 0.0.0.0 --tcp-port 18081 --max-packets 100

# strict schema + auth token
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --strict-schema --auth-token secret

# HMAC signature verify (payload + t_s replay window)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --hmac-secret topsecret --hmac-field hmac_sha256 --clock-t-s 100.0 --hmac-max-age-s 5.0

# nonce anti-replay (duplicate nonce drop)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-field nonce --nonce-cache-size 4096

# nonce 지속화 + TTL (재시작 이후 replay 차단)
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-store reports/nonce_store.json --nonce-ttl-s 30.0 --clock-t-s 100.0

# append-only nonce journal + compact
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-store reports/nonce_store.json --nonce-journal reports/nonce_journal.jsonl --nonce-journal-compact

# nonce journal 검증 리포트 출력
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-journal reports/nonce_journal.jsonl --journal-verify-report reports/journal_verify_report.json

# journal 검증 결과를 운영 알람 이벤트로 출력
python scripts/run_hbm_stream_loop.py --source file --input examples/hbm_stream_input.jsonl --enforce-nonce --nonce-journal reports/nonce_journal.jsonl --journal-alert-output reports/journal_alert.json
```

참고:
- nonce journal은 hash-linked 레코드(`prev_hash`, `hash`)를 사용해 무결성 체인을 유지합니다.
- 각 레코드는 `payload_digest`를 포함해 "어떤 패킷이 처리되었는지"까지 추적합니다.
- `--journal-verify-report`를 주면 재시작 시 journal replay 검증 결과(`status`, `verified_entries`, `stopped_at_line`, `reason`)를 JSON으로 저장합니다.
- `--journal-alert-output`을 주면 검증 결과를 운영 알람 이벤트(`severity`, `code`, `actionable`)로 JSON 저장합니다.
- `status=stopped|error`는 `CRITICAL/JOURNAL_REPLAY_INTEGRITY_FAIL`로 매핑되어 즉시 대응 가능한 신호로 출력됩니다.
- `status=stopped|error`인 경우, 해당 알람 이벤트가 SYD_DRIFT 감사체인에도 `HBM_ALERT_CRITICAL` 블록으로 append됩니다.

## 설계 문서

- `docs/00_CONCEPT.md`
- `docs/01_LAYER_STACK.md`
- `docs/02_FORMULAS.md`

## 유기적 엔진 연결점

- `integration.merge_engine_snapshots()` — Fabless/Memory/Battery/VectorSpace/Runtime 조합
- `integration.build_input_from_engine_snapshots()` — 다중 엔진 상태 -> `HBMInput`
- `integration.build_input_from_typed_states()` — DTO 기반 상태 -> `HBMInput`
- `audit_bridge.append_observation_to_chain()` — HBM 결과 -> 외부 감사체인

## HBM_System 개념 설명 (입문용)

HBM_System은 "HBM 칩 설계 엔진"이 아니라, **HBM 패키지/시스템 레벨의 건강도와 운영 리스크를 추적하는 상위 관측 엔진**이다.

- `Fabless` (레벨 A): 소자/물리 타당성
- `Memory_Engine` (레벨 B): 셀/회로 안정성
- `HBM_System` (레벨 C): 적층 열/TSV/채널/컨트롤러/운영 무결성

즉, HBM_System은 하위 엔진의 상태를 받아 "실제 제품 시스템 관점에서 지금 안전하게 지속 동작 가능한가?"를 `Omega_hbm`으로 판정한다.

## 핵심 수식 요약

상세 수식은 `docs/02_FORMULAS.md`에 있고, README에서는 운용 관점 핵심만 요약한다.

1) 대역폭 근사:

`bandwidth_gbps ~= f(stack_count, channels_per_stack, io_rate, contention_ratio, controller_efficiency)`

2) 전력 밀도:

`power_density_w_per_stack = total_power_w / stack_count`

3) 열 기울기:

`thermal_gradient_c ~= g(power_density, cooling_coeff, ambient_temp_c)`

4) TSV 실패 리스크:

`tsv_failure_risk ~= h(tsv_density, thermal_gradient_c)`

5) 통합 건강도:

`Omega_hbm = weighted(thermal, tsv, contention, lower_layer_health, runtime_pressure)`

6) 보안/무결성 운영 신호:

- journal replay 검증 `status/reason`
- 운영 알람 `severity/code/actionable`
- `stopped|error -> CRITICAL/JOURNAL_REPLAY_INTEGRITY_FAIL`

## 4단계 평가 (긍정/중립/보수/부정)

### 1) 긍정 (잘 된 점)

- 레벨 A/B/C 분리(Fabless/Memory/HBM_System)가 명확해 레이어 꼬임이 없다.
- runtime 파이프라인(policy -> observe -> protect -> re-observe)이 일관되다.
- 실시간 ingestion(file/stdin/tcp/tcp_server) + HMAC + nonce + journal까지 운용 경로가 살아있다.
- tamper 시 `CRITICAL` 알람과 SYD_DRIFT 체인 append가 연결되어 감사 추적성이 높다.

### 2) 중립 (방향은 맞지만 미완성)

- 현재 모델은 "HBM 제품 관측/평가 엔진"에 가깝고 PHY/SI/PI 풀 시뮬레이터는 아니다.
- controller는 arbitration 중심 MVP이며 QoS/refresh 간섭/워크로드 클래스 모델은 확장 여지.
- `Omega_hbm`는 실용 지표이지만 산업 인증(SOTIF/ISO26262 유사 프레임) 직접 대체 모델은 아님.

### 3) 보수 (지금 결정해야 할 설계 포인트)

- 운영 리포트(JSON)와 체인 이벤트를 외부 관제 대시보드 규격과 어떻게 표준화할지 결정 필요.
- lower-layer 입력 품질(측정 지연/결측/스케일 불일치)에 대한 강건한 보정계층 강화 필요.
- 실측 데이터(calibration dataset) 기반으로 가중치와 임계값을 지속 보정하는 운영 루프 필요.

### 4) 부정 (현 단계 한계)

- 실제 HBM 실리콘/패키지 tape-out sign-off 용 도구가 아니다.
- SI/PI, TSV EM 수명, 상세 thermal FEM 같은 고충실도 물리 해석은 범위 밖이다.
- 공급망/공정 변동/장기 열화의 실측 기반 통계 모델은 아직 얕다.

## 확장성과 활용성

### 확장서(확장 문서) 관점 활용

- 연구/운영팀 공통 언어로 `Omega_hbm`와 replay-alert를 공유할 수 있다.
- 하위 엔진에서 올라오는 다종 상태를 단일 계약(`HBMInput`)으로 정규화한다.
- 보안 이벤트를 chain 이벤트로 남겨 "성능 + 무결성"을 함께 감사할 수 있다.

### 실무 활용 시나리오

- 엣지 AI 장치의 HBM 위험 조기 감지(열/contestion/tsv 리스크)  
- 운영 중 replay/tamper 신호를 즉시 CRITICAL로 승격해 대응 자동화  
- 배포 전후 비교: preset/워크로드별 안정 구간(안전 운전 영역) 추적

## 현재 한계성 정리

- 정밀 공정/물성 해석 대신 "운영 의사결정용 근사 모델" 중심이다.
- 외부 관제/알람 플랫폼과의 표준 연동(예: schema registry, incident ticket bridge)은 미완성.
- 다중 노드/클러스터 단위 HBM fleet 운영 모델은 아직 단일 노드 중심 설계다.

## 추후 확장 방향

1. Controller 고도화: QoS class, refresh interference, burst scheduling 정책 도입  
2. Calibration 루프: 실측 로그 기반 가중치/임계값 자동 보정  
3. Fleet 관제: multi-node `Omega_hbm` 집계 + cluster risk rollout  
4. Audit 확장: chain 이벤트를 운영 incident/workflow와 직접 연결  
5. 문서 확장: 개념/수식/운영 runbook을 KR/EN 동기화로 지속 관리

## 블록체인 서명/무결성

- 기준 파일: `SIGNATURE.sha256`
- 무결성 문서: `BLOCKCHAIN_INFO.md`
- 릴리스 로그: `PHAM_BLOCKCHAIN_LOG.md`

검증:

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
shasum -a 256 -c SIGNATURE.sha256
python -m pytest -q
```
