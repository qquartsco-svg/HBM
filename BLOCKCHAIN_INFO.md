# BLOCKCHAIN_INFO

## Scope

`HBM_System` 배포 무결성 기준 문서다.  
정본 해시 매니페스트는 `SIGNATURE.sha256` 이다.

## Integrity Model

- 배포 검증 기준 파일: `SIGNATURE.sha256`
- 릴리스 로그: `PHAM_BLOCKCHAIN_LOG.md`
- 버전 기준 파일: `VERSION`
- 패키지 메타 버전: `pyproject.toml`

## Verification

```bash
cd /Users/jazzin/Desktop/00_BRAIN/_staging/HBM_System
shasum -a 256 -c SIGNATURE.sha256
python -m pytest -q
```

## Signature Regeneration

아래 규칙으로 `SIGNATURE.sha256`를 재생성한다.

- 상대 경로 엔트리 사용
- 제외: `.pytest_cache/`, `reports/`, `__pycache__/`, `.DS_Store`
- 포함: 코드/문서/테스트/메타(`VERSION`, `CHANGELOG.md`, `WORK_LOG.md`)

## Notes

- HBM_System은 고충실도 sign-off 툴이 아니라, 패키지/시스템 운영 리스크 관측 엔진이다.
- 성능 지표와 보안/무결성 신호를 함께 감사체인으로 남기는 운영 모델을 채택한다.
