# Research Directive — D04 PoC 데모 UI

## Goal
시연용 로컬 웹 데모(`http://127.0.0.1:8765`)의 UI를 **강의 시연에서 부끄럽지 않은 수준**으로 올린다.
기능(추출·판정·게이트·사람 확정 칸 공란)은 절대 깨지지 않게 유지한다.

## Frozen Metric
`eval/score_calculator.py` 복합 점수 (0–100). Inner Loop는 이 파일을 수정하지 않는다.
가중치: `outer/metric_weights.json`

목표: baseline 대비 **+15점 이상**, 최종 **≥ 78**.

## Target (수정 가능)
- `src/poc_d04/server.py` 의 `CSS`, `PAGE`, 결과 HTML 마크업 문자열만
- 스타일/레이아웃/타이포/시각 계층만 변경

## Frozen (수정 금지)
- `eval/`, `meta_eval/`
- 파이프라인 로직: `extract.py`, `rules.py`, `gate.py`, `questions.py`, `evaluate.py`, `pipeline.py`
- 데이터·정답표·프롬프트 팩
- 사람 확정 칸을 AI가 채우는 행위
- 서버를 외부 바인딩하거나 의존성 추가 (표준 라이브러리 + 기존 openpyxl만)

## Guard
```
cd poc-d04 && PYTHONPATH=src .venv/bin/python -m pytest -q
```
통과 필수. Guard 실패 시 revert.

## Design Hints (시연 맥락)
1. 브랜드 신호: "D04 · 구매 요청서 누락 확인"이 첫 화면에서 강하게 읽혀야 한다.
2. 판단 기준 문장("추가 문의 항목을 찾았는가")이 눈에 들어와야 한다.
3. **사람 확정** 열은 시각적으로 분리(노란 배경만으로 부족하면 헤더/라벨로 강조).
4. 게이트 위반 / OK / 경고의 색 계층을 명확히.
5. 건설·교육 PoC 분위기: 차갑고 정돈된 산업적 톤. AI 기본 보라/크림·테라코타/신문 레이아웃 금지.
6. 폰트는 system 기본만으로 끝내지 말고, Google Fonts CDN 또는 의도적 스택 사용 가능(오프라인 시 fallback).
7. 시연 거리(프로젝터)에서도 CTA·표 헤더가 읽혀야 한다.

## Iterations (이번 세션)
Bounded: Inner 8–12 완료 (재실행). 이후 `autoresearch.md`에 상태 남기고 중단.

## Outer update (round 1 → 2)
Frozen Metric이 실험 1에서 100으로 포화됨. 이후 실험은:
- 점수 **100 유지** + Guard 통과 필수
- 추가 판정(정성): 시연 거리 가독성 — 결과 요약이 fold 위에 보이는가, 게이트 카드가 스캔 가능한가, 사람 확정 열이 표에서 즉시 식별되는가
- 악화(정보 밀도↓, 대비↓, CTA 약화)면 DISCARD

## Outer update (round 2 → 3)
정성 Inner(3–7) 전부 KEEP, 점수는 계속 100. Frozen Metric이 더 이상 변별하지 못한다.
다음 Inner는 **새 위젯을 넣지 않는다.** 회귀 수정만.
사람이 `eval/`에 대비·fold 스크린샷 체크를 추가하기 전에는 Inner를 재개하지 말 것. Inner는 eval을 수정하지 않는다.

## Outer update (round 3 → 4)
재실행 Inner 8–12도 전부 KEEP·100. 변별력은 여전히 0.
허용된 정성 개선(sticky stepper, /bad→게이트, 대비, 1–5 키, 확인필요 행)은 반영됨.
다음은 회귀만. 새 위젯·새 색 실험은 DISCARD 기본.

## Dev server
```
cd poc-d04 && PYTHONPATH=src .venv/bin/python -m poc_d04 serve
```
변경 후 서버는 프로세스 재시작이 필요할 수 있음(모듈 로드 시점 CSS).
