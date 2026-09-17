"""적대적 검토(docs/REVIEW_01.md)에서 발견한 사례의 회귀 테스트."""
import pytest

from poc_d04.extract import extract_rule, find_standalone, load_pasted
from poc_d04.gate import audit
from poc_d04.rules import check

DEMO = "A현장, 품목 P-01 20개, 다음 주 필요."


def _states(ex, text):
    return {i["항목ID"]: i["상태"] for i in check(ex, text)["항목"]}


def _codes(ex, text):
    return sorted(v["코드"] for v in audit(ex, text))


def test_A_qty_with_unit_glued_is_split_when_unit_missing():
    ex = load_pasted({"항목": [{"항목ID": "수량", "원문값": "20개"}]}, DEMO)
    by = {i["항목ID"]: i for i in ex["항목"]}
    assert by["qty"]["원문값"] == "20" and by["unit"]["원문값"] == "개"
    assert DEMO[by["unit"]["원문시작"]:by["unit"]["원문끝"]] == "개"
    assert _codes(ex, DEMO) == []
    # 단위 칸이 이미 있으면 나누지 않는다(원문값은 그대로 두고 규칙이 모호로 판정)
    ex2 = load_pasted({"항목": [{"항목ID": "수량", "원문값": "20개"}, {"항목ID": "단위", "원문값": "개"}]}, DEMO)
    assert {i["항목ID"]: i["원문값"] for i in ex2["항목"]}["qty"] == "20개"
    assert _states(ex2, DEMO)["qty"] == "모호"


def test_B_numeric_json_value_becomes_string():
    ex = load_pasted({"항목": [{"항목ID": "수량", "원문값": 20}]}, DEMO)
    q = next(i for i in ex["항목"] if i["항목ID"] == "qty")
    assert q["원문값"] == "20" and DEMO[q["원문시작"]:q["원문끝"]] == "20"


def test_C_offset_prefers_standalone_occurrence():
    text = "2026-09-20까지 P-01 20개 A현장"
    assert find_standalone(text, "20") == text.index(" 20개") + 1
    ex = load_pasted({"항목": [{"항목ID": "수량", "원문값": "20"}]}, text)
    q = next(i for i in ex["항목"] if i["항목ID"] == "qty")
    assert q["원문시작"] == text.index(" 20개") + 1


def test_D_g3_catches_spec_inferred_in_candidate_without_id():
    text = "볼밸브 12개 B현장 1동"
    ex = load_pasted({"항목": [{"항목ID": "품목 ID", "원문값": "볼밸브", "표준명후보": "볼밸브 50A"}]}, text)
    assert "G3" in _codes(ex, text)
    ok = load_pasted({"항목": [{"항목ID": "품목 ID", "원문값": "볼밸브", "표준명후보": "P-01 볼밸브 50A / P-02 볼밸브 100A (규격 확인)"}]}, text)
    assert "G3" not in _codes(ok, text)


def test_E_human_column_key_with_space_is_detected():
    ex = load_pasted({"항목": [{"항목ID": "희망일", "원문값": "다음 주", "사람 확정": "9/24"}]}, DEMO)
    assert "G5" in _codes(ex, DEMO)


def test_F_lowercase_or_dash_variant_id_is_recognized():
    text = "p-01 20개 다음 주 A현장"
    ex = load_pasted({"항목": [{"항목ID": "품목 ID", "원문값": "p-01"}]}, text)
    st = _states(ex, text)
    assert st["item_id"] == "충족" and st["spec"] == "충족"
    assert _codes(ex, text) == []  # 원문값은 그대로 'p-01' → 추적 가능


def test_G_empty_output_warns_but_does_not_fabricate():
    ex = load_pasted({}, DEMO)
    assert all(i["원문값"] is None for i in ex["항목"])
    assert any("하나도 없음" in w for w in ex["경고"])
    assert _codes(ex, DEMO) == []


def test_H_english_keys_list_form():
    ex = load_pasted([{"field": "item_id", "value": "P-01"}, {"field": "need_date", "value": "다음 주"}], DEMO)
    st = _states(ex, DEMO)
    assert st["item_id"] == "충족" and st["need_date"] == "모호"


def test_I_multi_item_request_is_flagged_for_human():
    ex = extract_rule("P-01 50A 20개, P-03 50A 40본 2026-09-25 A현장 3동 창고")
    assert any("복수 품목" in w for w in ex["경고"])
    assert "복수 품목" in next(i for i in ex["항목"] if i["항목ID"] == "item_id")["메모"]


def test_J_invalid_json_gives_readable_error():
    with pytest.raises(ValueError, match="JSON이 아닙니다"):
        load_pasted("{not json", DEMO)


def test_M_code_fence_and_prose_are_stripped():
    body = '{"항목":[{"항목ID":"수량","원문값":"20"}]}'
    for wrapped in (f"```json\n{body}\n```", f"다음은 결과입니다.\n```\n{body}\n```\n확인 바랍니다.", f"결과: {body} 끝."):
        ex = load_pasted(wrapped, DEMO)
        assert next(i for i in ex["항목"] if i["항목ID"] == "qty")["원문값"] == "20"


def test_K_duplicate_field_warns():
    ex = load_pasted({"항목": [{"항목ID": "수량", "원문값": "20"}, {"항목ID": "수량", "원문값": "20"}]}, DEMO)
    assert any("중복" in w for w in ex["경고"])


def test_L_dict_form_ignores_meta_keys_and_catches_document_level_human():
    ex = load_pasted({"문서ID": "X", "품목 ID": "P-01", "사람확정": "OK"}, DEMO)
    assert "G5" in _codes(ex, DEMO)
