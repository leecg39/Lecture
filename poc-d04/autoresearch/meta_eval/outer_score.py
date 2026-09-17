"""Level 0 — 절대 불변. Outer Loop 성과 측정."""
from __future__ import annotations


def outer_score(final_score: float, convergence_round: int, improvement_per_exp: float,
                target_score: float = 78.0, max_rounds: int = 6) -> float:
    """final 50% + 수렴 속도 30% + 실험당 개선 20%."""
    final_n = min(1.0, final_score / target_score)
    speed_n = max(0.0, 1.0 - (convergence_round / max_rounds)) if final_score >= target_score else 0.3
    imp_n = min(1.0, max(0.0, improvement_per_exp / 10.0))
    return round(100 * (final_n * 0.5 + speed_n * 0.3 + imp_n * 0.2), 2)
