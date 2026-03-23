# 03_OPERATIONS_RUNBOOK

HBM_System 운영 시, 보안/무결성/성능 신호를 기준으로 **즉시 대응 가능한 실행 절차**를 정의한다.

## 1) 운영 신호 우선순위

1. 무결성/보안 (`journal replay alert`)
2. 시스템 건강도 (`Omega_hbm`, verdict)
3. 성능 지표 (`bandwidth_gbps`, `contention_ratio`)

무결성 신호가 `CRITICAL`이면 성능 지표보다 우선한다.

## 2) 알람 코드와 기본 조치

### `JOURNAL_REPLAY_INTEGRITY_FAIL` (CRITICAL)

- 의미: nonce journal replay 검증 실패(`status=stopped|error`)
- 1차 조치:
  - ingestion 입력 차단(또는 안전 모드 전환)
  - 해당 노드 nonce store/journal 파일 백업
  - 마지막 정상 `head_hash`와 `stopped_at_line` 확보
- 2차 조치:
  - 원인 분류: `hash_chain_mismatch`, `invalid_json`, `invalid_row_schema`, `journal_read_exception`
  - 공격 가능성/운영 장애 여부 분리
- 3차 조치:
  - 필요 시 journal 회복(정상 구간까지만 재사용)
  - 재시작 후 `--journal-verify-report` 확인

### `JOURNAL_REPLAY_VERIFIED` (OK)

- 의미: startup replay 검증 정상
- 조치:
  - 운영 지속
  - `verified_entries`, `head_hash` 주기 로깅

### `JOURNAL_REPLAY_NOT_ACTIVE` (INFO)

- 의미: journal 미설정 또는 파일 부재
- 조치:
  - 운영 정책에 따라 journal 강제 여부 결정
  - 프로덕션 권장: `--nonce-journal`, `--journal-verify-report`, `--journal-alert-output` 활성화

## 3) Verdict 기반 조치

### `HEALTHY`
- 정상 운영

### `STABLE`
- 관측 강화(샘플링/로그 유지), 즉시 제한 없음

### `FRAGILE`
- 보호정책 강화: workload 완화, thermal margin 확보
- 필요 시 `SAFE` 모드 고정

### `CRITICAL`
- 보호 동작 우선: 전력 clamp 유지, 입력 부하 제한
- 외부 상위 오케스트레이터에 즉시 알림 전파

## 4) 운영 실행 템플릿

### 권장 실행 플래그(보안 강화)

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

### 점검 체크리스트

- `journal_alert.severity`가 `CRITICAL`인가?
- `journal_verify_report.status`가 `ok`인가?
- `Omega_hbm`와 verdict가 추세적으로 악화되는가?
- `thermal_gradient_c`와 `tsv_failure_risk`가 임계 구간에 접근하는가?

## 5) 장애 후 복구 절차

1. 증거 보존: `journal_verify_report.json`, `journal_alert.json`, chain export 백업
2. 입력 정지: replay/tamper 의심 구간 ingestion 중단
3. 범위 확인: 마지막 정상 `head_hash` 기준으로 복구 범위 확정
4. 재기동: 안전 플래그 활성화 상태로 재시작
5. 검증: `status=ok` 확인 후 점진적 부하 복구

## 6) 향후 운영 고도화

- 알람 코드를 incident 시스템과 자동 연동
- fleet 단위(노드 다수) 집계 runbook 확장
- 정기적 threshold 재보정(calibration loop) 문서화
