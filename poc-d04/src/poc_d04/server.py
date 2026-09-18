"""시연용 로컬 웹 데모 (표준 라이브러리 http.server, 외부 의존성 없음).

요청서 원문을 붙이면 추출 → 규칙 판정 → 게이트 감사 → 보완 질문을 단계별 화면으로 보여 준다
(한 번에 계산하고, 화면에서는 한 단계씩 넘겨 본다).
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
from .gate import GATE_TEXT
from .pipeline import run_doc

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{
  --ink:#121820; --muted:#3f4c59; --paper:#f3f1ec; --panel:#fffcf7;
  --line:#d5d0c6; --brand:#0f3d3e; --brand-2:#1a5c5e; --accent:#c47a2c;
  --ok:#1f6b45; --ok-bg:#e4f2ea; --bad:#9b1c1c; --bad-bg:#f8e4e4;
  --warn:#8a5a12; --warn-bg:#f7edd8; --human:#f3e2b3; --human-ink:#6b4e10;
  --shadow:0 12px 40px rgba(26,35,50,.08); --radius:10px;
  color-scheme:light;
}
*{box-sizing:border-box}
html{scroll-padding-top:56px;scroll-padding-bottom:72px}
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
.hero h1{margin:0;font-size:clamp(26px,4vw,36px);line-height:1.25;font-weight:700;letter-spacing:-.02em}
.hero .lede{margin:0;max-width:52ch;color:rgba(246,243,236,.88);font-size:17px;line-height:1.55}
.criterion{
  display:inline-flex;gap:8px;align-items:flex-start;margin-top:4px;
  padding:12px 14px 12px 16px;border-radius:8px;background:rgba(0,0,0,.18);
  font-size:15px;line-height:1.45; border-left:4px solid #ffd79a;
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
  padding:13px 20px; border:0; border-radius:9px; cursor:pointer;
  background:var(--brand); color:#f7f4ee; font-weight:600; font-size:16px;
  text-decoration:none; box-shadow:0 1px 0 rgba(255,255,255,.15) inset;
}
button:hover,.btn:hover{background:var(--brand-2)}
a.linkish{color:var(--brand-2);font-weight:500;font-size:14px;margin-left:4px}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:var(--radius);background:#fff;box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:15px;min-width:920px}
th,td{border-bottom:1px solid #e6e1d7;padding:11px 12px;vertical-align:top;text-align:left}
th{
  position:sticky;top:0;z-index:1; background:#eef3f3; color:var(--brand);
  font-weight:600; font-size:13px; letter-spacing:.02em;
}
th.human-h,td.human{
  background:var(--human); color:var(--human-ink); font-weight:700;
  box-shadow:inset 6px 0 0 var(--accent);
  min-width:7.5rem;
}
th.human-h::after{
  content:" · 비움";
  font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  font-weight:600; opacity:.85;
}
td.flag{color:var(--bad);font-weight:700}
tr:has(td.flag){background:#fbf3ea}
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
.summary-strip{
  display:flex;flex-wrap:wrap;gap:10px;margin:8px 0 18px;padding:12px;
  border:1px solid var(--line);border-radius:12px;background:#fff;box-shadow:var(--shadow);
}
.chip{
  display:flex;flex-direction:column;gap:2px;min-width:120px;
  padding:8px 12px;border-radius:9px;background:#f0eeea;border:1px solid var(--line);
}
.chip .k{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600}
.chip .v{font-size:16px;font-weight:600;color:var(--ink)}
.chip.good{background:var(--ok-bg);border-color:#b7d7c5}
.chip.bad{background:var(--bad-bg);border-color:#e2b4b4}
.chip.hot{background:#fff1df;border-color:#e7c48a}
.chip.hot .v,.chip.bad .v{color:var(--bad)}
.results-h{margin:22px 0 10px;font-size:16px;font-weight:600}
.gate-list{display:grid;gap:8px}
.gate{display:flex;gap:12px;align-items:flex-start}
.gate-code{
  flex:0 0 auto;font-family:'IBM Plex Mono',ui-monospace,monospace;font-weight:700;
  font-size:16px;padding:6px 10px;border-radius:6px;background:#fff;border:1px solid #e2b4b4;color:var(--bad);
}
.gate-rule{margin-top:4px;color:var(--muted);font-size:12px}
.verdict{
  display:flex;gap:14px;align-items:flex-start;margin:0 0 12px;padding:14px 16px;
  border-radius:var(--radius);border:1px solid transparent;font-size:15px;line-height:1.5;box-shadow:var(--shadow);
}
.verdict .vk{
  flex:0 0 auto;font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;font-weight:700;padding:4px 8px;border-radius:6px;background:#fff;margin-top:2px;
}
.verdict b{font-size:17px;letter-spacing:-.01em}
.verdict small{display:block;margin-top:4px;font-size:12.5px;opacity:.85}
.verdict.bad{background:var(--bad-bg);border-color:#e2b4b4;color:var(--bad);border-left:5px solid var(--bad)}
.verdict.bad .vk{color:var(--bad);border:1px solid #e2b4b4}
.verdict.ok{background:var(--ok-bg);border-color:#b7d7c5;color:var(--ok);border-left:5px solid var(--ok)}
.verdict.ok .vk{color:var(--ok);border:1px solid #b7d7c5}
.source{border:1px solid var(--line);border-radius:var(--radius);background:#fff;box-shadow:var(--shadow);overflow:hidden}
.source-text{
  margin:0;padding:16px 18px;background:#fff;color:var(--ink);white-space:pre-wrap;word-break:break-word;
  font-family:'IBM Plex Sans KR',system-ui,sans-serif;font-size:16px;line-height:2;border-radius:0;
}
.source-text mark{
  position:relative;background:#e4f2ea;color:var(--ok);padding:2px 4px;border-radius:4px;
  box-shadow:inset 0 -2px 0 var(--ok);font-weight:600;
}
.source-text mark .tag{
  position:absolute;left:0;top:-13px;font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:9.5px;
  line-height:1;color:var(--ok);font-weight:600;letter-spacing:.02em;white-space:nowrap;
}
.source-miss,.source-ok{padding:9px 14px;font-size:13px;border-top:1px solid var(--line)}
.source-miss{background:var(--bad-bg);color:var(--bad)}
.source-ok{background:var(--ok-bg);color:var(--ok)}
.gate-body{flex:1 1 auto;min-width:0}
.gate-action{
  display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;margin-top:8px;padding:8px 10px;
  border-radius:6px;background:rgba(255,255,255,.7);border:1px dashed #e2b4b4;font-size:12.5px;color:var(--ink);
}
.gate-action .k{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--bad);font-weight:700}
.gate-action .owner{margin-left:auto;font-weight:600;color:var(--brand)}
.roles{
  display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:16px;padding:10px 14px;
  border:1px solid var(--line);border-radius:var(--radius);background:#fff;font-size:13px;
}
.roles .k{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
.roles .role{display:flex;flex-direction:column;gap:1px;font-weight:600;color:var(--brand)}
.roles .role small{font-weight:400;color:var(--muted);font-size:11.5px}
.roles .arr{color:var(--accent);font-weight:700}
table.gate-check{min-width:0}
table.gate-check td:first-child{white-space:nowrap;font-weight:700}
.pill{
  display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700;
  border:1px solid transparent;white-space:nowrap;
}
.pill.ok{background:var(--ok-bg);color:var(--ok);border-color:#b7d7c5}
.pill.bad{background:var(--bad-bg);color:var(--bad);border-color:#e2b4b4}
.qlist{margin:0;padding-left:1.2rem;line-height:1.55}
.json-box{margin-top:18px;border:1px solid var(--line);border-radius:var(--radius);background:#fff;padding:8px 12px}
.json-box summary{cursor:pointer;font-weight:600;color:var(--brand)}
.json-box pre{margin:10px 0 4px}
/* 단계 진행 UI */
.stepper{
  display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 14px;padding:8px 0;
  list-style:none; position:sticky; top:0; z-index:5;
  background:linear-gradient(180deg,rgba(243,241,236,.97),rgba(243,241,236,.92));
  backdrop-filter:blur(8px);
}
.stepper li{
  display:flex;align-items:center;gap:8px;padding:8px 16px 8px 10px;border-radius:999px;
  border:1px solid var(--line);background:#fff;font-size:14px;font-weight:600;color:var(--muted);
  cursor:pointer;user-select:none;transition:background .15s,color .15s;
}
@media (prefers-reduced-motion:reduce){
  .stepper li{transition:none}
  html{scroll-behavior:auto}
}
.stepper li .n{
  display:inline-flex;width:22px;height:22px;border-radius:50%;align-items:center;justify-content:center;
  background:#e9e5dc;font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:12px;color:var(--ink);
}
.stepper li.active{background:var(--brand);color:#f7f4ee;border-color:var(--brand)}
.stepper li.active .n{background:rgba(255,255,255,.2);color:#fff}
.stepper li.done{color:var(--brand);border-color:#b7d7c5}
.stepper li.done .n{background:var(--ok-bg);color:var(--ok)}
.stepper li.locked{opacity:.45;cursor:not-allowed}
.stepper li .arrow{color:var(--line);margin:0 2px;font-size:12px}
.step[hidden]{display:none}
.step-title{display:flex;align-items:baseline;gap:10px;margin:0 0 6px}
.step-title .k{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:12px;color:var(--accent);font-weight:600;letter-spacing:.06em}
.step-title h2{margin:0;font-size:20px;font-weight:700;letter-spacing:-.01em}
.step-desc{margin:0 0 14px;color:var(--muted);font-size:13.5px;line-height:1.5}
.step .results-h{margin-top:16px}
.step-nav{
  display:flex;justify-content:space-between;align-items:center;gap:12px;
  position:sticky; bottom:0; z-index:4;
  margin-top:22px; padding:12px 0 10px;
  border-top:1px solid var(--line);
  background:linear-gradient(180deg,rgba(243,241,236,.2),rgba(243,241,236,.96) 28%);
}
.step-nav[hidden]{display:none}
button.ghost,a.btn.ghost{background:transparent;color:var(--brand);border:1px solid var(--line);box-shadow:none}
button.ghost:hover,a.btn.ghost:hover{background:#fff}
button:disabled,button:disabled:hover{opacity:.4;cursor:not-allowed;background:var(--brand)}
button.ghost:disabled,button.ghost:disabled:hover{background:transparent}
.kbd-hint{color:var(--muted);font-size:12px}
.kbd-hint kbd{font-family:'IBM Plex Mono',ui-monospace,monospace;border:1px solid var(--line);border-radius:4px;padding:0 5px;background:#fff}
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
  <ol class="stepper" id="stepper" aria-label="진행 단계">
    <li data-step="0"><span class="n">1</span>입력</li>
    <li data-step="1"><span class="n">2</span>추출</li>
    <li data-step="2"><span class="n">3</span>규칙 검사</li>
    <li data-step="3"><span class="n">4</span>게이트 감사</li>
    <li data-step="4"><span class="n">5</span>보완 질문 · 확정</li>
  </ol>
  <section class="step" data-step="0">
    <div class="step-title"><span class="k">STEP 1</span><h2>요청서 입력</h2></div>
    <p class="step-desc">요청서 원문을 붙이거나 표본을 고른다. ChatGPT 출력 JSON을 함께 붙이면 그 출력을 검사한다.</p>
    <form method="post" action="/run">
      <div class="row">
        <section class="panel">
          <h2>요청서 원문</h2>
          <label>표본 불러오기 <select name="doc" onchange="pick(this)">{options}</select></label>
          <textarea id="text" name="text" rows="8" placeholder="A현장, 품목 P-01 20개, 다음 주 필요.">{text}</textarea>
        </section>
        <section class="panel">
          <h2>(선택) ChatGPT 출력 JSON</h2>
          <span class="hint">비우면 규칙 추출기(오프라인). 붙이면 그 출력을 검사. 코드블록 기호가 섞여도 됩니다.</span>
          <textarea name="pasted" rows="8" placeholder='{{"항목":[{{"항목ID":"품목 ID","원문값":"P-01","원문발췌":"P-01"}}, ...]}}'>{pasted}</textarea>
        </section>
      </div>
      <div class="toolbar">
        <button type="submit">실행 → 단계별로 보기</button>
        <a class="btn ghost" href="/bad#step-3">실패 장면 불러오기</a>
      </div>
    </form>
    {notice}
  </section>
  {result}
  <nav class="step-nav" id="stepnav" hidden>
    <button type="button" class="ghost" id="prev">← 이전</button>
    <span class="kbd-hint"><span id="stepinfo"></span> · <kbd>←</kbd> <kbd>→</kbd> · <kbd>1</kbd>–<kbd>5</kbd></span>
    <button type="button" id="next">다음 →</button>
  </nav>
</div>
<script>
const S={samples};
function pick(sel){{ if(S[sel.value]) document.getElementById('text').value=S[sel.value]; }}
(function(){{
  const steps=[...document.querySelectorAll('.step')];
  const items=[...document.querySelectorAll('#stepper li')];
  const has=steps.length>1, last=steps.length-1;
  const nav=document.getElementById('stepnav'), prev=document.getElementById('prev'),
        next=document.getElementById('next'), info=document.getElementById('stepinfo');
  let cur=has?1:0;
  const m=location.hash.match(/^#step-([0-9]+)$/);
  if(m&&+m[1]<=last) cur=+m[1];
  else if(has && location.pathname==='/bad') cur=Math.min(3,last);
  function go(n,scroll){{
    cur=n;
    steps.forEach(s=>{{ s.hidden=(+s.dataset.step!==n); }});
    items.forEach(li=>{{
      const k=+li.dataset.step;
      li.classList.toggle('active',k===n);
      li.classList.toggle('done',has&&k<n);
      li.classList.toggle('locked',!has&&k>0);
      li.setAttribute('aria-current',k===n?'step':'false');
    }});
    nav.hidden=!has;
    prev.disabled=(n===0);
    next.textContent = n===last ? '처음으로 (입력)' : (n===0 ? '결과 보기 →' : '다음 →');
    info.textContent=`${{n+1}} / ${{last+1}}`;
    history.replaceState(null,'','#step-'+n);
    if(scroll) document.getElementById('stepper').scrollIntoView({{behavior:'smooth',block:'start'}});
  }}
  items.forEach(li=>li.addEventListener('click',()=>{{ const k=+li.dataset.step; if(k===0||has) go(k,true); }}));
  prev.onclick=()=>go(Math.max(0,cur-1),true);
  next.onclick=()=>go(cur===last?0:cur+1,true);
  document.addEventListener('keydown',e=>{{
    if(e.target.matches('textarea,select,input')) return;
    if(e.key==='ArrowRight'&&has&&cur<last) go(cur+1,true);
    if(e.key==='ArrowLeft'&&cur>0) go(cur-1,true);
    if(e.key>='1'&&e.key<='5'){{
      const k=+e.key-1;
      if(k<=last && (k===0||has)) go(k,true);
    }}
  }});
  go(cur,false);
}})();
</script>
</body></html>"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _highlight(text: str, items: list[dict]) -> tuple[str, int, int]:
    """원문에 추출 위치를 <mark>로 표시. (HTML, 위치 있는 값 수, 값 있는 항목 수)를 돌려준다.

    겹치는 구간은 앞선 것만 표시한다(값을 고치지 않고 보여 주기만 한다).
    """
    spans = []
    valued = traced = 0
    for it in items:
        if it.get("원문값") is None:
            continue
        valued += 1
        s, e = it.get("원문시작"), it.get("원문끝")
        if isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= len(text):
            traced += 1
            spans.append((s, e, it.get("항목명") or it.get("항목ID") or ""))
    spans.sort()
    out, pos = [], 0
    for s, e, name in spans:
        if s < pos:
            continue
        out.append(_e(text[pos:s]))
        out.append(f'<mark title="{_e(name)}">{_e(text[s:e])}<span class="tag">{_e(name)}</span></mark>')
        pos = e
    out.append(_e(text[pos:]))
    return "".join(out), traced, valued


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
        # 단계 섹션이 들어 있으면 결과 단계로, 아니면(오류·빈 입력) 입력 단계 안에 알림으로 표시
        is_steps = 'class="step"' in result
        return PAGE.format(css=CSS, options="".join(opts), text=_e(text), pasted=_e(pasted),
                           result=result if is_steps else "", notice="" if is_steps else result,
                           samples=json.dumps(samples, ensure_ascii=False))

    @staticmethod
    def _step(n: int, title: str, desc: str, body: list[str]) -> str:
        return (
            f'<section class="step" data-step="{n}" hidden>'
            f'<div class="step-title"><span class="k">STEP {n + 1}</span><h2>{title}</h2></div>'
            f'<p class="step-desc">{desc}</p>' + "".join(body) + "</section>"
        )

    def run(self, text: str, pasted: str, doc_id: str) -> str:
        text = text.replace("\r\n", "\n")
        if not text.strip():
            return '<div class="warn">요청서 원문이 비어 있습니다.</div>'
        backend = "paste" if pasted.strip() else "rule"
        try:
            r = run_doc(text, doc_id or None, backend, pasted if backend == "paste" else None)
        except ValueError as ex:
            return f'<div class="gate">{_e(ex)}</div>'
        ex_items = r["추출"].get("항목", [])
        res, viol, warn = r["판정"], r["게이트위반"], r["추출"].get("경고", [])
        need = [it["항목명"] for it in res["항목"] if it["확인필요"]]
        found = sum(1 for it in ex_items if it.get("원문값") is not None)

        # ── STEP 2. 추출 ──────────────────────────────────────────────
        s1 = [
            '<div id="result-anchor" class="summary-strip">',
            f'<div class="chip"><span class="k">백엔드</span><span class="v">{_e(backend)}</span></div>',
            f'<div class="chip"><span class="k">원문에서 찾은 값</span><span class="v">{found} / {len(ex_items)} 항목</span></div>',
            f'<div class="chip {"hot" if warn else "good"}"><span class="k">경고</span><span class="v">{len(warn)}건</span></div>',
            "</div>",
        ]
        for w in warn:
            s1.append(f'<div class="warn">경고: {_e(w)}</div>')
        s1.append(
            '<div class="table-wrap"><table><tr>'
            "<th>항목</th><th>원문 값</th><th>원문 위치</th><th>표준명 후보 (AI 제안)</th><th>메모</th></tr>"
        )
        for it in ex_items:
            pos = f'{it["원문시작"]}–{it["원문끝"]}' if it.get("원문시작") is not None else ""
            s1.append(
                f'<tr><td>{_e(it["항목명"])}</td>'
                f'<td>{_e(it["원문값"]) if it.get("원문값") is not None else "<i>(없음)</i>"}</td>'
                f'<td>{_e(pos)}</td><td>{_e(it.get("표준명후보"))}</td><td>{_e(it.get("메모"))}</td></tr>'
            )
        s1.append("</table></div>")
        s1.append(
            '<details class="json-box"><summary>추출 JSON</summary><pre>'
            + _e(json.dumps(r["추출"], ensure_ascii=False, indent=1))
            + "</pre></details>"
        )

        # ── STEP 3. 규칙 검사 → 누락 표시표 ──────────────────────────
        s2 = [
            '<div class="summary-strip">',
            f'<div class="chip {"hot" if need else "good"}"><span class="k">확인 필요</span><span class="v">{_e(", ".join(need) or "없음")}</span></div>',
            '<div class="chip"><span class="k">사람 확정</span><span class="v">표 마지막 열 · 비움</span></div>',
            "</div>",
            '<div class="table-wrap"><table><tr>'
            "<th>항목</th><th>원문 값</th><th>원문 위치</th><th>표준명 후보 (AI 제안)</th>"
            '<th>상태 (규칙)</th><th>근거</th><th>보완 질문 초안 (AI 제안)</th>'
            '<th class="human-h">사람 확정</th></tr>',
        ]
        for it in res["항목"]:
            pos = f'{it["원문시작"]}–{it["원문끝"]}' if it["원문시작"] is not None else ""
            st = ("확인 필요 · " if it["확인필요"] else "") + it["상태"]
            s2.append(
                f'<tr><td>{_e(it["항목명"])}</td>'
                f'<td>{_e(it["원문값"]) if it["원문값"] is not None else "<i>(없음)</i>"}</td>'
                f'<td>{_e(pos)}</td><td>{_e(it["표준명후보"])}</td>'
                f'<td class="{"flag" if it["확인필요"] else ""}">{_e(st)}</td>'
                f'<td>{_e(it["근거"])}</td><td>{_e(it["보완질문"])}</td>'
                '<td class="human"></td></tr>'
            )
        s2.append("</table></div>")
        s2.append(f'<p class="meta"><b>확인 필요 항목:</b> {_e(", ".join(need) or "없음")}</p>')

        # ── STEP 4. 게이트 감사 ───────────────────────────────────────
        by_code: dict[str, list[dict]] = {}
        for v in viol:
            by_code.setdefault(v["코드"], []).append(v)
        marked, traced, valued = _highlight(text, ex_items)
        trace_pct = f"{traced / valued * 100:.0f}%" if valued else "해당 없음"
        untraced = [it["항목명"] for it in ex_items
                    if it.get("원문값") is not None and it.get("원문시작") is None]
        owners = sorted({v["담당"] for v in viol if v.get("담당")})
        if viol:
            verdict = (
                '<div class="verdict bad"><span class="vk">판정</span><div>'
                f'<b>재시험</b> — 게이트 위반 {len(viol)}건. 원문 없는 값을 삭제하고 '
                f'{_e(" · ".join(owners)) or "담당자"}에게 확인한 뒤 다시 검사한다.'
                '<small>중요 오류가 있으면 결과를 사람 확정으로 넘기지 않는다 (성공·수정·중단 기준).</small></div></div>'
            )
        else:
            verdict = (
                '<div class="verdict ok"><span class="vk">판정</span><div>'
                '<b>계속</b> — 게이트 위반 0건. 규칙 검사 결과를 그대로 사람 확정 단계로 넘긴다.'
                '<small>AI 초안은 제안일 뿐이며 확정은 다음 단계에서 사람이 한다.</small></div></div>'
            )
        s3 = [
            verdict,
            '<div class="summary-strip">',
            f'<div class="chip {"bad" if viol else "good"}"><span class="k">게이트</span><span class="v">{len(viol)}건 위반</span></div>',
            f'<div class="chip {"good" if not viol else ""}"><span class="k">지시 대조</span>'
            f'<span class="v">{len(GATE_TEXT) - len(by_code)} / {len(GATE_TEXT)} 통과</span></div>',
            f'<div class="chip {"good" if valued and traced == valued else "bad"}"><span class="k">원문 추적</span>'
            f'<span class="v">{traced} / {valued} · {trace_pct}</span></div>',
            "</div>",
            '<h2 class="results-h">원문 근거</h2>',
            f'<div class="source"><pre class="source-text">{marked}</pre>'
            + (f'<div class="source-miss">원문에서 위치를 찾지 못한 값: <b>{_e(", ".join(untraced))}</b></div>' if untraced
               else '<div class="source-ok">값이 있는 항목 모두 원문 위치가 있다.</div>')
            + "</div>",
            '<h2 class="results-h">지시 ↔ 결과 대조</h2>',
            '<div class="table-wrap"><table class="gate-check"><tr><th>코드</th><th>AI에 준 지시</th><th>결과</th></tr>',
        ]
        for code, rule in GATE_TEXT.items():
            hits = by_code.get(code, [])
            status = (f'<span class="pill bad">위반 {len(hits)}건</span>' if hits
                      else '<span class="pill ok">통과</span>')
            s3.append(f'<tr><td><code>{_e(code)}</code></td><td>{_e(rule)}</td><td>{status}</td></tr>')
        s3.append("</table></div>")
        if viol:
            s3.append('<h2 class="results-h">위반 상세 · 권고 조치</h2><div class="gate-list">')
            for v in viol:
                s3.append(
                    f'<div class="gate"><span class="gate-code"><b>{_e(v["코드"])}</b></span>'
                    f'<div class="gate-body"><div><span class="gate-item">{_e(v["항목ID"] or "(문서)")}</span> · {_e(v["설명"])}</div>'
                    f'<div class="gate-rule">{_e(v["게이트"])}</div>'
                    f'<div class="gate-action"><span class="k">조치</span>{_e(v.get("조치"))}'
                    f'<span class="owner">확인 담당 · {_e(v.get("담당"))}</span></div></div></div>'
                )
            s3.append("</div>")
        else:
            s3.append('<div class="ok">게이트 위반 없음 — 원문 없는 값을 채우지 않았다.</div>')
        s3.append(
            '<div class="roles"><span class="k">확정 흐름</span>'
            '<span class="role">AI 초안 <small>추출·질문 제안 · 확정하지 않음</small></span><span class="arr">→</span>'
            '<span class="role">현장 담당자 <small>희망일·수령 위치 확인</small></span><span class="arr">→</span>'
            '<span class="role">본사 구매·지원팀 <small>필수 기준·원문 대조 후 최종 확인</small></span></div>'
        )

        # ── STEP 5. 보완 질문 · 사람 확정 ────────────────────────────
        qs = res.get("보완질문요약", [])
        s4 = []
        if qs:
            s4.append('<h2 class="results-h">보완 질문 초안 (AI 제안)</h2><ol class="qlist">'
                      + "".join(f"<li>{_e(q)}</li>" for q in qs) + "</ol>")
        else:
            s4.append('<div class="ok">추가로 물을 항목이 없다.</div>')
        s4.append(
            '<div class="warn">사람 확정: 위 질문을 요청자에게 보내 답을 받은 뒤, 누락 표시표의 '
            "<b>사람 확정</b> 열을 사람이 채운다. AI 제안은 확정이 아니다.</div>"
        )
        if doc_id and doc_id in self.ds["문서"] and self.ds["문서"][doc_id]["원문"] == text:
            m = score({doc_id: res}, self.ds)["전체"]
            s4.append(f'<h2 class="results-h">정답표 대조 ({_e(doc_id)})</h2>')
            s4.append(
                f'<p class="meta">탐지 {m["탐지"]}/{m["정답확인필요"]} · 오탐 {m["오탐"]} · '
                f'중요 오류 {m["중요 오류"]} · 상태 정확도 {m["상태 정확도"]*100:.0f}%</p>'
            )
            if m["미스"]:
                s4.append(
                    '<div class="table-wrap"><table><tr><th>항목</th><th>정답</th><th>예측</th><th>정답 사유</th></tr>'
                    + "".join(
                        f"<tr><td>{_e(x['항목'])}</td><td>{_e(x['정답'])}</td>"
                        f"<td>{_e(x['예측'])}</td><td>{_e(x['정답사유'])}</td></tr>"
                        for x in m["미스"]
                    )
                    + "</table></div>"
                )

        return (
            self._step(1, "추출", f"원문에서 값을 뽑는다. 백엔드 <code>{_e(backend)}</code> · 원문에 없는 값은 만들지 않는다.", s1)
            + self._step(2, "규칙 검사 → 누락 표시표", "뽑은 값에 규칙을 적용해 빈칸·모호 표현을 표시한다. 마지막 열은 사람이 채운다.", s2)
            + self._step(3, "게이트 감사", "AI에 준 지시와 결과를 대조한다 — 원문 없는 값, 모호 표현 단정, 사람 확정 칸 선점, 범위 밖 일. 위반은 조치·담당과 함께 표시한다.", s3)
            + self._step(4, "보완 질문 · 사람 확정", "확인이 필요한 항목마다 요청자에게 보낼 질문 초안을 만든다.", s4)
        )


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
