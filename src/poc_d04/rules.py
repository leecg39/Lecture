"""규칙 축: 필수 항목표 대조 판정 (AI 아님, 결정적).

상태: 충족 / 누락 / 모호 / 불일치.  확인필요 = 상태 != 충족.
"""
from __future__ import annotations

import re
from datetime import date

from .catalog import BASE_DATE, FIELD_NAMES, FIELD_ORDER, VAGUE_DATE_TERMS, items_by_id, normalize_unit
from .extract import LOC_RE

_ID = re.compile(r"^P-\d{2}$")
_UNREADABLE = "판독 불가"


def parse_date(token: str, base: str = BASE_DATE) -> date | None:
    """특정 날짜 표현만 date로. 모호 표현·판독 불가는 None."""
    y = int(base[:4])
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", token)
    if m:
        return _safe_date(int(m[1]), int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d{1,2})월\s?(\d{1,2})일", token)
    if m:
        return _safe_date(y, int(m[1]), int(m[2]))
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})", token)
    if m:
        return _safe_date(y, int(m[1]), int(m[2]))
    return None


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _get(extraction: dict, field: str) -> dict:
    for it in extraction["항목"]:
        if it["항목ID"] == field:
            return it
    return {"항목ID": field, "원문값": None, "메모": None, "표준명후보": None, "후보품목": []}


def _as_id(val) -> str | None:
    """'p-01', 'P–01'(전각 대시) 같은 표기를 사전 키로 정규화. ID 형식이 아니면 None."""
    if val is None:
        return None
    v = str(val).strip().upper().replace("–", "-").replace("—", "-")
    return v if _ID.match(v) else None


def _candidates(item: dict):
    lex = items_by_id()
    val = _as_id(item.get("원문값"))
    if val and val in lex:
        return [lex[val]]
    ids = item.get("후보품목") or []
    if not ids and item.get("표준명후보"):
        ids = re.findall(r"P-\d{2}", str(item["표준명후보"]))
    return [lex[i] for i in ids if i in lex]


def _unreadable(item: dict) -> bool:
    return bool(item.get("메모")) and _UNREADABLE in str(item["메모"])


