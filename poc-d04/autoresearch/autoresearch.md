# Autoresearch Session — D04 PoC UI

- Started: 2026-09-17
- Resumed: 2026-09-18 (RSI Inner 3–7 + Outer round 2)
- Rerun: 2026-09-18 (Inner 8–12 + Outer round 3)
- Rerun: 2026-09-18 (Inner 13–17 + Outer round 4)
- Round 5: 2026-09-18 (Inner 18–22, 사람 지시 — 게이트 감사 단계 기능 확장, PDF M03 기반)
- Rerun: 2026-09-18 (Inner 23–27 + Outer round 6 — STEP 4 크롬만)
- Target: `src/poc_d04/server.py` (CSS + PAGE + result markup); round 5에서 `gate.py`·`extract.py(load_pasted)`·`examples.py`까지 한정 확장
- Dev: `http://127.0.0.1:8765`
- Mode: Bounded RSI. Frozen Metric ceiling after exp 1.

## Results
| Exp | Score | Decision | Note |
|-----|-------|----------|------|
| 0 baseline | 72 | — | bare system CSS |
| 1 | 100 | KEEP | industrial slate / IBM Plex / hero-shell-panel |
| 2 | 100 | KEEP | summary chips, denser gates, collapsible JSON |
| 3 | 100 | KEEP | 15분 시연 단계 위저드 (입력→추출→규칙→게이트→질문) |
| 4 | 100 | KEEP | projector-scale type |
| 5 | 100 | KEEP | 사람 확정 열 헤더 `· 비움` + 두꺼운 악센트 (`td.human` 공란 유지) |
| 6 | 100 | KEEP | `/bad` 실패 장면 고스트 버튼 CTA |
| 7 | 100 | KEEP | `prefers-reduced-motion` 스테퍼 트랜지션 제거 |
| 8 | 100 | KEEP | sticky stepper |
| 9 | 100 | KEEP | `/bad` 게이트 단계부터 |
| 10 | 100 | KEEP | ink/muted 대비 |
| 11 | 100 | KEEP | 숫자 키 1–5 |
| 12 | 100 | KEEP | 확인 필요 행 하이라이트 |
| 13 | 100 | KEEP | scroll-padding-top |
| 14 | 100 | KEEP | sticky bottom step-nav |
| 15 | 100 | KEEP | 게이트 코드 배지 확대 |
| 16 | 100 | KEEP | 성공기준 왼쪽 액센트 |
| 17 | 100 | KEEP | 미사용 CSS 삭제 |
| 18 | 100 | KEEP | [R5] 지시 ↔ 결과 대조 체크리스트 — 게이트 전부 통과/위반 (PDF p5) |
| 19 | 100 | KEEP | [R5] 위반별 권고 조치·확인 담당 + AI 초안→현장→본사 흐름 (PDF p6) |
| 20 | 100 | KEEP | [R5] 원문 근거 하이라이트 + 원문 추적 비율 칩 (PDF p8·p13) |
| 21 | 100 | KEEP | [R5] **G6 범위 밖 행위** — 최저가·공급사 선정·자동 발주·자재군 확대 (PDF p9) |
| 22 | 100 | KEEP | [R5] 판정 배너 계속 / 재시험 (PDF p10 성공·수정·중단) |
| 23 | 100 | KEEP | scroll-padding-bottom |
| 24 | 100 | KEEP | 미사용 .linkish/.arrow 삭제 |
| 25 | 100 | KEEP | 원문 하이라이트 필드 태그 확대 |
| 26 | 100 | KEEP | 계속/재시험 판정 배너 글자 확대 |
| 27 | 100 | KEEP | 키보드 힌트 칩 확대 |

- Numeric improvement: **+28 pts** (72 → 100), first hit at exp 1
- Guard: pytest **44 passed** every KEEP (round 5부터 **45 passed**, G6 테스트 추가)

## Round 5 — 게이트 감사 단계 (사람 지시)
근거: `outputs/03_PoC설계_실사형/03_PoC설계_건설현장_실사형.pdf`. 강의안 5개 항목을 STEP 4에 모두 반영.
- 게이트 위반 dict에 `조치`·`담당` 키 추가 (additive). `load_pasted`가 항목표 밖 키를 `범위밖`으로 보존하고 경고를 남김.
- 실패 장면(`/bad`) 초안에 `공급사 = B상사 (최저가 자동 선정)` 1건 추가 → G2·G1·G4·G5·**G6** 5건, 원문 추적 3/6.
- 규칙 백엔드는 여전히 게이트 위반 0 (`test_rule_backend_has_no_gate_violations`).
- Frozen Metric은 회귀 감지용으로만 사용(전부 100). 기능 검증은 Guard(pytest 45) + 헤드리스 스크린샷으로 확인.
- Outer score: **95.0** (`outer_score(100, 1, 28)`)
- Weights unchanged (all axes 100; reweighting is a no-op)

## Outer verdict
Frozen Metric no longer ranks UI. Inner chrome should freeze. A harder eval (contrast, fold screenshot) needs a **human-owned eval v2**. Inner Loop must not edit `eval/` or `meta_eval/`.

## Resume
Round 6 (23–27) polished STEP 4 scan only. Metric still 100. Do not start Inner unless:
1. Guard is red, or
2. Human extended `eval/` (new Frozen checks), or
3. A real 시연 회귀가 있다.

`make serve` → http://127.0.0.1:8765
