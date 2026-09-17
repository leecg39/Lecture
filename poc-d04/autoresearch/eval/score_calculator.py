#!/usr/bin/env python3
"""Frozen Metric — Inner Loop가 수정하면 안 된다.

점수 = error*w + dom*w + form*w + visual*w + design*w  (각 0–100, 가중 합)
design 축: server.py CSS/PAGE 정적 분석 (의도된 디자인 신호).
나머지: HTTP로 실제 페이지 응답을 검사.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "src" / "poc_d04" / "server.py"
WEIGHTS = Path(__file__).resolve().parents[1] / "outer" / "metric_weights.json"
ROUTES = Path(__file__).with_name("test-routes.json")
BASE = "http://127.0.0.1:8765"


def _get(path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def _post(path: str, body: dict) -> tuple[int, str]:
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def score_error() -> float:
    """서버 응답 가능 + /health. (브라우저 콘솔은 HTTP 경로에서 0으로 가정, 크래시만 감점)"""
    code, _ = _get("/health")
    if code == 200:
        return 100.0
    code2, _ = _get("/")
    return 40.0 if code2 == 200 else 0.0


def score_dom(routes: list) -> float:
    ok = total = 0
    for route in routes:
        if route.get("method") == "POST":
            continue
        total += 1
        code, html = _get(route["path"])
        if code != 200:
            continue
        checks = route["checks"]
        sels = checks.get("required_selectors", [])
        texts = checks.get("required_text", [])
        sel_ok = True
        for s in sels:
            if s == "form" and "<form" not in html:
                sel_ok = False
            elif s == "textarea#text" and 'id="text"' not in html:
                sel_ok = False
            elif s.startswith("select") and "<select" not in html:
                sel_ok = False
            elif s.startswith("button") and "<button" not in html:
                sel_ok = False
            elif s.startswith("a[href") and "/bad" not in html:
                sel_ok = False
            elif s == "table" and "<table" not in html:
                sel_ok = False
            elif s == "td.human" and 'class="human"' not in html and "class='human'" not in html:
                sel_ok = False
            elif s == ".gate" and 'class="gate"' not in html and "class='gate'" not in html:
                sel_ok = False
        text_ok = all(t in html for t in texts)
        if sel_ok and text_ok:
            ok += 1
    return 100.0 * ok / total if total else 0.0


def score_form(routes: list) -> float:
    posts = [r for r in routes if r.get("method") == "POST"]
    if not posts:
        # /bad 가 결과 테이블을 보여주면 폼 경로 대체 점수
        code, html = _get("/bad")
        if code == 200 and "확인 필요" in html and 'class="human"' in html:
            return 100.0
        return 0.0
    ok = 0
    for r in posts:
        code, html = _post(r["path"], r.get("body", {}))
        checks = r["checks"]
        if code != 200:
            continue
        if all(t in html for t in checks.get("required_text", [])) and "<table" in html:
            ok += 1
    return 100.0 * ok / len(posts)


def score_visual() -> float:
    """레이아웃·반응형·가독성 신호 (응답 HTML + CSS 문자열)."""
    code, html = _get("/")
    if code != 200:
        return 0.0
    src = SERVER.read_text(encoding="utf-8")
    pts = 0
    # viewport
    if "viewport" in html or "viewport" in src:
        pts += 20
    # responsive
    if "@media" in src:
        pts += 20
    # max-width container / shell
    if "max-width" in src:
        pts += 15
    # sticky or overflow for tables
    if "overflow" in src or "sticky" in src:
        pts += 15
    # distinct human column still marked
    if "human" in src and ("#fff2cc" in src or "human" in src):
        pts += 15
    # CTA button styled beyond bare
    if "button" in src and ("padding" in src or "background" in src):
        pts += 15
    return min(100.0, float(pts))


def score_design() -> float:
    """디자인 의도 신호 — Frozen checklist. 메트릭 정의를 바꾸지 말고 target CSS만 맞춘다."""
    src = SERVER.read_text(encoding="utf-8")
    # extract CSS + PAGE blobs roughly
    pts = 0.0
    checks = [
        (20, r"fonts\.googleapis|@import|font-family:[^;]*(Geist|IBM|Source|DM Sans|Newsreader|Fraunces|JetBrains|Space Grotesk|Noto Sans KR|Pretendard)"),
        (15, r"--[a-z-]+:"),  # CSS variables = intentional system
        (10, r"linear-gradient|radial-gradient"),
        (10, r"letter-spacing|text-transform:\s*uppercase"),
        (10, r"box-shadow|backdrop-filter"),
        (10, r"border-radius:\s*[4-9]px|border-radius:\s*1[0-2]px"),
        (10, r"class=\"(shell|hero|brand|panel|card|toolbar|badge)"),
        (5, r"prefers-color-scheme|color-scheme"),
        (5, r"focus-visible|:focus"),
        (5, r"grid-template|display:\s*grid"),
    ]
    for w, pat in checks:
        if re.search(pat, src, re.I):
            pts += w
    # penalties: known AI-default looks
    if re.search(r"#7c3aed|#8b5cf6|purple|indigo", src, re.I):
        pts -= 15
    if re.search(r"#[Ff]4[Ff]1[Ee][Aa]|terracotta|#c45[cC]26", src):
        pts -= 15
    return max(0.0, min(100.0, pts))


def main() -> int:
    weights = json.loads(WEIGHTS.read_text(encoding="utf-8"))
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    parts = {
        "error": score_error(),
        "dom": score_dom(routes),
        "form": score_form(routes),
        "visual": score_visual(),
        "design": score_design(),
    }
    total = sum(parts[k] * weights[k] for k in parts)
    out = {"score": round(total, 2), "parts": {k: round(v, 2) for k, v in parts.items()}, "weights": weights}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
