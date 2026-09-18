import type { FixSuggestion, WorkingDraft } from "../domain/smart-fix.ts"
import { FIELD_ORDER, FIELD_NAMES } from "../domain/catalog.ts"

type Props = {
  draft: WorkingDraft
  fixes: FixSuggestion[]
  onApplyOne: (fix: FixSuggestion) => void
  onApplyAll: () => void
  onManual: (fieldId: FixSuggestion["fieldId"], value: string) => void
}

export function SmartFixPanel({ draft, fixes, onApplyOne, onApplyAll, onManual }: Props) {
  const autoCount = fixes.filter((f) => f.autoApplicable).length
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>2단계 · 스마트 수정</h2>
        <p>KS·용어사전 권장값 · 원클릭 또는 개별 적용</p>
      </div>
      <div className="toolbar-row">
        <button type="button" className="btn-filled" disabled={autoCount === 0} onClick={onApplyAll}>
          원클릭 일괄 자동 교정 ({autoCount})
        </button>
        <p className="muted">
          희망일은 날짜를 지어내지 않습니다. 정확한 연-월-일을 직접 입력하세요.
        </p>
      </div>
      {fixes.length === 0 ? (
        <p className="ok-banner">적용할 권장 교정이 없습니다. 사전 검수로 이동하세요.</p>
      ) : (
        <ul className="fix-list">
          {fixes.map((fix) => (
            <li key={`${fix.fieldId}-${fix.recommended}-${fix.reason}`}>
              <div>
                <strong>{fix.fieldName}</strong>
                <span className="mono">
                  {fix.current || "(없음)"} → {fix.recommended || "(직접 입력)"}
                </span>
                <p>{fix.reason}</p>
              </div>
              <div className="row-actions">
                {fix.autoApplicable ? (
                  <button type="button" onClick={() => onApplyOne(fix)}>
                    권장값 적용
                  </button>
                ) : (
                  <label className="inline-edit">
                    <span className="sr-only">{fix.fieldName} 직접 입력</span>
                    <input
                      type="text"
                      placeholder={
                        fix.fieldId === "need_date" ? "예: 2026-09-25" : fix.recommended
                      }
                      defaultValue={draft[fix.fieldId].value}
                      onBlur={(e) => {
                        const v = e.target.value.trim()
                        if (v) onManual(fix.fieldId, v)
                      }}
                    />
                  </label>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="table-wrap">
        <table className="gap-table">
          <thead>
            <tr>
              <th>항목</th>
              <th>현재 값</th>
              <th>출처</th>
            </tr>
          </thead>
          <tbody>
            {FIELD_ORDER.map((id) => (
              <tr key={id}>
                <td>{FIELD_NAMES[id]}</td>
                <td className="mono">{draft[id].value || "—"}</td>
                <td>{draft[id].origin}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
