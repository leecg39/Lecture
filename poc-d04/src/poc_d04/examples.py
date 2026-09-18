"""실패 장면(잘못된 초안)과 오프라인 캡처(도구 접속 불가 대비)를 생성한다."""
from __future__ import annotations

import json
from pathlib import Path

from .data_gen import load_dataset
from .extract import load_pasted
from .gate import audit
from .pipeline import render_table, run_doc
from .questions import draft
from .rules import check

DEMO_ID = "D04-13"
# 조별 실습 표본: 유형별 1건 + 스캔 1건 + 복합 결함 1건
GROUP_SAMPLES = {
    "1조": "D04-08",   # 필수 누락 · 별칭만(P-01/P-02) · 규격 누락
    "2조": "D04-15",   # 모호 표현 · 별칭 '엘보' 후보 2개
    "3조": "D04-19",   # 단위 불일치 (본 ↔ m)
    "4조": "D04-26",   # 배송 위치 없음
    "5조": "D04-03S",  # 저품질 스캔 · 규격 판독 불가
    "6조": "D04-12",   # 복합 결함(별칭·규격·희망일·배송 위치)
}

BAD_DRAFT = {
    "문서ID": DEMO_ID,
    "항목": [
        {"항목ID": "품목 ID", "원문값": "P-01", "원문발췌": "P-01", "표준명후보": "볼밸브 50A"},
        {"항목ID": "수량", "원문값": "20", "원문발췌": "20"},
        {"항목ID": "단위", "원문값": "개", "원문발췌": "개"},
        {"항목ID": "희망일", "원문값": "2026-09-24", "원문발췌": "다음 주", "메모": "다음 주 → 수요일 기준 9/24로 정리"},
        {"항목ID": "배송 위치", "원문값": "A현장 3동 자재창고", "원문발췌": "A현장", "메모": "통상 자재창고로 배송"},
        {"항목ID": "규격", "원문값": "50A", "원문발췌": "", "메모": "P-01은 50A이므로 기재"},
        {"항목ID": "공급사", "원문값": "B상사", "원문발췌": "", "메모": "3사 견적 중 최저가로 자동 선정"},
    ],
    "사람확정": "이상 없음, 발주 진행 가능",
}


def to_paste_format(extraction: dict) -> dict:
    """규칙 추출 결과를 ChatGPT가 낼 법한 붙여넣기 형식(오프셋 없이 원문발췌)으로 바꾼다."""
    return {"항목": [
        {"항목ID": it["항목명"], "원문값": it["원문값"],
         "원문발췌": it["원문값"], "표준명후보": it["표준명후보"], "메모": it["메모"]}
        for it in extraction["항목"]]}


