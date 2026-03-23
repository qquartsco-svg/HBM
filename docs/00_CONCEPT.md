# HBM_System 개념 (Level C)

> English: [00_CONCEPT_EN.md](00_CONCEPT_EN.md)

HBM_System은 HBM 그 자체를 제조하는 엔진이 아니라, **패키지/시스템 레벨 기초 설계 검증 엔진**이다.

- Level A (`Fabless`): 소자 물리
- Level B (`Memory_Engine`): 셀/회로
- Level C (`HBM_System`): 적층/패키지/채널/컨트롤러

## 엣지 AI 설계 철학

엣지 AI는 전력·열·실시간성 제약이 강하므로, HBM은 최고 성능보다 **생존 가능한 성능**이 중요하다.

- burst workload에서 SAFE/BALANCED/PERF 정책 전환
- 열/TSV 임계 초과 시 power clamp
- 하위 엔진 건강도를 상위 시스템 건강도(`omega_hbm`)에 반영

## 엔진 연결 철학

HBM_System은 단절된 독립 엔진이 아니라, 하위 엔진 출력을 흡수하는 상위 통합 엔진이다.

- `fabless.omega_global` -> signal margin 근거
- `memory.omega_global`, `rowhammer_risk`, `retention_risk` -> 메모리 안정성 입력
- `battery.omega_battery` -> cooling/전력 여유 추정
- `vectorspace.omega_vector` -> 시스템 통합 건강도 반영
