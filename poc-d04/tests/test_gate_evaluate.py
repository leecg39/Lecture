import json

from poc_d04.evaluate import passes, render_report, score
from poc_d04.extract import extract_rule, load_pasted
from poc_d04.gate import audit
from poc_d04.pipeline import run_all, run_doc
from poc_d04.rules import check


def _codes(v):
    return sorted(x["코드"] for x in v)


def test_rule_backend_has_no_gate_violations(dataset):
    for doc_id, d in dataset["문서"].items():
        assert audit(extract_rule(d["원문"], doc_id), d["원문"]) == [], doc_id


def test_g2_vague_to_date(demo_text):
    pasted = {"항목": [{"항목ID": "희망일", "원문값": "2026-09-24", "메모": "다음 주 → 9/24로 추정"}]}
    v = audit(load_pasted(pasted, demo_text), demo_text)
    assert "G2" in _codes(v)
    # 표준명후보 칸에 날짜를 넣는 경우도 잡는다
    pasted2 = {"항목": [{"항목ID": "희망일", "원문값": "다음 주", "표준명후보": "2026-09-24"}]}
    assert "G2" in _codes(audit(load_pasted(pasted2, demo_text), demo_text))


def test_g4_spec_fabricated(demo_text):
    pasted = {"항목": [{"항목ID": "규격", "원문값": "50A"}]}
    v = audit(load_pasted(pasted, demo_text), demo_text)
    assert _codes(v) == ["G4"]


def test_g1_value_not_in_text(demo_text):
    pasted = {"항목": [{"항목ID": "수량", "원문값": "200"}]}
    assert _codes(audit(load_pasted(pasted, demo_text), demo_text)) == ["G1"]


def test_g3_alias_merge():
    text = "볼밸브 12개 2026-09-29 B현장 1동 야적장"
    pasted = {"항목": [{"항목ID": "품목 ID", "원문값": "볼밸브", "표준명후보": "P-01 볼밸브 50A"}]}
    assert "G3" in _codes(audit(load_pasted(pasted, text), text))
    # 규격이 원문에 있으면 병합이 아니다
    text2 = "볼밸브 50A 12개"
    pasted2 = {"항목": [{"항목ID": "품목 ID", "원문값": "볼밸브", "표준명후보": "P-01 볼밸브 50A"}]}
    assert "G3" not in _codes(audit(load_pasted(pasted2, text2), text2))


def test_g5_human_column_prefilled(demo_text):
    pasted = {"항목": [{"항목ID": "희망일", "원문값": "다음 주", "사람확정": "2026-09-24"}]}
    assert "G5" in _codes(audit(load_pasted(pasted, demo_text), demo_text))


def test_g6_out_of_scope_items(demo_text):
    # 항목 수준: 공급사 최저가 선정 → G6. 문서 수준: 자동 발주 키 → G6.
    pasted = {"항목": [{"항목ID": "품목 ID", "원문값": "P-01"},
                     {"항목ID": "공급사", "원문값": "B상사", "메모": "최저가 자동 선정"}],
              "발주": "자동 발주 진행"}
    ex = load_pasted(pasted, demo_text)
    assert len(ex["범위밖"]) == 2 and any("항목표 밖" in w for w in ex["경고"])
    v = audit(ex, demo_text)
    assert _codes(v).count("G6") == 2 and all(x["담당"] and x["조치"] for x in v)
    # 제외 목록과 무관한 미지 키는 표에 넣지 않되 게이트 위반은 아니다
    pasted2 = {"항목": [{"항목ID": "품목 ID", "원문값": "P-01"}, {"항목ID": "비고", "원문값": "급함"}]}
    assert "G6" not in _codes(audit(load_pasted(pasted2, demo_text), demo_text))


def test_metrics_meet_targets_on_rule_backend(dataset, tmp_path):
    runs = {k: run_doc(d["원문"], k, "rule") for k, d in dataset["문서"].items()}
    m = score({k: v["판정"] for k, v in runs.items()}, dataset)
    assert all(passes(m).values()), m["전체"]["미스"]
    assert m["전체"]["누락 탐지율"] == 1.0 and m["전체"]["원문 추적 가능 비율"] == 1.0
    assert m["전체"]["중요 오류"] == 0
    assert "유형:정상" in m and "버전:scan" in m


def test_metric_formulas_with_handmade_predictions(dataset):
    """D04-13: 정답 확인필요 = 희망일·배송위치. 예측이 희망일을 충족으로 두고 수량을 경고하면
    탐지 1/2, 오탐 1/2, 중요오류 1(희망일)."""
    text = dataset["문서"]["D04-13"]["원문"]
    pred = check(extract_rule(text, "D04-13"), text)
    for r in pred["항목"]:
        if r["항목ID"] == "need_date":
            r["상태"], r["확인필요"] = "충족", False
        if r["항목ID"] == "qty":
            r["상태"], r["확인필요"] = "모호", True
    m = score({"D04-13": pred}, dataset)["전체"]
    assert m["탐지"] == 1 and m["정답확인필요"] == 2
    assert m["오탐"] == 1 and m["예측확인필요"] == 2
    assert m["중요 오류"] == 1
    assert not passes({"전체": m})["중요 오류"]


def test_run_all_writes_report(dataset, tmp_path):
    data_dir = tmp_path / "data"
    from poc_d04.data_gen import build_dataset
    build_dataset(data_dir)
    r = run_all(data_dir, tmp_path / "out", "rule")
    assert (tmp_path / "out" / "평가리포트.md").exists()
    assert "통과" in r["report"] and "미달" not in r["report"]
    js = json.loads((tmp_path / "out" / "results_rule.json").read_text(encoding="utf-8"))
    assert len(js) == len(dataset["문서"])
    assert "## 게이트 위반" in render_report(r["metrics"], "rule") or "게이트 위반" in r["report"]
