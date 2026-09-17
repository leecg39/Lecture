"""가상 구매 요청서 30건 × (읽기 쉬운 / 저품질 스캔) + 정답표 생성.

정답은 추출기를 돌려서 만들지 않고 스펙에서 독립적으로 도출한다(평가의 기준이므로).
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .catalog import (
    FIELD_ORDER, FIELD_NAMES, LEXICON, VAGUE_DATE_TERMS, items_by_id, normalize_unit, write_catalog,
)

Segment = tuple[str | None, str]  # (field or None, text)


@dataclass(frozen=True)
class Spec:
    doc_no: int
    kind: str  # 정상 / 필수누락 / 모호표현 / 단위불일치 / 배송조건누락
    template: int
    requester: str
    site: str
    detail: str | None
    item_ref: str  # "P-01" 또는 별칭
    spec: str | None
    qty: str | None
    unit: str | None
    date: str | None
    location_mode: str  # full / site_only / none
    note: str
    scan_fields: tuple[str, ...]
    remark: str = ""

    @property
    def doc_id(self) -> str:
        return f"D04-{self.doc_no:02d}"


ID_RE = re.compile(r"^P-\d{2}$")

# ---------------------------------------------------------------- 스펙 30건
S = Spec
SPECS: list[Spec] = [
    # 정상 (1–6)
    S(1, "정상", 1, "김현장", "A현장", "3동 지하1층 자재창고", "P-01", "50A", "20", "개", "2026-09-25", "full", "현장 소장 확인 완료", ("qty",)),
    S(2, "정상", 2, "박지원", "B현장", "1동 1층 야적장", "P-03", "50A", "40", "본", "9월 26일", "full", "기존 발주분과 별도 건입니다", ("qty",)),
    S(3, "정상", 3, "이자재", "C현장", "정문 게이트 하치장", "P-09", "50A", "120", "m", "9/28", "full", "우천 시 실내 보관 요청", ("spec",)),
    S(4, "정상", 1, "최공무", "A현장", "2동 옥상 기계실", "P-07", "50A", "15", "EA", "2026-09-30", "full", "기계실 배관 교체용", ("item_id",)),
    S(5, "정상", 4, "정설비", "B현장", "동측 게이트 자재창고", "P-10", None, "10", "롤", "2026-09-24", "full", "소모품", ("qty",),
      "규격 미기재이나 품목 ID 확정 → 사전 규격 적용(원문값 없음)"),
    S(6, "정상", 2, "한구매", "C현장", "1동 1층 야적장", "P-05", "50A", "30", "본", "10월 2일", "full", "야적장 입구에 내려 주세요", ("qty",)),
    # 필수 누락 (7–12)
    S(7, "필수누락", 1, "김현장", "A현장", "3동 지하1층 자재창고", "P-02", "100A", None, "개", "2026-09-26", "full", "수량은 확인 후 회신", ("spec",),
      "수량 누락"),
    S(8, "필수누락", 3, "박지원", "B현장", "1동 1층 야적장", "볼밸브", None, "12", "개", "2026-09-29", "full", "기존 것과 같은 걸로", ("qty",),
      "별칭만 있음(P-01/P-02 후보) + 규격 누락 → 병합 금지"),
    S(9, "필수누락", 2, "이자재", "C현장", "정문 게이트 하치장", "P-04", "100A", "25", None, "9월 30일", "full", "하치장 진입 시 안전관리자 연락", ("qty",),
      "단위 누락"),
    S(10, "필수누락", 4, "최공무", "A현장", "2동 옥상 기계실", "P-03", "50A", "40", "본", None, "full", "기계실 반입", ("spec",),
      "희망일 누락"),
    S(11, "필수누락", 1, "정설비", "B현장", "동측 게이트 자재창고", "P-09", None, None, None, "2026-10-01", "full", "길이는 도면 확인 후 알려드림", ("need_date",),
      "수량·단위 누락"),
    S(12, "필수누락", 6, "한구매", "C현장", None, "PVC관", None, "30", "본", None, "none", "", (),
      "별칭만·규격 누락·희망일 누락·배송 위치 누락(스캔 손상 없음: 원문이 이미 결함)"),
    # 모호 표현 (13–18) — 13은 기획안 시연 사례
    S(13, "모호표현", 5, "김현장", "A현장", None, "P-01", None, "20", "개", "다음 주", "site_only", "", ("qty",),
      "기획안 §4-6 시연 사례. 희망일·배송 위치 확인 대상"),
    S(14, "모호표현", 1, "박지원", "B현장", "1동 1층 야적장", "P-07", "50A", "15", "개", "ASAP", "full", "협력사 대기 중", ("qty",)),
    S(15, "모호표현", 2, "이자재", "C현장", "정문 게이트 하치장", "엘보", "50A", "20", "개", "이번 달 안", "full", "각도는 도면 참조", ("spec",),
      "별칭 '엘보' → P-07/P-08 후보 2개(각도 미확정)"),
    S(16, "모호표현", 3, "최공무", "A현장", "2동 옥상 기계실", "P-05", "50A", "30", "본", "빨리", "full", "공정 지연 중", ("qty",)),
    S(17, "모호표현", 4, "정설비", "B현장", "동측 게이트 자재창고", "P-10", "12mm", "6", "롤", "내주 초", "full", "", ("spec",)),
    S(18, "모호표현", 2, "한구매", "C현장", "1동 1층 야적장", "백관", "100A", "10", "본", "급합니다", "full", "기존 라인 연결용", ("qty",),
      "별칭 '백관' + 규격 100A → 표준명 후보 P-06 단일이지만 사람 확정 필요"),
    # 단위 불일치 (19–24)
    S(19, "단위불일치", 1, "김현장", "A현장", "3동 지하1층 자재창고", "P-03", "50A", "40", "m", "2026-09-27", "full", "", ("qty",),
      "표준 단위 '본'인데 'm'"),
    S(20, "단위불일치", 2, "박지원", "B현장", "1동 1층 야적장", "P-09", "50A", "30", "개", "9월 29일", "full", "", ("spec",),
      "표준 단위 'm'인데 '개'"),
    S(21, "단위불일치", 3, "이자재", "C현장", "정문 게이트 하치장", "P-10", "12mm", "5", "개", "9/30", "full", "", ("spec",),
      "표준 단위 '롤'인데 '개'"),
    S(22, "단위불일치", 4, "최공무", "A현장", "2동 옥상 기계실", "P-01", "50A", "20", "본", "2026-09-28", "full", "", ("qty",),
      "표준 단위 '개'인데 '본'"),
    S(23, "단위불일치", 1, "정설비", "B현장", "동측 게이트 자재창고", "P-07", "50A", "15", "본", "2026-10-02", "full", "", ("item_id",),
      "표준 단위 '개'인데 '본'"),
    S(24, "단위불일치", 2, "한구매", "C현장", "1동 1층 야적장", "P-06", "100A", "12", "EA", "10월 5일", "full", "", ("qty",),
      "표준 단위 '본'인데 'EA'(=개)"),
    # 배송조건 누락 (25–30)
    S(25, "배송조건누락", 1, "김현장", "A현장", None, "P-01", "50A", "20", "개", "2026-09-25", "site_only", "", ("qty",),
      "현장명만"),
    S(26, "배송조건누락", 6, "박지원", "B현장", None, "P-03", "50A", "40", "본", "9월 26일", "none", "야적 가능", ("qty",),
      "배송 위치 없음"),
    S(27, "배송조건누락", 3, "이자재", "C현장", None, "P-09", "50A", "60", "m", "9/29", "site_only", "", ("spec",),
      "현장명만"),
    S(28, "배송조건누락", 6, "최공무", "A현장", None, "P-10", "12mm", "8", "롤", "2026-09-30", "none", "", ("spec",),
      "배송 위치 없음"),
    S(29, "배송조건누락", 2, "정설비", "B현장", None, "P-05", "50A", "20", "본", "2026-10-01", "site_only", "", ("qty",),
      "현장명만"),
    S(30, "배송조건누락", 3, "한구매", "C현장", None, "P-02", "100A", "12", "개", "10월 6일", "none", "", ("item_id",),
      "배송 위치 없음"),
]

# ---------------------------------------------------------------- 렌더링


def _seg(field: str | None, text: str | None) -> list[Segment]:
    return [] if text is None else [(field, text)]


def _lit(text: str) -> list[Segment]:
    return [(None, text)]


def _loc_text(spec: Spec, site: str) -> str | None:
    if spec.location_mode == "none":
        return None
    if spec.location_mode == "site_only" or not spec.detail:
        return site
    return f"{site} {spec.detail}"


def build_segments(spec: Spec, v: dict[str, str | None]) -> list[Segment]:
    """v: 필드값(스캔이면 손상된 값). 템플릿마다 없는 값의 줄·라벨은 생략한다."""
    r, site, note = spec.requester, spec.site, spec.note
    item, sp, qty, unit, date, loc = (v["item_id"], v["spec"], v["qty"], v["unit"], v["need_date"], v["delivery_location"])
    t = spec.template
    segs: list[Segment] = []
    if t == 1:
        segs += _lit(f"[구매 요청서] {site} 현장지원팀 / 요청자 {r}\n")
        segs += _lit("품목: ") + _seg("item_id", item)
        if sp:
            segs += _lit(" ") + _seg("spec", sp)
        segs += _lit("\n")
        if qty or unit:
            segs += _lit("수량: ") + _seg("qty", qty)
            if qty and unit:
                segs += _lit(" ")
            segs += _seg("unit", unit) + _lit("\n")
        if date:
            segs += _lit("희망 납기: ") + _seg("need_date", date) + _lit("\n")
        if loc:
            segs += _lit("배송지: ") + _seg("delivery_location", loc) + _lit("\n")
        if note:
            segs += _lit(f"비고: {note}\n")
    elif t == 2:
        segs += _lit(f"{r}: 안녕하세요, {site} 자재 요청드립니다.\n")
        segs += _lit(f"{r}: ") + _seg("item_id", item)
        if sp:
            segs += _lit(" ") + _seg("spec", sp)
        if qty or unit:
            segs += _lit(" ") + _seg("qty", qty) + _seg("unit", unit)
        segs += _lit(" 필요합니다.\n")
        if date or loc:
            segs += _lit(f"{r}: ")
            if date:
                segs += _lit("납기는 ") + _seg("need_date", date) + _lit(" 희망하고")
            if date and loc:
                segs += _lit(", ")
            if loc:
                segs += _lit("배송은 ") + _seg("delivery_location", loc) + _lit("로 부탁드려요")
            segs += _lit(".\n")
        if note:
            segs += _lit(f"{r}: {note}\n")
    elif t == 3:
        segs += _lit(f"제목: 자재 구매 요청\n\n구매팀 담당자님, {r}입니다.\n아래 자재 구매를 요청합니다.\n")
        segs += _lit("- 품명/규격: ") + _seg("item_id", item)
        if sp:
            segs += _lit(" / ") + _seg("spec", sp)
        segs += _lit("\n")
        if qty or unit:
            segs += _lit("- 수량: ") + _seg("qty", qty) + _seg("unit", unit) + _lit("\n")
        if date:
            segs += _lit("- 희망 납기: ") + _seg("need_date", date) + _lit("\n")
        if loc:
            segs += _lit("- 납품 장소: ") + _seg("delivery_location", loc) + _lit("\n")
        if note:
            segs += _lit(f"{note}\n")
    elif t == 4:
        segs += _lit(f"{site} {r} 메모\n")
        segs += _seg("item_id", item)
        if sp:
            segs += _lit(" ") + _seg("spec", sp)
        if qty or unit:
            segs += _lit(" ") + _seg("qty", qty) + _seg("unit", unit)
        segs += _lit("\n")
        if date:
            segs += _seg("need_date", date) + _lit("\n")
        if loc:
            segs += _lit("→ ") + _seg("delivery_location", loc) + _lit("\n")
        if note:
            segs += _lit(f"{note}\n")
    elif t == 5:
        # 기획안 §4-6 시연 사례 형식: "A현장, 품목 P-01 20개, 다음 주 필요."
        segs += _seg("delivery_location", loc) + _lit(", 품목 ") + _seg("item_id", item)
        if sp:
            segs += _lit(" ") + _seg("spec", sp)
        if qty or unit:
            segs += _lit(" ") + _seg("qty", qty) + _seg("unit", unit)
        if date:
            segs += _lit(", ") + _seg("need_date", date)
        segs += _lit(" 필요.")
    elif t == 6:
        segs += _lit(f"{r}입니다. ") + _seg("item_id", item)
        if sp:
            segs += _lit(" ") + _seg("spec", sp)
        if qty or unit:
            segs += _lit(" ") + _seg("qty", qty) + _seg("unit", unit)
        if date:
            segs += _lit(" ") + _seg("need_date", date) + _lit("까지")
        segs += _lit(" 부탁드립니다.")
        if note:
            segs += _lit(f" {note}")
        segs += _lit("\n")
    else:
        raise ValueError(t)
    return segs


def render(segs: list[Segment]) -> tuple[str, dict[str, tuple[int, int]]]:
    text, spans, pos = [], {}, 0
    for field, s in segs:
        if field:
            spans[field] = (pos, pos + len(s))
        text.append(s)
        pos += len(s)
    return "".join(text), spans


# ---------------------------------------------------------------- 스캔 손상
_CORRUPT = str.maketrans({"0": "O", "1": "l", "5": "S", "8": "B"})


def corrupt(value: str) -> str:
    out = value.translate(_CORRUPT)
    if out == value:
        raise ValueError(f"손상 불가 값: {value!r}")
    return out


def noise_literal(s: str) -> str:
    """스캔 잡음: 라벨 뒤 공백 제거, 일부 공백 삭제, 쉼표 뒤 공백 제거. 값 자체는 건드리지 않는다."""
    s = s.replace(": ", ":").replace(", ", ",")
    out, n = [], 0
    for ch in s:
        if ch == " ":
            n += 1
            if n % 3 == 0:
                continue
        out.append(ch)
    return "".join(out)


def field_values(spec: Spec) -> dict[str, str | None]:
    return {
        "item_id": spec.item_ref,
        "spec": spec.spec,
        "qty": spec.qty,
        "unit": spec.unit,
        "need_date": spec.date,
        "delivery_location": _loc_text(spec, spec.site),
    }


def build_doc(spec: Spec, scan: bool) -> tuple[str, dict[str, tuple[int, int]], dict[str, str | None]]:
    v = field_values(spec)
    if scan:
        for f in spec.scan_fields:
            if v[f] is None:
                raise ValueError(f"{spec.doc_id}: 손상 대상 {f} 값이 없음")
            v[f] = corrupt(v[f])
    segs = build_segments(spec, v)
    if scan:
        segs = [(f, s if f else noise_literal(s)) for f, s in segs]
    text, spans = render(segs)
    return text, spans, v


# ---------------------------------------------------------------- 정답 도출

def _candidates(spec: Spec, item_readable: bool):
    if not item_readable:
        return []
    if ID_RE.match(spec.item_ref):
        it = items_by_id().get(spec.item_ref)
        return [it] if it else []
    cands = [it for it in LEXICON if spec.item_ref in it.aliases or spec.item_ref == it.name]
    if spec.spec:
        narrowed = [it for it in cands if it.spec == spec.spec]
        if narrowed:
            cands = narrowed
    return cands


def derive_truth(spec: Spec, scan: bool) -> dict[str, dict]:
    """항목별 (정답상태, 사유). 스캔 손상 항목은 '모호(판독)'."""
    corrupted = set(spec.scan_fields) if scan else set()
    t: dict[str, dict] = {}
    explicit_id = bool(ID_RE.match(spec.item_ref))
    item_readable = "item_id" not in corrupted
    cands = _candidates(spec, item_readable)

    # 품목 ID
    if not item_readable:
        t["item_id"] = ("모호", "판독 불가(스캔 손상)")
    elif explicit_id:
        t["item_id"] = ("충족", "품목 ID 원문 존재")
    else:
        names = ", ".join(sorted({c.item_id for c in cands})) or "없음"
        t["item_id"] = ("모호", f"별칭만 있음 → 표준명 후보({names}) 사람 확정")

    # 수량
    if spec.qty is None:
        t["qty"] = ("누락", "수량 없음")
    elif "qty" in corrupted:
        t["qty"] = ("모호", "판독 불가(스캔 손상)")
    else:
        t["qty"] = ("충족", "양의 정수")

    # 단위
    if spec.unit is None:
        t["unit"] = ("누락", "단위 없음")
    else:
        std = normalize_unit(spec.unit)
        units = {c.unit for c in cands}
        if not cands:
            t["unit"] = ("모호", "품목 미확정으로 표준 단위 비교 불가")
        elif len(units) > 1:
            t["unit"] = ("모호", "후보 품목의 표준 단위가 서로 다름")
        elif std == next(iter(units)):
            t["unit"] = ("충족", "표준 단위와 일치")
        else:
            t["unit"] = ("불일치", f"표준 단위 '{next(iter(units))}'와 다름")

    # 희망일
    if spec.date is None:
        t["need_date"] = ("누락", "희망일 없음")
    elif "need_date" in corrupted:
        t["need_date"] = ("모호", "판독 불가(스캔 손상)")
    elif any(term in spec.date for term in VAGUE_DATE_TERMS):
        t["need_date"] = ("모호", f"모호 표현 '{spec.date}' → 날짜로 단정하지 않음")
    else:
        t["need_date"] = ("충족", "특정 날짜")

    # 배송 위치
    if spec.location_mode == "none":
        t["delivery_location"] = ("누락", "배송 위치 없음")
    elif spec.location_mode == "site_only":
        t["delivery_location"] = ("모호", "현장명만 있고 세부 위치 없음")
    else:
        t["delivery_location"] = ("충족", "현장명 + 세부 위치")

    # 규격
    if spec.spec is not None:
        if "spec" in corrupted:
            t["spec"] = ("모호", "판독 불가(스캔 손상)")
        elif explicit_id and item_readable and cands and cands[0].spec != spec.spec:
            t["spec"] = ("불일치", f"품목 ID 사전 규격 '{cands[0].spec}'과 다름")
        else:
            t["spec"] = ("충족", "규격 원문 존재")
    else:
        if explicit_id and item_readable and cands:
            t["spec"] = ("충족", f"품목 ID 확정 → 사전 규격 '{cands[0].spec}' 적용(원문값 없음)")
        else:
            t["spec"] = ("누락", "규격 없음(품목 ID 미확정)")

    return {f: {"정답상태": s, "사유": r} for f, (s, r) in t.items()}


# ---------------------------------------------------------------- 데이터셋 빌드

def build_dataset(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_catalog(out_dir)
    req_dir, scan_dir = out_dir / "requests", out_dir / "requests_scan"
    req_dir.mkdir(exist_ok=True)
    scan_dir.mkdir(exist_ok=True)

    truth_rows, docs, manifest = [], {}, []
    for spec in SPECS:
        for scan in (False, True):
            if scan and not spec.scan_fields:
                continue
            doc_id = spec.doc_id + ("S" if scan else "")
            text, spans, v = build_doc(spec, scan)
            fname = f"D04_가상구매요청서_{spec.doc_no:02d}{'_scan' if scan else ''}.txt"
            path = (scan_dir if scan else req_dir) / fname
            path.write_text(text, encoding="utf-8")
            truth = derive_truth(spec, scan)
            docs[doc_id] = {"문서ID": doc_id, "파일": str(path.relative_to(out_dir)), "유형": spec.kind,
                            "버전": "scan" if scan else "clean", "원문": text}
            for f in FIELD_ORDER:
                status = truth[f]["정답상태"]
                span = spans.get(f)
                value = v[f] if span else None
                if span:
                    assert text[span[0]:span[1]] == value, (doc_id, f)
                truth_rows.append({
                    "문서ID": doc_id, "유형": spec.kind, "버전": "scan" if scan else "clean",
                    "항목ID": f, "항목명": FIELD_NAMES[f], "정답상태": status,
                    "정답값": value if status == "충족" else "",
                    "원문값": value or "",
                    "원문시작": span[0] if span else "", "원문끝": span[1] if span else "",
                    "원문발췌": text[span[0]:span[1]] if span else "",
                    "사유": truth[f]["사유"],
                })
        manifest.append({"문서ID": spec.doc_id, "유형": spec.kind, "템플릿": spec.template,
                         "스캔손상항목": ";".join(spec.scan_fields), "설명": spec.remark})

    with (out_dir / "D04_원문위치_정답표.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(truth_rows[0].keys()))
        w.writeheader()
        w.writerows(truth_rows)
    (out_dir / "D04_원문위치_정답표.json").write_text(
        json.dumps({"문서": docs, "정답": truth_rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out_dir / "requests_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        w.writeheader()
        w.writerows(manifest)
    return {"docs": docs, "truth": truth_rows}


def load_dataset(data_dir: Path) -> dict:
    return json.loads((data_dir / "D04_원문위치_정답표.json").read_text(encoding="utf-8"))
