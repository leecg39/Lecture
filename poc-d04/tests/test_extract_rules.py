from poc_d04.extract import extract_rule, load_pasted
from poc_d04.rules import check, parse_date


def _by(ex):
    return {i["항목ID"]: i for i in ex["항목"]}


def _st(res):
    return {i["항목ID"]: i["상태"] for i in res["항목"]}


def test_demo_extraction_and_check(demo_text):
    ex = extract_rule(demo_text, "demo")
    b = _by(ex)
    assert b["item_id"]["원문값"] == "P-01" and b["qty"]["원문값"] == "20" and b["unit"]["원문값"] == "개"
    assert b["need_date"]["원문값"] == "다음 주" and "변환하지 않음" in b["need_date"]["메모"]
    assert b["delivery_location"]["원문값"] == "A현장"
    assert b["spec"]["원문값"] is None
    for i in ex["항목"]:
        if i["원문값"] is not None:
            assert demo_text[i["원문시작"]:i["원문끝"]] == i["원문값"]
    st = _st(check(ex, demo_text))
    assert st == {"item_id": "충족", "qty": "충족", "unit": "충족", "need_date": "모호",
                  "delivery_location": "모호", "spec": "충족"}


def test_alias_not_merged_without_spec():
    text = "볼밸브 12개 2026-09-29 B현장 1동 야적장"
    b = _by(extract_rule(text))
    assert b["item_id"]["원문값"] == "볼밸브"
    assert set(b["item_id"]["후보품목"]) == {"P-01", "P-02"}
    assert "병합 금지" in b["item_id"]["표준명근거"]
    st = _st(check(extract_rule(text), text))
    assert st["item_id"] == "모호" and st["spec"] == "누락" and st["unit"] == "충족"


def test_alias_narrowed_by_spec_still_needs_human():
    text = "백관 100A 10본 급합니다 C현장 1동 1층 야적장"
    b = _by(extract_rule(text))
    assert b["item_id"]["후보품목"] == ["P-06"]
    assert _st(check(extract_rule(text), text))["item_id"] == "모호"


def test_unreadable_tokens_flagged_not_guessed():
    text = "품목:P-Ol 5OA\n수량:2O 개\n희망 납기:2O26-O9-25\n배송지:A현장 3동"
    ex = extract_rule(text)
    b = _by(ex)
    assert b["item_id"]["원문값"] == "P-Ol" and "판독" in b["item_id"]["메모"]
    assert b["qty"]["원문값"] == "2O" and b["spec"]["원문값"] == "5OA" and b["need_date"]["원문값"] == "2O26-O9-25"
    st = _st(check(ex, text))
    assert st["item_id"] == st["qty"] == st["spec"] == st["need_date"] == "모호"
    assert st["unit"] == "모호"  # 품목 미확정 → 비교 불가


def test_unit_mismatch_and_synonym():
    t1 = "P-03 50A 40m 2026-09-27 A현장 3동 자재창고"
    assert _st(check(extract_rule(t1), t1))["unit"] == "불일치"
    t2 = "P-07 50A 15 EA 2026-09-30 A현장 2동 기계실"
    assert _st(check(extract_rule(t2), t2))["unit"] == "충족"
    t3 = "P-06 100A 12EA 10월 5일 C현장 1동 야적장"
    assert _st(check(extract_rule(t3), t3))["unit"] == "불일치"


def test_missing_fields():
    t = "P-02 100A\n수량: 개\n희망 납기: 2026-09-26\n배송지: A현장 3동 지하1층 자재창고"
    st = _st(check(extract_rule(t), t))
    assert st["qty"] == "누락" and st["unit"] == "충족"
    t2 = "한구매입니다. PVC관 30본 부탁드립니다."
    st2 = _st(check(extract_rule(t2), t2))
    assert st2 == {"item_id": "모호", "qty": "충족", "unit": "충족", "need_date": "누락",
                   "delivery_location": "누락", "spec": "누락"}


def test_date_forms_and_past_date():
    assert parse_date("2026-09-25").isoformat() == "2026-09-25"
    assert parse_date("9월 26일").isoformat() == "2026-09-26"
    assert parse_date("9/28").isoformat() == "2026-09-28"
    assert parse_date("다음 주") is None
    t = "P-01 50A 20개 2026-09-10 A현장 3동 창고"
    assert _st(check(extract_rule(t), t))["need_date"] == "불일치"
    t2 = "최공무입니다. P-10 12mm 8롤 2026-09-30까지 부탁드립니다."
    st = _st(check(extract_rule(t2), t2))
    assert st["need_date"] == "충족" and st["qty"] == "충족" and st["unit"] == "충족" and st["spec"] == "충족"


def test_location_prefers_detailed_mention():
    t = "[구매 요청서] A현장 현장지원팀 / 요청자 김현장\n품목: P-01 50A\n수량: 20 개\n배송지: A현장 3동 지하1층 자재창고\n"
    b = _by(extract_rule(t))
    assert b["delivery_location"]["원문값"] == "A현장 3동 지하1층 자재창고"


def test_spec_mismatch_with_explicit_id():
    t = "P-01 100A 20개 2026-09-25 A현장 3동 창고"
    assert _st(check(extract_rule(t), t))["spec"] == "불일치"


def test_paste_loader_recovers_offsets(demo_text):
    pasted = {"항목": [
        {"항목ID": "품목 ID", "원문값": "P-01", "표준명후보": "볼밸브 50A"},
        {"항목ID": "수량", "원문값": "20"},
        {"항목ID": "단위", "원문값": "개"},
        {"항목ID": "희망일", "원문값": "다음 주", "메모": "구체 날짜 없음"},
        {"항목ID": "배송 위치", "원문값": "A현장"},
        {"항목ID": "규격", "원문값": None},
    ]}
    ex = load_pasted(pasted, demo_text, "demo")
    b = _by(ex)
    assert b["item_id"]["원문시작"] == demo_text.index("P-01")
    assert b["need_date"]["원문시작"] == demo_text.index("다음 주")
    assert b["spec"]["원문값"] is None
    st = _st(check(ex, demo_text))
    assert st["need_date"] == "모호" and st["delivery_location"] == "모호" and st["spec"] == "충족"


def test_paste_loader_accepts_english_keys_and_dict_form(demo_text):
    pasted = {"품목 ID": {"value": "P-01"}, "수량": {"value": "20"}, "단위": "개",
              "희망일": {"value": "다음 주"}, "배송 위치": {"value": "A현장"}, "규격": {"value": "없음"}}
    b = _by(load_pasted(pasted, demo_text))
    assert b["item_id"]["원문값"] == "P-01" and b["unit"]["원문값"] == "개" and b["spec"]["원문값"] is None
