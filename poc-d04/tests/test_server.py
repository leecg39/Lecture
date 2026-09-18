from poc_d04.data_gen import build_dataset
from poc_d04.server import Demo


def test_demo_run_rule_and_bad_draft(tmp_path):
    build_dataset(tmp_path)
    demo = Demo(tmp_path)
    html = demo.run("A현장, 품목 P-01 20개, 다음 주 필요.", "", "D04-13")
    assert "게이트 위반 없음" in html and "희망일, 배송 위치" in html and "탐지 2/2" in html
    assert 'class="human"></td>' in html  # 사람 확정 칸은 비어 있다
    bad = '{"항목":[{"항목ID":"희망일","원문값":"2026-09-24","메모":"다음 주 추정"}],"사람확정":"OK"}'
    html2 = demo.run("A현장, 품목 P-01 20개, 다음 주 필요.", bad, "D04-13")
    assert "<b>G2</b>" in html2 and "<b>G5</b>" in html2
    # 게이트 단계: 판정 배너·지시 대조·조치·담당·원문 근거 (PDF M03 p5/p6/p8/p10)
    assert "재시험" in html2 and 'class="verdict bad"' in html2
    assert "계속" in html and 'class="verdict ok"' in html
    assert 'class="gate-check"' in html and '<span class="pill ok">통과</span>' in html
    assert "확인 담당 · 현장 담당자" in html2 and 'class="gate-action"' in html2
    assert '<pre class="source-text">' in html and "<mark" in html
    assert "원문에서 위치를 찾지 못한 값" in html2
    assert "요청서 원문이 비어" in demo.run("", "", "")
    assert "JSON이 아닙니다" in demo.run("A현장 P-01 20개", "{oops", "")


def test_page_escapes_and_lists_samples(tmp_path):
    build_dataset(tmp_path)
    page = Demo(tmp_path).page(text="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page
    assert "D04-13 · 모호표현 · clean" in page
