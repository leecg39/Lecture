import type { CheckResult, GateViolation } from "../domain/types.ts"

type Props = {
  violations: GateViolation[]
  wrongCheck: CheckResult | null
}

export function FailureScene({ violations, wrongCheck }: Props) {
  const needs = wrongCheck?.needsCheckFields.length ?? 0
  return (
    <section className="panel failure">
      <div className="panel-head">
        <h2>실패 장면 · 잘못된 초안</h2>
        <p>그럴듯한 값이 원문 근거 없는 값이다</p>
      </div>
      <p className="stamp">제외</p>
      <p>
        같은 원문에서 AI가 <code>다음 주</code>를 <code>2026-09-24</code>로 바꾸고, 없는 창고와
        규격 50A를 채웠습니다. 규칙만 보면 확인 필요 {needs}건으로 통과할 수 있습니다. 게이트가
        막아 줍니다.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>코드</th>
              <th>항목</th>
              <th>지적</th>
            </tr>
          </thead>
          <tbody>
            {violations.map((item) => (
              <tr key={`${item.code}-${item.fieldId}-${item.detail}`}>
                <td className="mono">{item.code}</td>
                <td>{item.fieldId ?? "문서"}</td>
                <td>{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <label className="field">
        위험 한 줄
        <input defaultValue="원문에 없는 날짜·위치·규격을 채운 초안은 추가 문의 항목을 숨긴다." />
      </label>
    </section>
  )
}
