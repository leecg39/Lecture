"""정답표 대조 지표 (기획안 §5-3). 항목 단위로 계산한다.

- 누락 탐지율 = 정답 확인필요 ∧ 예측 확인필요 / 정답 확인필요
- 잘못된 누락 경고 비율 = 정답 충족 ∧ 예측 확인필요 / 예측 확인필요
- 중요 오류 = 정답 확인필요 ∧ 예측 충족 ∧ 항목 ∈ {품목, 수량, 단위, 희망일}
- 원문 추적 가능 비율 = 원문값 있는 예측 중 오프셋 유효·텍스트 일치
"""
from __future__ import annotations

from collections import defaultdict

from .catalog import CRITICAL_FIELDS, FIELD_NAMES

TARGETS = {
    "누락 탐지율": (">=", 0.95),
    "잘못된 누락 경고 비율": ("<=", 0.10),
    "중요 오류": ("==", 0),
    "원문 추적 가능 비율": (">=", 1.00),
}


def _empty():
    return {"정답확인필요": 0, "탐지": 0, "예측확인필요": 0, "오탐": 0, "중요오류": 0,
            "추출값": 0, "추적가능": 0, "항목수": 0, "상태일치": 0, "미스": []}


def _ratio(a: int, b: int) -> float | None:
    return None if b == 0 else a / b


def _finalize(b: dict) -> dict:
    return {
        "항목수": b["항목수"],
        "누락 탐지율": _ratio(b["탐지"], b["정답확인필요"]),
        "잘못된 누락 경고 비율": _ratio(b["오탐"], b["예측확인필요"]),
        "중요 오류": b["중요오류"],
        "원문 추적 가능 비율": _ratio(b["추적가능"], b["추출값"]),
        "상태 정확도": _ratio(b["상태일치"], b["항목수"]),
        "정답확인필요": b["정답확인필요"], "예측확인필요": b["예측확인필요"], "탐지": b["탐지"], "오탐": b["오탐"],
        "미스": b["미스"],
    }


def score(results: dict[str, dict], dataset: dict) -> dict:
    """results: 문서ID → rules.check() 결과. dataset: data_gen.load_dataset()."""
    truth = defaultdict(dict)
    meta = {}
    for row in dataset["정답"]:
        truth[row["문서ID"]][row["항목ID"]] = row
        meta[row["문서ID"]] = (row["유형"], row["버전"])
    buckets: dict[str, dict] = defaultdict(_empty)

    for doc_id, res in results.items():
        if doc_id not in truth:
            continue
        kind, ver = meta[doc_id]
        text = dataset["문서"][doc_id]["원문"]
        for r in res["항목"]:
            f = r["항목ID"]
            t = truth[doc_id][f]
            flag_t, flag_p = t["정답상태"] != "충족", r["상태"] != "충족"
            for key in ("전체", f"유형:{kind}", f"버전:{ver}", f"항목:{FIELD_NAMES[f]}"):
                b = buckets[key]
                b["항목수"] += 1
                b["상태일치"] += int(t["정답상태"] == r["상태"])
                b["정답확인필요"] += int(flag_t)
                b["예측확인필요"] += int(flag_p)
                b["탐지"] += int(flag_t and flag_p)
                b["오탐"] += int((not flag_t) and flag_p)
                crit = flag_t and not flag_p and f in CRITICAL_FIELDS
                b["중요오류"] += int(crit)
                if r.get("원문값") is not None:
                    b["추출값"] += 1
                    s, e = r.get("원문시작"), r.get("원문끝")
                    ok = s is not None and e is not None and text[s:e] == str(r["원문값"])
                    b["추적가능"] += int(ok)
                if t["정답상태"] != r["상태"] and key == "전체":
                    b["미스"].append({"문서ID": doc_id, "항목": FIELD_NAMES[f], "정답": t["정답상태"],
                                    "예측": r["상태"], "정답사유": t["사유"], "예측근거": r["근거"], "중요오류": crit})
    out = {k: _finalize(v) for k, v in buckets.items()}
    out["_문서수"] = len([d for d in results if d in truth])
    return out


