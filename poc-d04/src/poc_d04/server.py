"""시연용 로컬 웹 데모 (표준 라이브러리 http.server, 외부 의존성 없음).

요청서 원문을 붙이면 추출 → 규칙 판정 → 게이트 감사 → 보완 질문을 표로 보여 준다.
ChatGPT 출력 JSON을 함께 붙이면 그 출력을 검사한다(붙여넣기 경로). 사람 확정 칸은 항상 비어 있다.
교육용 로컬 데모이며 운영 서버가 아니다. 기본으로 127.0.0.1에만 바인딩한다.
"""
from __future__ import annotations

import html
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .data_gen import load_dataset
from .evaluate import score
from .pipeline import run_doc

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{
  --ink:#1a2332; --muted:#5c6b7a; --paper:#f3f1ec; --panel:#fffcf7;
  --line:#d5d0c6; --brand:#0f3d3e; --brand-2:#1a5c5e; --accent:#c47a2c;
  --ok:#1f6b45; --ok-bg:#e4f2ea; --bad:#9b1c1c; --bad-bg:#f8e4e4;
  --warn:#8a5a12; --warn-bg:#f7edd8; --human:#f3e2b3; --human-ink:#6b4e10;
  --shadow:0 12px 40px rgba(26,35,50,.08); --radius:10px;
  color-scheme:light;
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh; color:var(--ink);
  font-family:'IBM Plex Sans KR',system-ui,sans-serif;
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(26,92,94,.12), transparent 55%),
    radial-gradient(900px 400px at 100% 0%, rgba(196,122,44,.10), transparent 50%),
    linear-gradient(180deg,#e8e4dc 0%, var(--paper) 40%, #ebe7df 100%);
}
.shell{max-width:1180px;margin:0 auto;padding:28px 22px 64px}
.hero{
  display:grid; gap:14px; margin-bottom:22px;
  padding:22px 24px; border:1px solid var(--line); border-radius:14px;
  background:linear-gradient(135deg,rgba(15,61,62,.96),rgba(26,92,94,.88));
  color:#f6f3ec; box-shadow:var(--shadow);
}
.brand{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.badge{
  font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:12px; font-weight:500;
  letter-spacing:.08em; text-transform:uppercase;
  padding:5px 10px; border-radius:999px; background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.22);
}
.hero h1{margin:0;font-size:clamp(22px,3vw,30px);line-height:1.25;font-weight:700;letter-spacing:-.02em}
.hero .lede{margin:0;max-width:52ch;color:rgba(246,243,236,.88);font-size:15px;line-height:1.55}
.criterion{
  display:inline-flex;gap:8px;align-items:flex-start;margin-top:4px;
  padding:10px 12px;border-radius:8px;background:rgba(0,0,0,.18);
  font-size:13px;line-height:1.45;
}
.criterion strong{color:#ffd79a}
.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:18px 0 8px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:860px){.row{grid-template-columns:1fr}.shell{padding:18px 14px 48px}}
.panel{
  background:var(--panel); border:1px solid var(--line); border-radius:var(--radius);
  padding:16px 16px 14px; box-shadow:var(--shadow);
}
.panel h2{margin:0 0 10px;font-size:15px;font-weight:600;letter-spacing:-.01em}
.panel .hint{display:block;margin:0 0 10px;color:var(--muted);font-size:12.5px;line-height:1.45}
label{font-size:13px;color:var(--muted)}
select,textarea,button,a.btn{
  font:inherit;
}
select{
  margin-left:6px; padding:7px 10px; border-radius:8px; border:1px solid var(--line);
  background:#fff; color:var(--ink); max-width:100%;
}
select:focus-visible,textarea:focus-visible,button:focus-visible,a:focus-visible{
  outline:2px solid var(--brand-2); outline-offset:2px;
}
textarea{
  width:100%; margin-top:8px; padding:12px; min-height:168px; resize:vertical;
  border:1px solid var(--line); border-radius:8px; background:#fff;
  font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:12.5px; line-height:1.45;
  color:var(--ink);
}
button,.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:11px 18px; border:0; border-radius:9px; cursor:pointer;
  background:var(--brand); color:#f7f4ee; font-weight:600; font-size:14px;
  text-decoration:none; box-shadow:0 1px 0 rgba(255,255,255,.15) inset;
}
button:hover,.btn:hover{background:var(--brand-2)}
a.linkish{color:var(--brand-2);font-weight:500;font-size:14px;margin-left:4px}
.results{margin-top:28px}
.results h2{margin:22px 0 10px;font-size:16px;font-weight:600}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:var(--radius);background:#fff;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:920px}
th,td{border-bottom:1px solid #e6e1d7;padding:9px 10px;vertical-align:top;text-align:left}
th{
  position:sticky;top:0;z-index:1; background:#eef3f3; color:var(--brand);
  font-weight:600; font-size:12px; letter-spacing:.02em;
}
th.human-h,td.human{
  background:var(--human); color:var(--human-ink); font-weight:600;
  box-shadow:inset 3px 0 0 var(--accent);
}
td.flag{color:var(--bad);font-weight:700}
.gate,.ok,.warn{
  border-radius:8px; padding:11px 14px; margin:8px 0; border:1px solid transparent;
  font-size:13.5px; line-height:1.45;
}
.gate{background:var(--bad-bg);border-color:#e2b4b4;border-left:4px solid var(--bad)}
.ok{background:var(--ok-bg);border-color:#b7d7c5;border-left:4px solid var(--ok)}
.warn{background:var(--warn-bg);border-color:#e2cfa5;border-left:4px solid var(--warn)}
pre{
  background:#1a2332; color:#e8eef2; padding:14px; border-radius:var(--radius);
  overflow:auto; font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:12px;
}
code{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:.92em}
.meta{color:var(--muted);font-size:13px}
"""

PAGE = """<!doctype html><html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>D04 PoC 데모 — 구매 요청서 누락 확인</title>
<style>{css}</style>
</head><body>
<div class="shell">
  <header class="hero">
    <div class="brand">
      <span class="badge">D04 · PoC</span>
      <span class="badge">건설 · 구매 요청</span>
    </div>
    <h1>구매 요청서 누락 확인</h1>
    <p class="lede">문서에서 뽑고, 빈칸을 표시하고, 사람이 확정한다. 교육용 가상 자료 · 로컬 시연 데모.</p>
    <div class="criterion">성공 기준: <strong>「문서 생성 성공」이 아니라 「추가 문의 항목을 찾았는가」</strong></div>
  </header>
  <form method="post" action="/run">
    <div class="row">
      <section class="panel">
        <h2>1. 요청서 원문</h2>
        <label>표본 불러오기 <select name="doc" onchange="pick(this)">{options}</select></label>
        <textarea id="text" name="text" rows="8" placeholder="A현장, 품목 P-01 20개, 다음 주 필요.">{text}</textarea>
      </section>
      <section class="panel">
        <h2>2. (선택) ChatGPT 출력 JSON</h2>
        <span class="hint">비우면 규칙 추출기(오프라인). 붙이면 그 출력을 검사. 코드블록 기호가 섞여도 됩니다.</span>
        <textarea name="pasted" rows="8" placeholder='{{"항목":[{{"항목ID":"품목 ID","원문값":"P-01","원문발췌":"P-01"}}, ...]}}'>{pasted}</textarea>
      </section>
    </div>
    <div class="toolbar">
      <button type="submit">추출 → 규칙 검사 → 게이트 감사</button>
      <a class="linkish" href="/bad">실패 장면 불러오기 (잘못된 초안)</a>
    </div>
  </form>
  <div class="results">{result}</div>
</div>
<script>
const S={samples};
function pick(sel){{ if(S[sel.value]) document.getElementById('text').value=S[sel.value]; }}
</script>
</body></html>"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


class Demo:
    def __init__(self, data_dir: Path = DATA):
        self.ds = load_dataset(data_dir) if (data_dir / "D04_원문위치_정답표.json").exists() else {"문서": {}, "정답": []}
        bad = ROOT / "examples" / "D04_잘못된초안_예시.json"
        self.bad = bad.read_text(encoding="utf-8") if bad.exists() else ""

    def page(self, text: str = "", pasted: str = "", result: str = "", selected: str = "") -> str:
        opts = ['<option value="">— 직접 입력 —</option>']
        for doc_id, d in self.ds["문서"].items():
            sel = " selected" if doc_id == selected else ""
            opts.append(f'<option value="{_e(doc_id)}"{sel}>{_e(doc_id)} · {_e(d["유형"])} · {_e(d["버전"])}</option>')
        samples = {k: v["원문"] for k, v in self.ds["문서"].items()}
        return PAGE.format(css=CSS, options="".join(opts), text=_e(text), pasted=_e(pasted), result=result,
                           samples=json.dumps(samples, ensure_ascii=False))

    def run(self, text: str, pasted: str, doc_id: str) -> str:
        text = text.replace("\r\n", "\n")
        if not text.strip():
            return '<div class="warn">요청서 원문이 비어 있습니다.</div>'
        backend = "paste" if pasted.strip() else "rule"
        try:
            r = run_doc(text, doc_id or None, backend, pasted if backend == "paste" else None)
        except ValueError as ex:
            return f'<div class="gate">{_e(ex)}</div>'
        res, viol, warn = r["판정"], r["게이트위반"], r["추출"].get("경고", [])
        out = [f"<h2>결과 · 백엔드 <code>{_e(backend)}</code></h2>"]
        for w in warn:
            out.append(f'<div class="warn">경고: {_e(w)}</div>')
        if viol:
            out.append('<h2>게이트 위반</h2>')
            for v in viol:
                out.append(f'<div class="gate"><b>{_e(v["코드"])}</b> · {_e(v["항목ID"] or "(문서)")} · {_e(v["설명"])}<br><small>{_e(v["게이트"])}</small></div>')
        else:
            out.append('<div class="ok">게이트 위반 없음 — 원문 없는 값을 채우지 않았다.</div>')
        out.append('<h2>누락 표시표</h2><div class="table-wrap"><table><tr><th>항목</th><th>원문 값</th><th>원문 위치</th><th>표준명 후보 (AI 제안)</th>'
                   '<th>상태 (규칙)</th><th>근거</th><th>보완 질문 초안 (AI 제안)</th><th class="human-h">사람 확정</th></tr>')
        for it in res["항목"]:
            pos = f'{it["원문시작"]}–{it["원문끝"]}' if it["원문시작"] is not None else ""
            st = ("확인 필요 · " if it["확인필요"] else "") + it["상태"]
            out.append(f'<tr><td>{_e(it["항목명"])}</td><td>{_e(it["원문값"]) if it["원문값"] is not None else "<i>(없음)</i>"}</td>'
                       f'<td>{_e(pos)}</td><td>{_e(it["표준명후보"])}</td>'
                       f'<td class="{"flag" if it["확인필요"] else ""}">{_e(st)}</td><td>{_e(it["근거"])}</td>'
                       f'<td>{_e(it["보완질문"])}</td><td class="human"></td></tr>')
        out.append("</table></div>")
        names = [it["항목명"] for it in res["항목"] if it["확인필요"]]
        out.append(f"<p><b>확인 필요 항목:</b> {_e(', '.join(names) or '없음')}</p>")
        qs = res.get("보완질문요약", [])
        if qs:
            out.append("<h2>보완 질문 초안</h2><ol>" + "".join(f"<li>{_e(q)}</li>" for q in qs) + "</ol>")
        if doc_id and doc_id in self.ds["문서"] and self.ds["문서"][doc_id]["원문"] == text:
            m = score({doc_id: res}, self.ds)["전체"]
            out.append(f"<h2>정답표 대조 ({_e(doc_id)})</h2><p>탐지 {m['탐지']}/{m['정답확인필요']} · 오탐 {m['오탐']} · "
                       f"중요 오류 {m['중요 오류']} · 상태 정확도 {m['상태 정확도']*100:.0f}%</p>")
            if m["미스"]:
                out.append("<table><tr><th>항목</th><th>정답</th><th>예측</th><th>정답 사유</th></tr>" + "".join(
                    f"<tr><td>{_e(x['항목'])}</td><td>{_e(x['정답'])}</td><td>{_e(x['예측'])}</td><td>{_e(x['정답사유'])}</td></tr>" for x in m["미스"]) + "</table>")
        out.append("<h2>추출 JSON</h2><pre>" + _e(json.dumps(r["추출"], ensure_ascii=False, indent=1)) + "</pre>")
        return "".join(out)


def make_handler(demo: Demo):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: str, status: int = 200):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            if url.path == "/":
                q = urllib.parse.parse_qs(url.query)
                doc = q.get("doc", [""])[0]
                text = demo.ds["문서"].get(doc, {}).get("원문", "")
                self._send(demo.page(text=text, selected=doc))
            elif url.path == "/bad":
                text = demo.ds["문서"].get("D04-13", {}).get("원문", "A현장, 품목 P-01 20개, 다음 주 필요.")
                result = demo.run(text, demo.bad, "D04-13")
                self._send(demo.page(text=text, pasted=demo.bad, result=result, selected="D04-13"))
            elif url.path == "/health":
                self._send("ok")
            else:
                self._send("not found", 404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
            text = form.get("text", [""])[0]
            pasted = form.get("pasted", [""])[0]
            doc = form.get("doc", [""])[0]
            result = demo.run(text, pasted, doc)
            self._send(demo.page(text=text, pasted=pasted, result=result, selected=doc))

        def log_message(self, fmt, *args):  # 조용히
            pass

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765, data_dir: Path = DATA) -> None:
    demo = Demo(data_dir)
    httpd = ThreadingHTTPServer((host, port), make_handler(demo))
    print(f"D04 PoC 데모 서버: http://{host}:{port}  (종료: Ctrl+C)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
