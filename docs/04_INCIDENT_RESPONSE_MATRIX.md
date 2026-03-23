# 04_INCIDENT_RESPONSE_MATRIX

이 문서는 **알람 코드·건강 판정·심각도·대응 SLA·권장 담당 역할·자동 조치**를 한 표로 정리한 인시던트 매트릭스다.  
실제 조직의 역할명은 바꿔 써도 되며, 여기서는 역할을 **기능 단위**로만 정의한다.

## 1) 심각도(Severity) 정의

| Severity | 의미 | 목표 응답 시간(권장) | 비고 |
|----------|------|----------------------|------|
| P0 | 서비스/안전에 직접 위협 | 15분 이내 | 무결성 실패, CRITICAL verdict 지속 |
| P1 | 성능 저하 또는 잠재 위험 | 1시간 이내 | FRAGILE 지속, 알람 반복 |
| P2 | 관측 이상 또는 정책 위반 가능성 | 4시간 이내 | INFO/WARN 수준 |
| P3 | 정보성 | 다음 영업일 | 문서화·모니터링만 |

## 2) 알람 코드 × 매트릭스 (Journal / 무결성)

| Code | Severity | P | SLA(권장) | 1차 담당 | 2차 담당 | 자동 조치(권장) | 수동 조치(필수) |
|------|----------|---|-----------|----------|----------|-----------------|-----------------|
| `JOURNAL_REPLAY_INTEGRITY_FAIL` | CRITICAL | P0 | 15m | On-call Ops | Security/Platform | ingestion 차단 또는 safe mode 플래그 | journal/store 백업, 원인 분류, 신뢰 구간 복구 |
| `JOURNAL_REPLAY_VERIFIED` | OK | P3 | N/A | Ops | — | 정상 로그만 | 주기적 아카이브 |
| `JOURNAL_REPLAY_NOT_ACTIVE` | INFO | P2 | 4h | Platform | Ops | 없음(정책 결정) | 프로덕션에서 journal 활성화 여부 결정 |

**`journal_verify_report.reason`별 추가 가이드**

| reason | P | 권장 조치 |
|--------|---|-----------|
| `hash_chain_mismatch` | P0 | tamper/손상 의심 → 입력 중단 + 증거 보존 + 복구 범위 확정 |
| `invalid_json` | P1 | 파일 손상/부분 쓰기 → 마지막 정상 라인까지 절단 후 검증 |
| `invalid_row_schema` | P1 | 스키마 불일치 → 송신측/버전 불일치 점검 |
| `journal_read_exception` | P1 | 디스크/권한/OS → I/O 점검 |
| `journal_not_found` | P2 | 최초 기동 또는 경로 오류 → 설정 검증 |

## 3) 건강 판정(Verdict) × 매트릭스

| Verdict | P | SLA(권장) | 1차 담당 | 자동 조치(권장) | 수동 조치 |
|---------|---|-----------|----------|-----------------|-----------|
| `HEALTHY` | P3 | N/A | Ops | 없음 | 정기 리포트 |
| `STABLE` | P2 | 4h | Ops | 관측 강화 로그 | 추세 모니터링 |
| `FRAGILE` | P1 | 1h | Ops + SRE | workload 완화, SAFE 정책 고정 | 상위 오케스트레이터에 부하 제한 요청 |
| `CRITICAL` | P0 | 15m | On-call Ops | 보호 clamp 유지, 입력 제한 | 상위 시스템 긴급 정지/페일오버 검토 |

## 4) 체인 이벤트 (SYD_DRIFT 호환)

| 이벤트 | 조건 | P | 권장 조치 |
|--------|------|---|-----------|
| `HBM_ALERT_CRITICAL` | journal replay `CRITICAL` | P0 | chain export 백업 + Ops 에스컬레이션 |
| 일반 HBM tick 블록 | 정상 관측 | P3 | 정상 아카이브 |

## 5) 자동화 연동 훅 (선택)

운영 환경에 따라 아래 JSON 필드를 **웹훅/티켓 시스템**으로 전달한다.

- `journal_alert.json`: `severity`, `code`, `actionable`, `status`, `reason`
- `journal_verify_report.json`: `status`, `stopped_at_line`, `verified_entries`, `head_hash`

## 6) 관련 문서

- `docs/03_OPERATIONS_RUNBOOK.md` — 절차 중심 런북
- `docs/02_FORMULAS.md` — 지표·수식 정본
