# Autoresearch Session — D04 PoC UI

- Started: 2026-09-17
- Resumed: 2026-09-18 (RSI Inner 3–7 + Outer round 2)
- Target: `src/poc_d04/server.py` (CSS + PAGE + result markup)
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

- Numeric improvement: **+28 pts** (72 → 100), first hit at exp 1
- Guard: pytest **44 passed** every KEEP
- Outer score: **95.0** (`outer_score(100, 1, 28)`)
- Weights unchanged (all axes 100; reweighting is a no-op)

## Outer verdict
Frozen Metric no longer ranks UI. Inner chrome should freeze. A harder eval (contrast, fold screenshot) needs a **human-owned eval v2**. Inner Loop must not edit `eval/` or `meta_eval/`.

## Resume
Do not start Inner unless:
1. Guard is red, or
2. Human extended `eval/` (new Frozen checks), or
3. A real 시연 회귀가 있다.

`make serve` → http://127.0.0.1:8765