def write_bad_draft(data_dir: Path, ex_dir: Path) -> list[Path]:
    ds = load_dataset(data_dir)
    text = ds["문서"][DEMO_ID]["원문"]
    ex = load_pasted(BAD_DRAFT, text, DEMO_ID)
    viol = audit(ex, text)
    res = draft(check(ex, text))
    good = run_doc(text, DEMO_ID, "rule")
    ex_dir.mkdir(parents=True, exist_ok=True)
    jpath = ex_dir / "D04_잘못된초안_예시.json"
    jpath.write_text(json.dumps(BAD_DRAFT, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# D04_잘못된초안_예시 — 실패 장면 (시연 6–8분)",
        "",
        "교육용 가상. 원문에 없는 값을 채운 AI 초안을 그대로 보여 주고, 게이트 검사기가 무엇을 지적하는지 확인한다.",
        "", "## 원문", "", "```", text, "```", "",
        "## 잘못된 초안 (AI가 '친절하게' 채운 결과)", "", "```json",
        json.dumps(BAD_DRAFT, ensure_ascii=False, indent=2), "```", "",
        "## 게이트 검사 결과", "",
        "| 코드 | 항목 | 지적 | 게이트 |", "|---|---|---|---|",
    ]
    for v in viol:
        lines.append(f"| {v['코드']} | {v['항목ID'] or '(문서)'} | {v['설명']} | {v['게이트']} |")
    lines += ["", "## 왜 위험한가 (강사 멘트 요지)", "",
              "- 규칙 검사만 돌리면 이 초안은 **확인 필요 0건**으로 통과한다. 날짜·위치·규격이 모두 '값이 있고 형식이 맞기' 때문이다. 원문 추적(게이트)이 없으면 규칙은 지어낸 값을 걸러내지 못한다.",
              "- '다음 주'를 9/24로 단정하면 현장은 9/24에 자재를 기다리고, 요청자는 9/28을 생각했을 수 있다 → 추가 문의가 아니라 오배송이 된다.",
              "- '통상 자재창고'는 이 요청서에 없는 정보다. 그럴듯한 값이 원문 근거 없는 값이다.",
              "- 규격 50A는 사전 규칙으로 적용할 수 있지만, 그것은 '규칙' 열에서 근거를 남기고 하는 일이지 AI가 원문값 칸에 채울 일이 아니다.",
              "- '이상 없음, 발주 진행 가능'은 사람 확정 칸이다. AI가 채우면 검토 단계가 사라진다.",
              "- '공급사 B상사(최저가 자동 선정)'은 이번 시험에서 **제외한 일**이다. 요청서 누락 확인 PoC가 견적 비교·발주까지 손대면 범위가 흐려지고 검증할 수 없게 된다.",
              "", "## 같은 원문의 올바른 표시표 (비교용)", ""]
    lines.append(render_table(good))
    lines += ["", "## 위험 한 줄 (학습자 작성 예)", "",
              "> 원문에 없는 날짜·위치·규격을 채운 초안은 '문서 생성 성공'처럼 보이지만 추가 문의 항목을 숨긴다.", ""]
    mpath = ex_dir / "D04_잘못된초안_예시.md"
    mpath.write_text("\n".join(lines), encoding="utf-8")
    return [jpath, mpath]


def write_offline_captures(data_dir: Path, ex_dir: Path) -> list[Path]:
    ds = load_dataset(data_dir)
    cap = ex_dir / "D04_오프라인_추출결과"
    cap.mkdir(parents=True, exist_ok=True)
    paths = []
    targets = {"시연": DEMO_ID, **GROUP_SAMPLES}
    index = ["# 오프라인 추출 결과 캡처 (도구 접속 불가 대비)", "",
             "규칙 백엔드로 만든 결과를 ChatGPT 출력 형식으로 정리했다. 교실에서 AI 접속이 안 되면 이 파일의 JSON을 활동지에 옮겨 같은 활동을 진행한다.",
             "", "| 배정 | 문서ID | 유형 | 파일 |", "|---|---|---|---|"]
    for label, doc_id in targets.items():
        d = ds["문서"][doc_id]
        r = run_doc(d["원문"], doc_id, "rule")
        paste = to_paste_format(r["추출"])
        fname = f"{label}_{doc_id}.md"
        lines = [f"# {label} · {doc_id} ({d['유형']} · {d['버전']})", "", "## 원문", "", "```", d["원문"].rstrip(), "```", "",
                 "## 1단계 추출 결과 (ChatGPT 출력 형식)", "", "```json", json.dumps(paste, ensure_ascii=False, indent=2), "```", "",
                 "## 2단계 규칙 검사 → 누락 표시표", "", render_table(r),
                 "## 3단계 보완 질문 초안", ""]
        qs = r["판정"]["보완질문요약"]
        lines += [f"{i}. {q}" for i, q in enumerate(qs, 1)] or ["없음 (모든 필수 항목 충족)"]
        if qs:
            lines += ["", "메신저 초안:", "", f"> 안녕하세요, 구매팀입니다. 요청 건 확인 중 {len(qs)}가지만 여쭙습니다. "
                      + " ".join(f"{i}) {q}" for i, q in enumerate(qs, 1))]
        lines += ["", "## 사람 확정 칸", "", "| 항목 | 사람 확정 | 확정자 |", "|---|---|---|"]
        lines += [f"| {it['항목명']} |  |  |" for it in r["판정"]["항목"]]
        p = cap / fname
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths.append(p)
        (cap / f"{label}_{doc_id}.json").write_text(json.dumps(paste, ensure_ascii=False, indent=2), encoding="utf-8")
        index.append(f"| {label} | {doc_id} | {d['유형']} · {d['버전']} | [{fname}]({fname}) |")
    ip = cap / "README.md"
    ip.write_text("\n".join(index) + "\n", encoding="utf-8")
    paths.append(ip)
    return paths


def write_all(data_dir: Path, ex_dir: Path) -> list[Path]:
    return write_bad_draft(data_dir, ex_dir) + write_offline_captures(data_dir, ex_dir)
