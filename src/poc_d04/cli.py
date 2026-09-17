"""명령줄: gen / run / check-paste / eval / workbook / examples / all"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA, OUT, EXAMPLES = ROOT / "data", ROOT / "out", ROOT / "examples"


def cmd_gen(_a):
    from .data_gen import build_dataset
    d = build_dataset(DATA)
    print(f"생성: 문서 {len(d['docs'])}건, 정답 {len(d['truth'])}행 → {DATA}")


def cmd_run(a):
    from .pipeline import run_all
    r = run_all(DATA, OUT, a.backend)
    m = r["metrics"]["전체"]
    print(f"[{a.backend}] 탐지율 {m['누락 탐지율']:.3f} 오탐 {m['잘못된 누락 경고 비율']:.3f} "
          f"중요오류 {m['중요 오류']} 추적 {m['원문 추적 가능 비율']:.3f} → {OUT/'평가리포트.md'}")


def cmd_check_paste(a):
    from .data_gen import load_dataset
    from .pipeline import render_table, run_doc
    if a.text:
        text, doc_id = Path(a.text).read_text(encoding="utf-8"), a.doc
    else:
        ds = load_dataset(DATA)
        text, doc_id = ds["문서"][a.doc]["원문"], a.doc
    try:
        pasted = json.loads(Path(a.json).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"JSON을 읽을 수 없습니다: {e.msg} (줄 {e.lineno}, 열 {e.colno}). ChatGPT 출력에서 코드 블록 기호(```)와 설명 문장을 지우고 다시 저장하세요.", file=sys.stderr)
        return 3
    r = run_doc(text, doc_id, "paste", pasted)
    print(render_table(r))
    for w in r["추출"].get("경고", []):
        print(f"경고: {w}")
    if a.truth and not a.text:
        from .evaluate import score
        ds = load_dataset(DATA)
        m = score({doc_id: r["판정"]}, ds)["전체"]
        print(f"정답 대조: 탐지 {m['탐지']}/{m['정답확인필요']} · 오탐 {m['오탐']} · 중요오류 {m['중요 오류']} · 상태 정확도 {m['상태 정확도']:.2f}")
        for x in m["미스"]:
            print(f"  - {x['항목']}: 정답 {x['정답']} / 예측 {x['예측']} ({x['정답사유']})")
    return 1 if r["게이트위반"] else 0


def cmd_eval(_a):
    from .data_gen import load_dataset
    from .evaluate import passes, render_report, score
    p = OUT / "results_rule.json"
    if not p.exists():
        print("먼저 run을 실행하세요", file=sys.stderr)
        return 1
    runs = json.loads(p.read_text(encoding="utf-8"))
    ds = load_dataset(DATA)
    metrics = score({k: v["판정"] for k, v in runs.items()}, ds)
    print(render_report(metrics, "rule"))
    return 0 if all(passes(metrics).values()) else 2


def cmd_workbook(_a):
    from .workbook import build_workbook
    p = build_workbook(OUT / "D04_누락표시표_활동지.xlsx", DATA, OUT)
    print(f"활동지 → {p}")


def cmd_examples(_a):
    from .examples import write_all
    for p in write_all(DATA, EXAMPLES):
        print(f"예시 → {p}")


def cmd_all(a):
    cmd_gen(a)
    a.backend = "rule"
    cmd_run(a)
    cmd_workbook(a)
    cmd_examples(a)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="poc_d04", description="D사 시연용 PoC — 구매 요청서 누락 확인")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gen", help="data/ 생성").set_defaults(fn=cmd_gen)
    r = sub.add_parser("run", help="전 표본 추출→판정→게이트→평가")
    r.add_argument("--backend", choices=["rule", "llm"], default="rule")
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("check-paste", help="ChatGPT 출력 JSON 검사")
    c.add_argument("--doc", required=True, help="문서ID (예: D04-13) 또는 --text와 함께 임의 ID")
    c.add_argument("--json", required=True, help="붙여넣은 JSON 파일")
    c.add_argument("--text", help="정답표 밖의 요청서 텍스트 파일")
    c.add_argument("--truth", action="store_true", help="정답표와 대조")
    c.set_defaults(fn=cmd_check_paste)
    sub.add_parser("eval", help="out/results_rule.json 재평가").set_defaults(fn=cmd_eval)
    sub.add_parser("workbook", help="xlsx 활동지").set_defaults(fn=cmd_workbook)
    sub.add_parser("examples", help="실패 장면·오프라인 캡처").set_defaults(fn=cmd_examples)
    sub.add_parser("all", help="gen→run→workbook→examples").set_defaults(fn=cmd_all)
    a = p.parse_args(argv)
    rc = a.fn(a)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
