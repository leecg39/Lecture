"""추출 → 규칙 판정 → 게이트 감사 → 보완 질문을 한 번에 묶는 실행 경로."""
from __future__ import annotations

import json
from pathlib import Path

from .data_gen import load_dataset
from .evaluate import render_report, score
from .extract import extract_llm, extract_rule, load_pasted
from .gate import audit
from .questions import draft
from .rules import check


def run_doc(text: str, doc_id: str | None = None, backend: str = "rule", pasted=None) -> dict:
    if backend == "rule":
        ex = extract_rule(text, doc_id)
    elif backend == "llm":
        ex = extract_llm(text, doc_id)
    elif backend == "paste":
        if pasted is None:
            raise ValueError("paste 백엔드는 pasted JSON이 필요합니다")
        ex = load_pasted(pasted, text, doc_id)
    else:
        raise ValueError(backend)
    res = draft(check(ex, text))
    viol = audit(ex, text)
    return {"문서ID": doc_id, "원문": text, "추출": ex, "판정": res, "게이트위반": viol}


def run_all(data_dir: Path, out_dir: Path, backend: str = "rule") -> dict:
    ds = load_dataset(data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = {}
    for doc_id, d in ds["문서"].items():
        runs[doc_id] = run_doc(d["원문"], doc_id, backend)
    (out_dir / f"results_{backend}.json").write_text(
        json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    metrics = score({k: v["판정"] for k, v in runs.items()}, ds)
    report = render_report(metrics, backend)
    gate_lines = ["", "## 게이트 위반", ""]
    total = sum(len(r["게이트위반"]) for r in runs.values())
    if total == 0:
        gate_lines.append("없음 (규칙 백엔드는 원문 토큰만 값으로 쓰므로 위반이 없어야 정상)")
    else:
        for k, r in runs.items():
            for v in r["게이트위반"]:
                gate_lines.append(f"- {k} · {v['코드']} · {v['항목ID']} · {v['설명']}")
    report += "\n".join(gate_lines) + "\n"
    (out_dir / "평가리포트.md").write_text(report, encoding="utf-8")
    (out_dir / f"metrics_{backend}.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"runs": runs, "metrics": metrics, "report": report}


def render_table(result: dict) -> str:
    """누락 표시표(Markdown): 원문 값 / 표준명 후보 / 상태 / 근거 / 보완 질문 / 사람 확정."""
    res = result["판정"]
    lines = [f"### {result.get('문서ID') or ''} 누락 표시표", "", "```", result["원문"].rstrip(), "```", "",
             "| 항목 | 원문 값 | 표준명 후보 | 상태 | 근거 | 보완 질문 초안 | 사람 확정 |",
             "|---|---|---|---|---|---|---|"]
    for r in res["항목"]:
        lines.append(f"| {r['항목명']} | {r['원문값'] if r['원문값'] is not None else '(없음)'} | "
                     f"{r['표준명후보'] or ''} | {'확인 필요 · ' if r['확인필요'] else ''}{r['상태']} | {r['근거']} | "
                     f"{r['보완질문'] or ''} |  |")
    names = [r["항목명"] for r in res["항목"] if r["확인필요"]]
    lines += ["", f"확인 필요 항목: {', '.join(names) or '없음'}"]
    if result["게이트위반"]:
        lines += ["", "게이트 위반:"] + [f"- {v['코드']} {v['항목ID']}: {v['설명']}" for v in result["게이트위반"]]
    else:
        lines += ["", "게이트 위반: 없음"]
    return "\n".join(lines) + "\n"
