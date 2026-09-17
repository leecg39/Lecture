from collections import Counter

from poc_d04.catalog import FIELD_ORDER
from poc_d04.data_gen import SPECS, corrupt


def test_30_specs_six_per_kind():
    assert len(SPECS) == 30
    assert Counter(s.kind for s in SPECS) == {"정상": 6, "필수누락": 6, "모호표현": 6, "단위불일치": 6, "배송조건누락": 6}
    assert len({s.doc_no for s in SPECS}) == 30


def test_truth_offsets_match_text(dataset):
    for row in dataset["정답"]:
        if row["원문시작"] != "":
            text = dataset["문서"][row["문서ID"]]["원문"]
            assert text[row["원문시작"]:row["원문끝"]] == row["원문값"] == row["원문발췌"]
        else:
            assert row["원문값"] == ""


def test_every_doc_has_six_fields(dataset):
    per_doc = Counter(r["문서ID"] for r in dataset["정답"])
    assert set(per_doc.values()) == {len(FIELD_ORDER)}


def test_normal_docs_all_ok(dataset):
    for r in dataset["정답"]:
        if r["유형"] == "정상" and r["버전"] == "clean":
            assert r["정답상태"] == "충족", r


def test_scan_corrupted_fields_are_ambiguous(dataset):
    by = {(r["문서ID"], r["항목ID"]): r for r in dataset["정답"]}
    for s in SPECS:
        for f in s.scan_fields:
            assert by[(s.doc_id + "S", f)]["정답상태"] == "모호"
            assert "판독" in by[(s.doc_id + "S", f)]["사유"]


def test_demo_case_matches_plan(dataset):
    """기획안 §4-6: P-01·20·개 원문값, 희망일·배송 위치 확인 대상."""
    t = {r["항목ID"]: r["정답상태"] for r in dataset["정답"] if r["문서ID"] == "D04-13"}
    assert t == {"item_id": "충족", "qty": "충족", "unit": "충족", "need_date": "모호",
                 "delivery_location": "모호", "spec": "충족"}
    assert dataset["문서"]["D04-13"]["원문"] == "A현장, 품목 P-01 20개, 다음 주 필요."


def test_corrupt_changes_value():
    assert corrupt("20") == "2O"
    assert corrupt("P-01") == "P-Ol"
    assert corrupt("2026-10-01") == "2O26-lO-Ol"
