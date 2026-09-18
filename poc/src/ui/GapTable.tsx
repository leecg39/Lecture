import { CRITICAL_FIELDS } from "../domain/catalog.ts"
import type { CheckRow, FieldId, HumanAction } from "../domain/types.ts"

type Props = {
  rows: CheckRow[]
  sourceText: string
  onHuman: (fieldId: FieldId, action: HumanAction) => void
  error: string | null
}

function needsClass(row: CheckRow): string {
  if (row.status === "충족") return "ok"
  if (row.status === "불일치") return "bad"
  return "warn"
}

export function GapTable({ rows, sourceText, onHuman, error }: Props) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>누락 표시표</h2>
        <p>원문 값 / 표준명 후보 / 확인 필요</p>
      </div>
      {error ? <p className="error">{error}</p> : null}
      <div className="table-wrap">
        <table className="gap-table">
          <thead>
            <tr>
              <th>항목</th>
              <th>상태</th>
              <th>원문 값</th>
              <th>표준명 후보</th>
              <th>확인 필요</th>
              <th>사람 확정</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.fieldId} className={needsClass(row)}>
                <td>
                  {row.fieldName}
                  {CRITICAL_FIELDS.has(row.fieldId) ? <span className="pill">중요</span> : null}
                </td>
                <td>{row.status}</td>
                <td className="mono">{row.sourceValue ?? "—"}</td>
                <td>{row.aliasCandidate ?? "—"}</td>
                <td>{row.needsCheck ? row.basis : "—"}</td>
                <td>
                  <div className="human-cell">
                    <span>{row.role.human || "비움"}</span>
                    <div className="row-actions">
                      {row.needsCheck ? (
                        <button
                          type="button"
                          onClick={() => onHuman(row.fieldId, { kind: "confirm_check" })}
                        >
                          확인 필요로 확정
                        </button>
                      ) : null}
                      {row.sourceValue && sourceText.includes(row.sourceValue) ? (
                        <button
                          type="button"
                          onClick={() =>
                            onHuman(row.fieldId, {
                              kind: "confirm_value",
                              value: row.sourceValue as string,
                            })
                          }
                        >
                          원문값 확정
                        </button>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => onHuman(row.fieldId, { kind: "reject" })}
                      >
                        제외
                      </button>
                      <button
                        type="button"
                        onClick={() => onHuman(row.fieldId, { kind: "clear" })}
                      >
                        비움
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
