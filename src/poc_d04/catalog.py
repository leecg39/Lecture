"""필수 항목표와 용어 사전 (교육용 가상 · 배관 자재군).

모든 품목 ID·규격·별칭은 교육용 가상이며 실제 건설 자재 규격을 뜻하지 않는다.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

BASE_DATE = "2026-09-17"  # 판정 기준일 (교육일 가정)

FIELD_ORDER = ["item_id", "qty", "unit", "need_date", "delivery_location", "spec"]

FIELD_NAMES = {
    "item_id": "품목 ID",
    "qty": "수량",
    "unit": "단위",
    "need_date": "희망일",
    "delivery_location": "배송 위치",
    "spec": "규격",
}

CRITICAL_FIELDS = {"item_id", "qty", "unit", "need_date"}

REQUIRED_FIELDS = [
    {
        "자재군": "배관",
        "항목ID": "item_id",
        "항목명": "품목 ID",
        "구분": "공통",
        "충족조건": "P-NN 형식의 품목 ID가 원문에 있고 사전에 존재",
        "모호조건": "별칭·표준명만 있음(표준명 후보로 제안), 후보가 2개 이상, 판독 불가 글자",
        "중요항목": "Y",
    },
    {
        "자재군": "배관",
        "항목ID": "qty",
        "항목명": "수량",
        "구분": "공통",
        "충족조건": "양의 정수",
        "모호조건": "판독 불가 글자(예: 2O)",
        "중요항목": "Y",
    },
    {
        "자재군": "배관",
        "항목ID": "unit",
        "항목명": "단위",
        "구분": "공통",
        "충족조건": "사전의 표준 단위와 같음(EA=개, M=m 동의어 허용)",
        "모호조건": "품목이 확정되지 않아 비교 불가, 판독 불가",
        "중요항목": "Y",
    },
    {
        "자재군": "배관",
        "항목ID": "need_date",
        "항목명": "희망일",
        "구분": "공통",
        "충족조건": "특정 날짜(YYYY-MM-DD, M월 D일, M/D)",
        "모호조건": "'다음 주', 'ASAP', '빨리', '이번 달 안' 등 기간·정도 표현. 날짜로 단정하지 않음",
        "중요항목": "Y",
    },
    {
        "자재군": "배관",
        "항목ID": "delivery_location",
        "항목명": "배송 위치",
        "구분": "공통",
        "충족조건": "현장명 + 세부 위치(동·층·창고·게이트 등)",
        "모호조건": "현장명만 있음",
        "중요항목": "N",
    },
    {
        "자재군": "배관",
        "항목ID": "spec",
        "항목명": "규격",
        "구분": "자재군추가",
        "충족조건": "규격 토큰(50A, 100A, 12mm 등)이 있거나, 품목 ID가 확정되어 사전 규격을 적용할 수 있음",
        "모호조건": "판독 불가. 품목 ID 없이 별칭만 있고 규격도 없으면 누락",
        "중요항목": "N",
    },
]


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    spec: str
    unit: str
    aliases: tuple[str, ...]
    note: str = ""

    @property
    def display(self) -> str:
        return f"{self.name} {self.spec}"


LEXICON: list[Item] = [
    Item("P-01", "볼밸브", "50A", "개", ("볼밸브", "볼발브", "밸브", "ball valve"),
         "P-02(100A)와 별칭이 같음 → 규격 없으면 병합 금지"),
    Item("P-02", "볼밸브", "100A", "개", ("볼밸브", "볼발브", "밸브", "ball valve"),
         "P-01(50A)와 별칭이 같음 → 규격 없으면 병합 금지"),
    Item("P-03", "PVC 파이프", "50A", "본", ("PVC 파이프", "PVC관", "PVC파이프", "피브이씨 파이프", "pvc pipe"),
         "P-04(100A)와 별칭이 같음 → 규격 없으면 병합 금지"),
    Item("P-04", "PVC 파이프", "100A", "본", ("PVC 파이프", "PVC관", "PVC파이프", "피브이씨 파이프", "pvc pipe"),
         "P-03(50A)와 별칭이 같음 → 규격 없으면 병합 금지"),
    Item("P-05", "강관", "50A", "본", ("강관", "백관", "스틸파이프", "steel pipe"),
         "P-06(100A)와 별칭이 같음"),
    Item("P-06", "강관", "100A", "본", ("강관", "백관", "스틸파이프", "steel pipe"),
         "P-05(50A)와 별칭이 같음"),
    Item("P-07", "PVC 엘보 90도", "50A", "개", ("엘보", "엘보우", "90도 엘보", "elbow"),
         "P-08(45도)과 '엘보' 별칭 공유 → 각도 확인"),
    Item("P-08", "PVC 엘보 45도", "50A", "개", ("엘보", "엘보우", "45도 엘보", "45엘보"),
         "P-07(90도)과 '엘보' 별칭 공유 → 각도 확인"),
    Item("P-09", "배관 보온재", "50A", "m", ("보온재", "단열재", "인슐레이션"),
         "길이 단위(m). 개수로 요청 오면 불일치"),
    Item("P-10", "테프론 테이프", "12mm", "롤", ("테프론", "테플론 테이프", "씰테이프", "테프론 테이프"),
         "롤 단위. 개수로 요청 오면 불일치"),
]

UNIT_SYNONYMS = {
    "개": {"개", "EA", "ea", "Ea", "개소", "pcs"},
    "본": {"본"},
    "m": {"m", "M", "미터", "메타", "meter"},
    "롤": {"롤", "roll", "ROLL", "Roll"},
}

VAGUE_DATE_TERMS = (
    "다음 주", "다음주", "내주 초", "내주", "이번 주", "이번주", "이번 달 안", "이달 안", "월말까지",
    "ASAP", "asap", "빨리", "급함", "급합니다", "조속히", "가능한 빨리", "최대한 빨리",
)


def normalize_unit(token: str | None) -> str | None:
    if token is None:
        return None
    for std, syns in UNIT_SYNONYMS.items():
        if token in syns:
            return std
    return None


def items_by_id() -> dict[str, Item]:
    return {i.item_id: i for i in LEXICON}


def alias_index() -> list[tuple[str, list[Item]]]:
    """별칭 → 품목 목록. 긴 별칭이 먼저 오도록 정렬(부분 문자열 오탐 방지)."""
    idx: dict[str, list[Item]] = {}
    for it in LEXICON:
        for a in dict.fromkeys(it.aliases + (it.name,)):
            if it not in idx.setdefault(a, []):
                idx[a].append(it)
    return sorted(idx.items(), key=lambda kv: -len(kv[0]))


def write_catalog(out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    req = out_dir / "D04_자재군별_필수항목표.csv"
    with req.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(REQUIRED_FIELDS[0].keys()))
        w.writeheader()
        w.writerows(REQUIRED_FIELDS)
    lex = out_dir / "D04_용어사전_교육용.csv"
    with lex.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["품목ID", "표준명", "규격", "표준단위", "별칭", "주의"])
        for it in LEXICON:
            w.writerow([it.item_id, it.name, it.spec, it.unit, ";".join(it.aliases), it.note])
    return req, lex
