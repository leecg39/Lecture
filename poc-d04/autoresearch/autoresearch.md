# Autoresearch Session — D04 PoC UI

- Started: 2026-09-17
- Target: `src/poc_d04/server.py` (CSS + PAGE + result markup)
- Dev: `http://127.0.0.1:8765`
- Mode: Bounded Inner Loop (stopped early — metric ceiling)

## Results
| Exp | Score | Decision | Note |
|-----|-------|----------|------|
| 0 baseline | 72 | — | bare system CSS |
| 1 | 100 | KEEP | industrial slate / IBM Plex / hero-shell-panel |
| 2 | 100 | KEEP | summary chips, denser gates, collapsible JSON (Guard-safe) |

- Improvement: **+28 pts** (72 → 100)
- Guard: pytest 44 passed
- Outer: metric saturated after exp1 → switched to qualitative 시연 readability

## Resume
Metric is maxed. Next useful work needs harder Frozen Metric in a **new eval version** (Outer may request human to extend `eval/` checklist) or Lighthouse/contrast tooling. Do not inflate score by editing `eval/score_calculator.py` from Inner Loop.

## Server
`make serve` → http://127.0.0.1:8765
