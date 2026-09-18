"""추출 백엔드: 규칙(오프라인) / 생성형 AI(선택, 가정) / ChatGPT 붙여넣기 로더.

세 경로 모두 같은 Extraction JSON 스키마를 낸다(TRD §2.5).
원칙: 원문에 없는 값을 만들지 않는다. 값이 없으면 None. 모호 표현은 그대로 둔다.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

from .catalog import FIELD_ORDER, FIELD_NAMES, VAGUE_DATE_TERMS, alias_index, items_by_id

# 판독 불가 후보 글자(스캔 손상): 숫자 자리에 O/o/l/I/S/B
DIGITISH = "0-9OolISB"
ID_RE = re.compile(rf"P-[{DIGITISH}]{{2}}(?![\w])")
SPEC_RE = re.compile(rf"(?<![\w-])(?:[{DIGITISH}]{{2,3}}A|[{DIGITISH}]{{1,2}}mm)(?![\w])")
ISO_RE = re.compile(rf"(?<![\w-])[{DIGITISH}]{{4}}-[{DIGITISH}]{{2}}-[{DIGITISH}]{{2}}(?![0-9A-Za-z-])")
KOR_DATE_RE = re.compile(r"(?<!\d)\d{1,2}월\s?\d{1,2}일")
SLASH_DATE_RE = re.compile(r"(?<![\d/])\d{1,2}/\d{1,2}(?![\d/])")
DOT_DATE_RE = re.compile(r"(?<![\d.])\d{1,2}\.\d{1,2}(?![\d.])")
UNIT_TOKENS = r"(?:개소|개|EA|ea|Ea|pcs|본|미터|메타|롤|roll|ROLL|Roll|m|M)"
QTY_UNIT_RE = re.compile(rf"(?<![\w-])([{DIGITISH},]+)\s*({UNIT_TOKENS})(?![\w])")
QTY_ONLY_RE = re.compile(rf"(?<![\w-])([{DIGITISH},]*[0-9][{DIGITISH},]*)(?![\w/.\-])")
UNIT_ONLY_RE = re.compile(rf"(?<![\w])({UNIT_TOKENS})(?![\w])")
DETAIL_TOKENS = r"(?:\d+동|지하\d+층|\d+층|옥상|정문|동측|서측|남측|북측|게이트|자재창고|야적장|하치장|기계실|입구)"
LOC_RE = re.compile(rf"([A-Z]현장)((?:\s?{DETAIL_TOKENS})*)")

_VAGUE_SORTED = sorted(VAGUE_DATE_TERMS, key=len, reverse=True)


def _item(field: str, value: str | None = None, span: tuple[int, int] | None = None,
          cand: str | None = None, basis: str | None = None, memo: str | None = None,
          cand_ids: list[str] | None = None) -> dict:
    return {
        "항목ID": field,
        "항목명": FIELD_NAMES[field],
        "원문값": value,
        "원문시작": span[0] if span else None,
        "원문끝": span[1] if span else None,
        "표준명후보": cand,
        "표준명근거": basis,
        "메모": memo,
        "후보품목": cand_ids or [],
    }


def _digits_only(token: str) -> bool:
    return bool(re.fullmatch(r"[0-9,]+", token))


class _Mask:
    def __init__(self, text: str):
        self.text = text
        self.used: list[tuple[int, int]] = []

    def free(self, s: int, e: int) -> bool:
        return all(e <= a or s >= b for a, b in self.used)

    def take(self, s: int, e: int) -> None:
        self.used.append((s, e))

    def search(self, rx: re.Pattern) -> re.Match | None:
        for m in rx.finditer(self.text):
            if self.free(m.start(), m.end()):
                self.take(m.start(), m.end())
                return m
        return None


def extract_rule(text: str, doc_id: str | None = None) -> dict:
    """규칙 기반 추출(오프라인 대체·테스트 기준). 원문에 있는 토큰만 값으로 쓴다."""
    mask = _Mask(text)
    items: dict[str, dict] = {}
    lex = items_by_id()

    # 1) 품목 ID
    m = mask.search(ID_RE)
    spec_m = mask.search(SPEC_RE)  # 2) 규격 (품목 후보 좁히기에 필요)
    spec_val = spec_m.group(0) if spec_m else None
    if m:
        tok = m.group(0)
        if _digits_only(tok[2:]):
            it = lex.get(tok)
            items["item_id"] = _item("item_id", tok, m.span(), it.display if it else None,
                                     "품목 ID 사전 일치" if it else "사전에 없는 품목 ID", None, [tok] if it else [])
        else:
            items["item_id"] = _item("item_id", tok, m.span(), None, None, f"판독 불가 후보: '{tok}'", [])
    else:
        found = None
        for alias, cands in alias_index():
            rx = re.compile(re.escape(alias), re.IGNORECASE)
            am = mask.search(rx)
            if am:
                found = (am, alias, cands)
                break
        if found:
            am, alias, cands = found
            if spec_val and _digits_only(spec_val[:-1] if spec_val.endswith("A") else spec_val[:-2]):
                narrowed = [c for c in cands if c.spec == spec_val]
                cands = narrowed or cands
            ids = [c.item_id for c in cands]
            if len(cands) == 1:
                cand_txt, basis = f"{cands[0].item_id} {cands[0].display}", "사전 별칭 일치 + 규격 일치 (사람 확정 필요)"
            else:
                cand_txt = " / ".join(f"{c.item_id} {c.display}" for c in cands) + " (규격 확인)"
                basis = "별칭 일치, 규격 미확인 → 병합 금지"
            items["item_id"] = _item("item_id", am.group(0), am.span(), cand_txt, basis, None, ids)
        else:
            items["item_id"] = _item("item_id")

    if spec_m:
        memo = None if _digits_only(spec_val[:-1] if spec_val.endswith("A") else spec_val[:-2]) else f"판독 불가 후보: '{spec_val}'"
        items["spec"] = _item("spec", spec_val, spec_m.span(), None, None, memo)
    else:
        items["spec"] = _item("spec")

    # 3) 희망일
    dm = None
    for rx in (ISO_RE, KOR_DATE_RE, SLASH_DATE_RE, DOT_DATE_RE):
        dm = mask.search(rx)
        if dm:
            break
    if dm:
        tok = dm.group(0)
        memo = None
        if rx is ISO_RE and not _digits_only(tok.replace("-", "")):
            memo = f"판독 불가 후보: '{tok}'"
        items["need_date"] = _item("need_date", tok, dm.span(), None, None, memo)
    else:
        vm = None
        for term in _VAGUE_SORTED:
            vm = mask.search(re.compile(re.escape(term)))
            if vm:
                break
        if vm:
            items["need_date"] = _item("need_date", vm.group(0), vm.span(), None, None,
                                       "모호 표현 — 날짜로 변환하지 않음(사람 확인)")
        else:
            items["need_date"] = _item("need_date")

    # 4) 배송 위치: 세부 위치가 붙은 현장 언급을 우선, 없으면 첫 현장명만
    best = None
    for lm in LOC_RE.finditer(text):
        has_detail = bool(lm.group(2).strip())
        if best is None or (has_detail and not best[1]):
            best = (lm, has_detail)
        if has_detail:
            break
    if best:
        lm, has_detail = best
        val = lm.group(0).rstrip()
        span = (lm.start(), lm.start() + len(val))
        mask.take(*span)
        items["delivery_location"] = _item("delivery_location", val, span, None, None,
                                           None if has_detail else "현장명만 있음 — 세부 위치 확인")
    else:
        items["delivery_location"] = _item("delivery_location")

    # 5) 수량·단위
    qm = mask.search(QTY_UNIT_RE)
    if qm:
        q, u = qm.group(1), qm.group(2)
        qs, qe = qm.start(1), qm.end(1)
        memo = None if _digits_only(q) else f"판독 불가 후보: '{q}'"
        items["qty"] = _item("qty", q, (qs, qe), None, None, memo)
        items["unit"] = _item("unit", u, (qm.start(2), qm.end(2)))
    else:
        qo = mask.search(QTY_ONLY_RE)
        if qo:
            q = qo.group(1)
            memo = None if _digits_only(q) else f"판독 불가 후보: '{q}'"
            items["qty"] = _item("qty", q, qo.span(1), None, None, memo)
        else:
            items["qty"] = _item("qty")
        um = mask.search(UNIT_ONLY_RE)
        if um:
            items["unit"] = _item("unit", um.group(1), um.span(1), None, None, "수량 없이 단위만 있음")
        else:
            items["unit"] = _item("unit", memo="단위 토큰 없음")

    # 6) 복수 품목 의심: 남은 영역에 품목 ID·수량+단위가 더 있으면 사람 확인 메모
    extra_ids = [m.group(0) for m in ID_RE.finditer(text) if mask.free(m.start(), m.end())]
    extra_qty = [m.group(0) for m in QTY_UNIT_RE.finditer(text) if mask.free(m.start(), m.end())]
    warnings: list[str] = []
    if extra_ids or extra_qty:
        note = f"복수 품목 의심(추가 토큰: {', '.join(extra_ids + extra_qty)}) — 이 PoC는 요청서당 1품목 기준, 사람 확인"
        items["item_id"]["메모"] = (items["item_id"]["메모"] + " · " if items["item_id"]["메모"] else "") + note
        warnings.append(note)

    return {"문서ID": doc_id, "백엔드": "rule", "항목": [items[f] for f in FIELD_ORDER], "경고": warnings}


# ---------------------------------------------------------------- 붙여넣기 로더

_KEY_ALIASES = {
    "field": "항목ID", "value": "원문값", "start": "원문시작", "end": "원문끝",
    "quote": "원문발췌", "excerpt": "원문발췌", "candidate": "표준명후보", "basis": "표준명근거", "note": "메모",
}
_NAME_TO_ID = {v: k for k, v in FIELD_NAMES.items()}
_NAME_TO_ID.update({"품목ID": "item_id", "품목": "item_id", "수량": "qty", "단위": "unit",
                    "희망일": "need_date", "희망납기": "need_date", "납기": "need_date",
                    "배송위치": "delivery_location", "배송지": "delivery_location", "규격": "spec"})


_NULLS = ("", "null", "None", "없음", "N/A", "n/a", "-", "—")
_QTY_UNIT_SPLIT = re.compile(rf"^([0-9][0-9,]*)\s*({UNIT_TOKENS})$")


def find_standalone(text: str, value: str) -> int:
    """value의 위치 중 앞뒤가 숫자·영문·한글이 아닌(독립 토큰) 첫 위치. 없으면 첫 위치, 없으면 -1.

    예: '2026-09-20까지 P-01 20개'에서 '20'은 날짜 안의 '20'이 아니라 수량 '20'을 가리켜야 한다.
    """
    if not value:
        return -1
    first, start = -1, 0
    while True:
        idx = text.find(value, start)
        if idx < 0:
            return first
        if first < 0:
            first = idx
        before = text[idx - 1] if idx > 0 else " "
        after = text[idx + len(value)] if idx + len(value) < len(text) else " "
        glued_before = _same_class(before, value[0]) or (before == "-" and value[0].isdigit())
        glued_after = _same_class(after, value[-1]) or (after == "-" and value[-1].isdigit())
        if not glued_before and not glued_after:
            return idx
        start = idx + 1


def _same_class(a: str, b: str) -> bool:
    """같은 글자 부류(숫자↔숫자, 한글↔한글, 영문↔영문)면 한 토큰의 일부로 본다. '20개'의 20과 개는 다른 부류."""
    if a.isdigit() and b.isdigit():
        return True
    if a.isascii() and a.isalpha() and b.isascii() and b.isalpha():
        return True
    return "가" <= a <= "힣" and "가" <= b <= "힣"


def strip_code_fence(s: str) -> str:
    """ChatGPT가 ```json ... ``` 으로 감싼 출력, 앞뒤 설명 문장을 벗겨 JSON 본문만 남긴다."""
    s = s.strip()
    m = re.search(r"```(?:json|JSON)?\s*(.*?)```", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 코드블록이 없으면 첫 '{' 또는 '['부터 마지막 '}' 또는 ']'까지
    starts = [i for i in (s.find("{"), s.find("[")) if i >= 0]
    ends = [i for i in (s.rfind("}"), s.rfind("]")) if i >= 0]
    if starts and ends and min(starts) < max(ends):
        return s[min(starts):max(ends) + 1]
    return s


def _norm_key(k: str) -> str:
    k = str(k).replace(" ", "")
    return _KEY_ALIASES.get(k, k)


def load_pasted(obj: dict | list | str, text: str, doc_id: str | None = None) -> dict:
    """ChatGPT가 낸 JSON(오프셋 없이 원문발췌만 있을 수 있음)을 표준 스키마로 정규화한다.

    - 원문시작/끝이 없으면 원문발췌(또는 원문값)를 독립 토큰 우선으로 찾아 복원. 못 찾으면 None → 게이트 G1.
    - 항목ID 대신 항목명(한글)·영문 키를 써도 받아준다. 값이 숫자형이면 문자열로 바꾼다.
    - 수량 칸에 '20개'처럼 단위가 붙어 오면 단위 칸이 비어 있을 때만 둘로 나눈다(둘 다 원문 토큰).
    - 정규화 과정에서 생긴 주의 사항은 '경고' 목록에 남긴다(값을 고치지는 않는다).
    """
    if isinstance(obj, str):
        obj = strip_code_fence(obj)
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError as e:
            raise ValueError(f"붙여넣은 내용이 JSON이 아닙니다: {e.msg} (줄 {e.lineno})") from e
    raw_items = obj["항목"] if isinstance(obj, dict) and "항목" in obj else obj
    if isinstance(raw_items, dict):  # {"품목 ID": {...}, ...} 형태
        raw_items = [{"항목ID": k, **(v if isinstance(v, dict) else {"원문값": v})}
                     for k, v in raw_items.items() if k not in ("문서ID", "사람확정", "확정")]
    if not isinstance(raw_items, list):
        raw_items = []
    by_field: dict[str, dict] = {}
    extra: dict = {}
    warnings: list[str] = []
    out_of_scope: list[dict] = []  # 필수 항목표 밖의 키 — 버리지 않고 남겨 게이트(G6)가 본다
    for r in raw_items:
        if not isinstance(r, dict):
            continue
        r = {_norm_key(k): v for k, v in r.items()}
        fid = r.get("항목ID")
        fid = _NAME_TO_ID.get(str(fid).replace(" ", ""), _NAME_TO_ID.get(fid, fid))
        if fid not in FIELD_ORDER:
            if fid not in (None, ""):
                out_of_scope.append({"키": str(fid), "값": r.get("원문값"), "메모": r.get("메모")})
                warnings.append(f"필수 항목표 밖의 항목 '{fid}' — 표에 넣지 않음")
            continue
        if fid in by_field:
            warnings.append(f"{FIELD_NAMES[fid]} 항목이 중복 출력됨 — 뒤의 값 사용")
        value = r.get("원문값")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(int(value)) if float(value).is_integer() else str(value)
        if value is not None and str(value).strip() in _NULLS:
            value = None
        if value is not None:
            value = str(value)
        s, e = r.get("원문시작"), r.get("원문끝")
        if value is not None and (not isinstance(s, int) or not isinstance(e, int) or text[s:e] != value):
            probe = r.get("원문발췌") or value
            idx = find_standalone(text, str(probe))
            if idx >= 0 and text[idx:idx + len(str(probe))] == value:
                s, e = idx, idx + len(str(probe))
            else:
                idx = find_standalone(text, value)
                s, e = (idx, idx + len(value)) if idx >= 0 else (None, None)
        item = _item(fid, value, (s, e) if s is not None else None, r.get("표준명후보"), r.get("표준명근거"), r.get("메모"))
        for k in ("사람확정", "확정", "최종", "최종확정"):
            if r.get(k) not in (None, ""):
                item["사람확정"] = r[k]
        by_field[fid] = item

    # 수량 칸에 단위가 붙어 온 경우: 단위 칸이 비어 있으면 둘로 나눈다(둘 다 원문 토큰이므로 추적 가능)
    q = by_field.get("qty")
    if q and q["원문값"] and q["원문시작"] is not None:
        m = _QTY_UNIT_SPLIT.match(q["원문값"])
        if m and (by_field.get("unit") is None or by_field["unit"]["원문값"] is None):
            base = q["원문시작"]
            by_field["qty"] = _item("qty", m.group(1), (base, base + len(m.group(1))), None, None, q["메모"])
            us = base + m.start(2)
            by_field["unit"] = _item("unit", m.group(2), (us, us + len(m.group(2))), None, None, "수량 칸에서 분리")
            warnings.append(f"수량 '{m.group(0)}'을 수량 '{m.group(1)}'과 단위 '{m.group(2)}'로 분리")

    for f in FIELD_ORDER:
        by_field.setdefault(f, _item(f))
    if not raw_items or all(by_field[f]["원문값"] is None for f in FIELD_ORDER):
        warnings.append("추출된 값이 하나도 없음 — 출력 형식 또는 원문 입력을 확인")
    if isinstance(obj, dict):
        for k in ("사람확정", "확정", "사람 확정", "최종확정"):
            if obj.get(k) not in (None, ""):
                extra["사람확정"] = obj[k]
        known = {"문서ID", "항목", "사람확정", "확정", "사람 확정", "최종확정"}
        for k, v in obj.items():
            if k not in known and v not in (None, ""):
                out_of_scope.append({"키": str(k), "값": v if isinstance(v, (str, int, float)) else json.dumps(v, ensure_ascii=False), "메모": None})
                warnings.append(f"문서 수준의 항목표 밖 키 '{k}' — 표에 넣지 않음")
    if out_of_scope:
        extra["범위밖"] = out_of_scope
    return {"문서ID": doc_id or (obj.get("문서ID") if isinstance(obj, dict) else None),
            "백엔드": "paste", "항목": [by_field[f] for f in FIELD_ORDER], "경고": warnings, **extra}


# ---------------------------------------------------------------- 생성형 AI 백엔드 (가정)

def extract_llm(text: str, doc_id: str | None = None, prompts_dir: Path | None = None,
                model: str | None = None) -> dict:
    """OPENAI_API_KEY가 있을 때만 동작. 프롬프트 팩(prompts/)을 그대로 사용해 붙여넣기 경로와 동일하게 처리한다."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY가 없습니다. --backend rule 또는 check-paste를 사용하세요.")
    prompts_dir = prompts_dir or Path(__file__).resolve().parents[2] / "prompts"
    system = (prompts_dir / "00_시스템규칙.md").read_text(encoding="utf-8")
    user = (prompts_dir / "01_추출.md").read_text(encoding="utf-8").replace("{{요청서}}", text)
    body = {
        "model": model or os.environ.get("POC_D04_MODEL", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    content = data["choices"][0]["message"]["content"]
    out = load_pasted(content, text, doc_id)
    out["백엔드"] = "llm"
    out["원본응답"] = content
    return out
