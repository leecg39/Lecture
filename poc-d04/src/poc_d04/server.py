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
body{font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;margin:24px;max-width:1200px;color:#222}
h1{font-size:20px} h2{font-size:16px;margin-top:28px}
textarea{width:100%;font-family:Menlo,monospace;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13px} th,td{border:1px solid #cfd8e3;padding:6px 8px;vertical-align:top}
th{background:#ddebf7;text-align:left} td.human{background:#fff2cc} td.flag{color:#b00020;font-weight:600}
.gate{background:#fde7e9;border-left:4px solid #b00020;padding:8px 12px;margin:6px 0}
.ok{background:#e6f4ea;border-left:4px solid #1e7e34;padding:8px 12px}
.warn{background:#fff8e1;border-left:4px solid #b26a00;padding:6px 12px;margin:4px 0}
.row{display:flex;gap:16px} .col{flex:1} pre{background:#f6f8fa;padding:10px;overflow:auto}
small{color:#555} button{padding:8px 16px;font-size:14px}
"""

PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>D04 PoC 데모 — 구매 요청서 누락 확인</title>
<style>{css}</style></head><body>
<h1>구매 요청서 누락 확인 — 문서에서 뽑고, 빈칸을 표시하고, 사람이 확정한다</h1>
<small>교육용 가상 자료 · 로컬 데모. 판단 기준: "문서 생성 성공"이 아니라 "추가 문의 항목을 찾았는가".</small>
<form method="post" action="/run">
<div class="row"><div class="col">
<h2>1. 요청서 원문</h2>
<label>표본 불러오기: <select name="doc" onchange="pick(this)">{options}</select></label>
<textarea id="text" name="text" rows="8" placeholder="A현장, 품목 P-01 20개, 다음 주 필요.">{text}</textarea>
</div><div class="col">
<h2>2. (선택) ChatGPT 출력 JSON</h2>
<small>비우면 규칙 추출기(오프라인)를 쓴다. 붙이면 그 출력을 검사한다. 코드블록 기호가 섞여도 된다.</small>
<textarea name="pasted" rows="8" placeholder='{{"항목":[{{"항목ID":"품목 ID","원문값":"P-01","원문발췌":"P-01"}}, ...]}}'>{pasted}</textarea>
</div></div>
<p><button type="submit">추출 → 규칙 검사 → 게이트 감사</button>
<a href="/bad" style="margin-left:16px">실패 장면 불러오기 (잘못된 초안)</a></p>
</form>
{result}
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
        out.append("<h2>누락 표시표</h2><table><tr><th>항목</th><th>원문 값</th><th>원문 위치</th><th>표준명 후보 (AI 제안)</th>"
                   "<th>상태 (규칙)</th><th>근거</th><th>보완 질문 초안 (AI 제안)</th><th>사람 확정</th></tr>")
        for it in res["항목"]:
            pos = f'{it["원문시작"]}–{it["원문끝"]}' if it["원문시작"] is not None else ""
            st = ("확인 필요 · " if it["확인필요"] else "") + it["상태"]
            out.append(f'<tr><td>{_e(it["항목명"])}</td><td>{_e(it["원문값"]) if it["원문값"] is not None else "<i>(없음)</i>"}</td>'
                       f'<td>{_e(pos)}</td><td>{_e(it["표준명후보"])}</td>'
                       f'<td class="{"flag" if it["확인필요"] else ""}">{_e(st)}</td><td>{_e(it["근거"])}</td>'
                       f'<td>{_e(it["보완질문"])}</td><td class="human"></td></tr>')
        out.append("</table>")
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
