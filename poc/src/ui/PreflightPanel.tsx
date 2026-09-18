import type { WorkingDraft } from "../domain/smart-fix.ts"
import { checklist } from "../domain/smart-fix.ts"
import type { CheckRow } from "../domain/types.ts"

type Props = {
  draft: WorkingDraft
  rows: CheckRow[]
  inspectorOk: boolean
  onInspector: (ok: boolean) => void
}

export function PreflightPanel({ draft, rows, inspectorOk, onInspector }: Props) {
  const items = checklist(draft, rows)
  const allOk = items.every((i) => i.ok)
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>3단계 · 사전 적합성 검수</h2>
        <p>6대 항목 종합 검수표 · 현장 공무담당자 확인</p>
      </div>
      <ul className="check-grid">
        {items.map((item) => (
          <li key={item.fieldId} className={item.ok ? "ok" : "bad"}>
            <span className="pill">{item.ok ? "승인" : "미달"}</span>
            <strong>{item.fieldName}</strong>
            <em>{item.detail}</em>
          </li>
        ))}
      </ul>
      <label className="inspector">
        <input
          type="checkbox"
          checked={inspectorOk}
          disabled={!allOk}
          onChange={(e) => onInspector(e.target.checked)}
        />
        <span>
          <b>검수 책임자 확인</b>
          {allOk
            ? " — 6대 항목 적합. 체크하면 4단계 발주요청이 활성화됩니다."
            : " — 미달 항목을 먼저 스마트 수정에서 보완하세요."}
        </span>
      </label>
    </section>
  )
}