def check(extraction: dict, text: str, base_date: str = BASE_DATE) -> dict:
    lex = items_by_id()
    out: list[dict] = []
    item = _get(extraction, "item_id")
    cands = _candidates(item)
    vid = _as_id(item.get("원문값"))
    explicit = bool(vid and vid in lex)

    def push(field: str, status: str, basis: str, src: dict, cand: str | None = None) -> None:
        s, e = src.get("원문시작"), src.get("원문끝")
        out.append({
            "항목ID": field,
            "항목명": FIELD_NAMES[field],
            "상태": status,
            "확인필요": status != "충족",
            "원문값": src.get("원문값"),
            "원문시작": s, "원문끝": e,
            "원문발췌": text[s:e] if s is not None and e is not None else None,
            "표준명후보": cand if cand is not None else src.get("표준명후보"),
            "근거": basis,
            "보완질문": None,
            "역할": {"AI제안": _ai_line(src), "규칙": basis, "사람확정": ""},
        })

    # 품목 ID
    v = item.get("원문값")
    if v is None:
        push("item_id", "누락", "품목 ID·품명 모두 없음", item)
    elif _unreadable(item):
        push("item_id", "모호", "글자 판독 불가 — 원문 재확인", item)
    elif vid:
        if vid in lex:
            push("item_id", "충족", f"사전 품목 {lex[vid].display}", item, lex[vid].display)
        else:
            push("item_id", "불일치", "사전에 없는 품목 ID", item)
    else:
        ids = ", ".join(c.item_id for c in cands) or "없음"
        push("item_id", "모호", f"별칭만 있음 → 표준명 후보({ids}), 사람 확정 필요", item)

    # 수량
    q = _get(extraction, "qty")
    qv = q.get("원문값")
    if qv is None:
        push("qty", "누락", "수량 없음", q)
    elif _unreadable(q) or not re.fullmatch(r"[0-9,]+", str(qv)):
        push("qty", "모호", "글자 판독 불가 — 원문 재확인", q)
    elif int(str(qv).replace(",", "")) <= 0:
        push("qty", "불일치", "수량이 0 이하", q)
    else:
        push("qty", "충족", "양의 정수", q)

    # 단위
    u = _get(extraction, "unit")
    uv = u.get("원문값")
    if uv is None:
        push("unit", "누락", "단위 없음", u)
    else:
        std = normalize_unit(str(uv))
        units = {c.unit for c in cands}
        if not cands:
            push("unit", "모호", "품목 미확정으로 표준 단위 비교 불가", u)
        elif len(units) > 1:
            push("unit", "모호", "후보 품목의 표준 단위가 서로 다름", u)
        else:
            want = next(iter(units))
            if std == want:
                push("unit", "충족", "표준 단위와 일치", u, want)
            else:
                push("unit", "불일치", f"표준 단위 '{want}'와 다름", u, want)

    # 희망일
    d = _get(extraction, "need_date")
    dv = d.get("원문값")
    if dv is None:
        push("need_date", "누락", "희망일 없음", d)
    elif _unreadable(d):
        push("need_date", "모호", "글자 판독 불가 — 원문 재확인", d)
    elif any(t in str(dv) for t in VAGUE_DATE_TERMS) and parse_date(str(dv)) is None:
        push("need_date", "모호", f"모호 표현 '{dv}' → 날짜로 단정하지 않음", d)
    else:
        pd = parse_date(str(dv), base_date)
        if pd is None:
            push("need_date", "모호", "날짜 형식으로 읽을 수 없음", d)
        elif pd < date.fromisoformat(base_date):
            push("need_date", "불일치", f"기준일 {base_date} 이전 날짜", d, pd.isoformat())
        else:
            push("need_date", "충족", "특정 날짜", d, pd.isoformat())

    # 배송 위치
    loc = _get(extraction, "delivery_location")
    lv = loc.get("원문값")
    if lv is None:
        push("delivery_location", "누락", "배송 위치 없음", loc)
    else:
        m = LOC_RE.fullmatch(str(lv).strip())
        if m and m.group(2).strip():
            push("delivery_location", "충족", "현장명 + 세부 위치", loc)
        elif m:
            push("delivery_location", "모호", "현장명만 있고 세부 위치 없음", loc)
        else:
            push("delivery_location", "모호", "현장명 형식이 아님 — 확인", loc)

    # 규격
    sp = _get(extraction, "spec")
    sv = sp.get("원문값")
    if sv is not None:
        if _unreadable(sp):
            push("spec", "모호", "글자 판독 불가 — 원문 재확인", sp)
        elif explicit and lex[vid].spec != sv:
            push("spec", "불일치", f"품목 ID 사전 규격 '{lex[vid].spec}'과 다름", sp, lex[vid].spec)
        else:
            push("spec", "충족", "규격 원문 존재", sp)
    else:
        if explicit:
            push("spec", "충족", f"품목 ID 확정 → 사전 규격 '{lex[vid].spec}' 적용(원문값 없음)", sp, lex[vid].spec)
        else:
            push("spec", "누락", "규격 없음(품목 ID 미확정)", sp)

    out.sort(key=lambda r: FIELD_ORDER.index(r["항목ID"]))
    return {"문서ID": extraction.get("문서ID"), "백엔드": extraction.get("백엔드"), "항목": out,
            "확인필요항목": [r["항목ID"] for r in out if r["확인필요"]]}


def _ai_line(src: dict) -> str:
    v = src.get("원문값")
    parts = [f"원문 '{v}'" if v is not None else "값 없음"]
    if src.get("표준명후보"):
        parts.append(f"후보 {src['표준명후보']}")
    if src.get("메모"):
        parts.append(str(src["메모"]))
    return " · ".join(parts)