def passes(metrics: dict) -> dict[str, bool]:
    m = metrics["전체"]
    res = {}
    for name, (op, tgt) in TARGETS.items():
        v = m[name]
        if v is None:
            res[name] = False
        elif op == ">=":
            res[name] = v >= tgt
        elif op == "<=":
            res[name] = v <= tgt
        else:
            res[name] = v == tgt
    return res


def _pct(v):
    return "—" if v is None else f"{v*100:.1f}%"


def render_report(metrics: dict, backend: str) -> str:
    m = metrics["전체"]
    p = passes(metrics)
    lines = [
        "# 평가 리포트 — 구매 요청서 누락 확인 PoC",
        "",
        f"- 백엔드: `{backend}` · 문서 {metrics['_문서수']}건 · 항목 {m['항목수']}개 (교육용 가상 표본, 실측 아님)",
        f"- 기준: 기획안 §5-3 교육용 목표. 소표본 결과이며 운영 무오류를 뜻하지 않는다.",
        "",
        "## 전체",
        "",
        "| 지표 | 값 | 목표 | 판정 |",
        "|---|---|---|---|",
        f"| 누락 탐지율 | {_pct(m['누락 탐지율'])} ({m['탐지']}/{m['정답확인필요']}) | ≥ 95% | {'통과' if p['누락 탐지율'] else '미달'} |",
        f"| 잘못된 누락 경고 비율 | {_pct(m['잘못된 누락 경고 비율'])} ({m['오탐']}/{m['예측확인필요']}) | ≤ 10% | {'통과' if p['잘못된 누락 경고 비율'] else '미달'} |",
        f"| 중요 오류 | {m['중요 오류']}건 | 0건 | {'통과' if p['중요 오류'] else '미달'} |",
        f"| 원문 추적 가능 비율 | {_pct(m['원문 추적 가능 비율'])} | 100% | {'통과' if p['원문 추적 가능 비율'] else '미달'} |",
        f"| 상태 정확도(보조) | {_pct(m['상태 정확도'])} | — | — |",
        "",
        "## 유형·버전·항목별",
        "",
        "| 구분 | 항목수 | 탐지율 | 오탐 비율 | 중요 오류 | 추적율 | 상태 정확도 |",
        "|---|---|---|---|---|---|---|",
    ]
    for k in sorted(k for k in metrics if k.startswith(("유형:", "버전:", "항목:"))):
        b = metrics[k]
        lines.append(f"| {k} | {b['항목수']} | {_pct(b['누락 탐지율'])} | {_pct(b['잘못된 누락 경고 비율'])} | "
                     f"{b['중요 오류']} | {_pct(b['원문 추적 가능 비율'])} | {_pct(b['상태 정확도'])} |")
    lines += ["", "## 정답과 다른 판정", ""]
    if not m["미스"]:
        lines.append("없음")
    else:
        lines += ["| 문서 | 항목 | 정답 | 예측 | 정답 사유 | 예측 근거 | 중요 |", "|---|---|---|---|---|---|---|"]
        for x in m["미스"]:
            lines.append(f"| {x['문서ID']} | {x['항목']} | {x['정답']} | {x['예측']} | {x['정답사유']} | {x['예측근거']} | {'Y' if x['중요오류'] else ''} |")
    lines += ["", "## 계속·수정·중단 판단 (기획안 §5-4 적용 예시)", "",
              "- 계속: 네 지표가 모두 목표를 지키고, 정답표 검토자·갱신 담당이 정해져 있다.",
              "- 수정: 시간은 줄어도 중요 오류가 있거나 특정 유형(예: 저품질 스캔)의 탐지율이 떨어진다 → 범위를 좁혀 재시험.",
              "- 중단·보류: 검토 비용으로 총시간이 늘거나, 자료·정답 검토·운영 담당을 확보할 수 없다.", ""]
    return "\n".join(lines)
