import { SAMPLES, type Sample } from "../fixtures/samples.ts"

type Props = {
  sampleId: string
  text: string
  paste: string
  usePaste: boolean
  onSample: (id: string) => void
  onText: (value: string) => void
  onPaste: (value: string) => void
  onUsePaste: (value: boolean) => void
  onRun: () => void
}

export function RequestPane({
  sampleId,
  text,
  paste,
  usePaste,
  onSample,
  onText,
  onPaste,
  onUsePaste,
  onRun,
}: Props) {
  return (
    <section className="panel request-pane">
      <div className="panel-head">
        <h2>요청서 원문</h2>
        <label className="toggle">
          <input
            type="checkbox"
            checked={usePaste}
            onChange={(event) => onUsePaste(event.target.checked)}
          />
          ChatGPT JSON 붙여넣기
        </label>
      </div>
      <label className="field">
        표본
        <select value={sampleId} onChange={(event) => onSample(event.target.value)}>
          {SAMPLES.map((sample: Sample) => (
            <option key={sample.id} value={sample.id}>
              {sample.id} · {sample.label}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        원문
        <textarea value={text} onChange={(event) => onText(event.target.value)} rows={8} />
      </label>
      {usePaste ? (
        <label className="field">
          추출 JSON
          <textarea
            value={paste}
            onChange={(event) => onPaste(event.target.value)}
            rows={8}
            placeholder='{"항목":[{"항목ID":"품목 ID","원문값":"P-01"}]}'
          />
        </label>
      ) : null}
      <button type="button" className="primary" onClick={onRun}>
        추출 후 규칙 검사
      </button>
    </section>
  )
}
