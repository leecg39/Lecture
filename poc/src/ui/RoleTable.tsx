import type { CheckRow } from "../domain/types.ts"

type Props = {
  rows: CheckRow[]
}

export function RoleTable({ rows }: Props) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>역할표</h2>
        <p>AI는 제안, 규칙은 판정, 확정은 사람</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>항목</th>
              <th>AI 제안</th>
              <th>규칙</th>
              <th>사람 확정</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.fieldId}>
                <td>{row.fieldName}</td>
                <td>{row.role.ai}</td>
                <td>{row.role.rule}</td>
                <td className={row.role.human ? "" : "muted"}>{row.role.human || "비움"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
