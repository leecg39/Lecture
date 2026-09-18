import { useEffect, useMemo, useRef, useState } from "react"
import { evaluateText, type Evaluation } from "./domain/pipeline.ts"
import {
  applyAllAuto,
  applyFix,
  draftFromRows,
  fitnessScore,
  issuePoNumber,
  suggestFixes,
  type FixSuggestion,
  type WorkingDraft,
} from "./domain/smart-fix.ts"
import type { FieldId } from "./domain/types.ts"
import {
  DEMO_TEXT,
  KS_PRESETS,
  SAMPLES,
  VAGUE_UNIT_SAMPLE,
  sampleById,
} from "./fixtures/samples.ts"
import { AutoCheckPanel } from "./ui/AutoCheckPanel.tsx"
import { DemoShell } from "./ui/DemoShell.tsx"
import { PreflightPanel } from "./ui/PreflightPanel.tsx"
import { SmartFixPanel } from "./ui/SmartFixPanel.tsx"
import { STAGES, type StageId } from "./ui/stages.ts"
import { SubmitPanel } from "./ui/SubmitPanel.tsx"

function runRule(text: string, docId: string): Evaluation {
  return evaluateText(text, docId)
}

export default function App() {
  const [stage, setStage] = useState<StageId>(0)
  const [sampleId, setSampleId] = useState("D04-13")
  const [text, setText] = useState(DEMO_TEXT)
  const [evalResult, setEvalResult] = useState<Evaluation>(() => runRule(DEMO_TEXT, "D04-13"))
  const [draft, setDraft] = useState<WorkingDraft>(() =>
    draftFromRows(runRule(DEMO_TEXT, "D04-13").check.rows),
  )
  const [inspectorOk, setInspectorOk] = useState(false)
  const [poNumber, setPoNumber] = useState<string | null>(null)
  const [supplier, setSupplier] = useState("")
  const [priority, setPriority] = useState("보통")
  const [checkNotice, setCheckNotice] = useState<string | null>(null)
  const [checkError, setCheckError] = useState<string | null>(null)
  const resultRef = useRef<HTMLElement | null>(null)

  const score = useMemo(
    () => fitnessScore(evalResult.check.rows, draft),
    [evalResult.check.rows, draft],
  )
  const fixes = useMemo(
    () => suggestFixes(evalResult.check.rows, draft),
    [evalResult.check.rows, draft],
  )

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target
      if (target instanceof HTMLElement) {
        const tag = target.tagName
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable) {
          return
        }
      }
      const hit = STAGES.find((item) => item.key === event.key)
      if (hit) setStage(hit.id)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  function resetFlow(nextText: string, id: string) {
    const next = runRule(nextText, id)
    setSampleId(id)
    setText(nextText)
    setEvalResult(next)
    setDraft(draftFromRows(next.check.rows))
    setInspectorOk(false)
    setPoNumber(null)
    setSupplier("")
    setPriority("보통")
    setCheckNotice(null)
    setCheckError(null)
    setStage(0)
  }

  function loadSample(id: string) {
    const sample = sampleById(id)
    if (!sample) return
    resetFlow(sample.text, id)
  }

  function loadVagueSample() {
    resetFlow(VAGUE_UNIT_SAMPLE, "MAN-02-vague")
  }

  function loadPreset(presetId: string) {
    const preset = KS_PRESETS.find((p) => p.id === presetId)
    if (!preset) return
    resetFlow(preset.text, preset.id)
  }

  /** 현재 원문으로 6대 항목 자동 체크를 다시 돌리고 1단계 결과를 보여 준다. */
  function recheck() {
    const source = text.replace(/\r\n/g, "\n")
    if (!source.trim()) {
      setCheckError("요청서 원문이 비어 있습니다. 내용을 입력한 뒤 다시 실행하세요.")
      setCheckNotice(null)
      return
    }

    const next = runRule(source, sampleId)
    const nextDraft = draftFromRows(next.check.rows)
    const nextScore = fitnessScore(next.check.rows, nextDraft)
    const defectCount = next.check.rows.filter((row) => row.needsCheck).length

    setText(source)
    setEvalResult(next)
    setDraft(nextDraft)
    setInspectorOk(false)
    setPoNumber(null)
    setCheckError(null)
    setCheckNotice(
      `자동 체크 완료 · 적합도 ${nextScore}/100 · 결함 ${defectCount}건 · ${new Date().toLocaleTimeString("ko-KR")}`,
    )
    setStage(0)

    requestAnimationFrame(() => {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    })
  }

  function onApplyOne(fix: FixSuggestion) {
    setDraft((d) => applyFix(d, fix))
    setInspectorOk(false)
    setPoNumber(null)
  }

  function onApplyAll() {
    setDraft((d) => applyAllAuto(d, fixes))
    setInspectorOk(false)
    setPoNumber(null)
  }

  function onManual(fieldId: FieldId, value: string) {
    setDraft((d) => ({
      ...d,
      [fieldId]: { value, origin: "수동", note: "현장 관리자 직접 입력" },
    }))
    setInspectorOk(false)
    setPoNumber(null)
  }

  function onSubmit() {
    if (!inspectorOk) return
    setPoNumber(issuePoNumber())
  }

  return (
    <div className="app">
      <DemoShell
        stage={stage}
        onStage={setStage}
        score={score}
        badge="현장관리자 › 발주 관리 › 신규 발주"
        onRecheck={recheck}
        onVagueSample={loadVagueSample}
      />
      <main className="layout">
        <section className="panel">
          <div className="panel-head">
            <h2>발주신청서 원문</h2>
            <p>표본 · KS 프리셋 · 모호 표현 테스트</p>
          </div>
          <div className="toolbar-row wrap">
            <label>
              표본{" "}
              <select
                value={sampleId}
                onChange={(e) => {
                  const id = e.target.value
                  if (KS_PRESETS.some((p) => p.id === id)) loadPreset(id)
                  else loadSample(id)
                }}
              >
                {SAMPLES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
                {KS_PRESETS.map((p) => (
                  <option key={p.id} value={p.id}>
                    KS · {p.label}
                  </option>
                ))}
              </select>
            </label>
            {KS_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                className="btn-outlined"
                onClick={() => loadPreset(p.id)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <textarea
            rows={6}
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              setCheckNotice(null)
              setCheckError(null)
            }}
            placeholder="발주신청서 원문을 붙여 넣으세요."
          />
          <div className="toolbar-row">
            <button
              type="button"
              className="btn-filled"
              data-action="recheck"
              onClick={recheck}
            >
              자동 체크 다시 실행
            </button>
            <button type="button" className="btn-ghost" onClick={loadVagueSample}>
              모호한 표현/틀린 단위 테스트용 샘플
            </button>
            <p className="muted">키보드 1–4로 단계 이동</p>
          </div>
          {checkError ? <p className="error">{checkError}</p> : null}
          {checkNotice ? <p className="ok-banner">{checkNotice}</p> : null}
        </section>

        {stage === 0 ? (
          <section ref={resultRef}>
            <AutoCheckPanel
              rows={evalResult.check.rows}
              draft={draft}
              score={score}
              sourceText={text}
            />
          </section>
        ) : null}
        {stage === 1 ? (
          <SmartFixPanel
            draft={draft}
            fixes={fixes}
            onApplyOne={onApplyOne}
            onApplyAll={onApplyAll}
            onManual={onManual}
          />
        ) : null}
        {stage === 2 ? (
          <PreflightPanel
            draft={draft}
            rows={evalResult.check.rows}
            inspectorOk={inspectorOk}
            onInspector={setInspectorOk}
          />
        ) : null}
        {stage === 3 ? (
          <SubmitPanel
            draft={draft}
            canSubmit={inspectorOk}
            poNumber={poNumber}
            supplier={supplier}
            priority={priority}
            onSupplier={setSupplier}
            onPriority={setPriority}
            onSubmit={onSubmit}
          />
        ) : null}
      </main>
      <footer className="footer">
        <p>건설 산업 조달 관리 시스템 (CPMS) v2.4 · MAN-02 · 교육용 가상 자료</p>
      </footer>
    </div>
  )
}
