# 구현 계획 — 계획 → 구현 → 적대적 검토 → 수정 → 커밋·푸시 반복

기한: 2026-09-19(토) 00:00 제출. 각 사이클은 커밋 1개 이상으로 끝낸다.
원격: https://github.com/leecg39/poc-d04-purchase-request-check (private)

## 사이클 1 — 골격·데이터 (문서·카탈로그·표본·정답표) — 완료 `301fde4`
- [x] PRD / TRD / PLAN 작성
- [x] `catalog.py`: 필수 항목표 6항목, 용어 사전 10품목(함정 3쌍: 볼밸브·PVC 파이프·강관 50A/100A, 엘보 90/45도)
- [x] `data_gen.py`: 30건 스펙(5유형×6), 렌더링(템플릿 6종), 스캔 손상(29건), 정답표 354행
- [x] `tests/test_data_gen.py`
- 검토 결과: 정답표 오프셋 = 원문 (assert + 테스트). 시연 사례 D04-13이 기획안 §4-6과 글자 단위로 일치

## 사이클 2 — 규칙 축 (추출·판정·게이트·질문·지표) — 완료 `301fde4`
- [x] `extract.py` 규칙 백엔드 + 붙여넣기 로더 + LLM 백엔드(키 있을 때, 가정)
- [x] `rules.py`, `gate.py`, `questions.py`, `evaluate.py`, `pipeline.py`
- [x] `cli.py` (`gen/run/check-paste/eval/workbook/examples/all`)
- [x] 테스트: extract/rules/gate/evaluate/paste
- 검토 결과: 첫 실행에서 정답 불일치 4건(단위만 있는 줄, `까지` 붙은 ISO 날짜) → 추출기 수정 → 상태 정확도 100%

## 사이클 3 — 교실 산출물 — 완료 `301fde4`
- [x] `prompts/` 4종
- [x] `workbook.py` xlsx (안내·누락표시표·역할표·8칸·5항목·시간기록지·검증지표표·참조표)
- [x] `examples.py` 잘못된 초안(G1·G2·G4·G5) + 오프라인 캡처(시연 1 + 조별 6)
- [x] `docs/DEMO_SCRIPT_15min.md`, `README.md`, `Makefile`

## 사이클 4 — 적대적 검토·수정 — 완료 `96b0e7a`
- [x] `docs/REVIEW_01.md`: 공격 A–L (단위 붙임, 숫자형, 중복 토큰 위치, ID 없는 규격 병합, 키 공백, 소문자 ID, 빈 출력, 복수 품목, 비JSON, 중복 항목, 메타 키)
- [x] 발견 사항 수정 + 회귀 테스트 12개
- [x] 커밋·푸시

## 사이클 5 — 후보 B·C 양식, 코드블록 입력, 문서 정합 — 완료
- [x] 후보 B 견적 비교 준비 시트 + 가상 견적서 6행(단위·배송비·규격 함정)
- [x] 후보 C 발주·입고 공동 조회 시트 + 가상 발주 5건(분할 입고·미갱신·갱신자 공란)
- [x] ```` ```json ```` 코드블록·설명 문장 포함 붙여넣기 허용 (REVIEW_02 · M)
- [x] TRD §6 테스트 목록·로더 허용 범위 갱신
- [x] `docs/REVIEW_02.md`: 기획안 ↔ 산출물 정합 점검

## 완료 감사 (PRD 기준) — `docs/REVIEW_02.md` §3 참조

## 남은 제안 (범위 밖, 사용자 결정)
- 교실 리허설 후 기획안 §8 "리허설 미수행" 문구 갱신
- 실제 ChatGPT 출력 5~10건을 `check-paste --truth`로 돌려 REVIEW_03에 기록(AI 백엔드 실측)
- 시나리오에 도구 지정이 생기면 프롬프트 팩을 해당 도구 형식으로 조정
