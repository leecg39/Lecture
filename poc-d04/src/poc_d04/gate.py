"""게이트 감사 (기획안 §3-2). 추출 결과가 원문과 규칙을 벗어났는지 결정적으로 검사한다.

G1 원문 없는 값 / 원문 위치 불일치
G2 모호 표현을 날짜로 단정
G3 별칭만으로 규격(품목) 병합
G4 원문 없는 규격 채움
G5 사람 확정 칸을 AI가 채움
"""
from __future__ import annotations

import re

from .catalog import LEXICON, VAGUE_DATE_TERMS
from .extract import SPEC_RE
from .rules import parse_date

_DATE_LIKE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}월\s?\d{1,2}일|\b\d{1,2}[/.]\d{1,2}\b")
_ID = re.compile(r"P-\d{2}")
_SPEC_TOKEN = re.compile(r"\b\d{2,3}A\b|\b\d{1,2}mm\b")

GATE_TEXT = {
    "G1": "값이 없으면 비우거나 '확인 필요'. 원문 없는 값을 채우지 않는다.",
    "G2": "'다음 주' 같은 모호 표현을 날짜로 단정하지 않는다.",
    "G3": "별칭이 비슷하다는 이유만으로 다른 규격을 합치지 않는다.",
    "G4": "원문에 없는 규격을 채우지 않는다.",
    "G5": "최종 확정은 사람이 한다. AI 출력은 '제안' 열에만 둔다.",
}


def _v(code: str, field: str | None, detail: str) -> dict:
    return {"코드": code, "게이트": GATE_TEXT[code], "항목ID": field, "설명": detail}


def _in_text(text: str, value: str) -> bool:
    return value is not None and str(value) in text


def audit(extraction: dict, text: str) -> list[dict]:
    viol: list[dict] = []
    vague_in_text = [t for t in VAGUE_DATE_TERMS if t in text]
    spec_in_text = SPEC_RE.search(text) is not None

    for it in extraction["항목"]:
        f, val = it["항목ID"], it.get("원문값")
        s, e = it.get("원문시작"), it.get("원문끝")

        # G4: 규격을 원문 없이 채움 (G1보다 먼저, 별도 보고)
        if f == "spec" and val is not None and not _in_text(text, val):
            viol.append(_v("G4", f, f"규격 '{val}'이 원문에 없음"))
            continue

        # G2: 모호 표현을 날짜로 단정
        if f == "need_date":
            texts = [str(x) for x in (val, it.get("표준명후보"), it.get("메모")) if x]
            fabricated = next(
                (dm for tx in texts for dm in _DATE_LIKE.findall(tx)
                 if not _in_text(text, dm) and parse_date(dm) is not None), None)
            if fabricated:
                why = f"'{vague_in_text[0]}'" if vague_in_text else "원문"
                viol.append(_v("G2", f, f"{why}을(를) 날짜 '{fabricated}'로 단정 (원문에 없음)"))
                continue

        # G1: 원문 위치·값 추적
        if val is not None:
            if s is None or e is None:
                viol.append(_v("G1", f, f"'{val}'에 원문 위치가 없음"))
            elif text[s:e] != str(val):
                viol.append(_v("G1", f, f"원문 위치 [{s}:{e}]='{text[s:e]}' ≠ 값 '{val}'"))

        # G3: 별칭 병합
        if f == "item_id" and val is not None and not _ID.fullmatch(str(val).upper()):
            alias_cands = [x for x in LEXICON if str(val) in x.aliases or str(val) == x.name]
            cand_txt = str(it.get("표준명후보") or "")
            single = set(_ID.findall(cand_txt))
            cand_specs = {s for s in _SPEC_TOKEN.findall(cand_txt) if s not in text}
            if len(alias_cands) > 1 and not spec_in_text:
                if len(single) == 1:
                    viol.append(_v("G3", f, f"별칭 '{val}'은 {len(alias_cands)}개 품목에 해당하나 규격 없이 {single.pop()}로 확정"))
                elif len(cand_specs) == 1 and len({x.spec for x in alias_cands}) > 1:
                    viol.append(_v("G3", f, f"별칭 '{val}'의 후보에 원문에 없는 규격 '{cand_specs.pop()}'을 붙여 한 품목으로 좁힘"))

        # G5: 사람 확정 칸 선점
        if it.get("사람확정") not in (None, ""):
            viol.append(_v("G5", f, f"사람 확정 칸에 AI 값 '{it['사람확정']}'"))

    if extraction.get("사람확정") not in (None, ""):
        viol.append(_v("G5", None, "문서 수준 사람 확정 칸이 채워져 있음"))
    return viol
