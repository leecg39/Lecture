import type { CheckRow } from "../domain/types.ts"
import type { WorkingDraft } from "../domain/smart-fix.ts"
import { FIELD_ORDER, FIELD_NAMES } from "../domain/catalog.ts"

type Props = {
  rows: CheckRow[]
  draft: WorkingDraft
  score: number
  sourceText: string
}

export function AutoCheckPanel({ rows, draft, score, sourceText }: Props) {
  const defects = rows.filter((r) => r.needsCheck)
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>1단계 · 자동 체크</h2>
        <p>6대 필수 항목 실시간 전수 검사</p>
      </div>
      <div className="score-hero" data-tone={score >= 90 ? "ok" : score >= 50 ? "warn" : "bad"}>
        <span className="k">진단 적합도</span>
        <strong>{score}</strong>
        <span className="u">/ 100</span>
        <p>
          {defects.length === 0
            ? "필수 결함 없음 — 스마트 수정으로 표준화할 수 있습니다."
            : `결함 ${defects.length}건 · 누락·모호·단위 오류를 확인하세요.`}
        </p>
      </div>
      <div className="source-box">
        <h3>원문</h3>
        <pre>{sourceText}</pre>
      </div>
      <div className="table-wrap">
        <table className="gap-table">
          <thead>
            <tr>
              <th>항목</th>
              <th>상태</th>
              <th>원문 값</th>
              <th>작업 초안</th>
              <th>근거</th>
            </tr>
          </thead>
          <tbody>
            {FIELD_ORDER.map((id) => {
              const row = rows.find((r) => r.fieldId === id)
              const status = row?.status ?? "누락"
              const tone =
                status === "충족" ? "ok" : status === "불일치" ? "bad" : "warn"
              return (
                <tr key={id} className={tone}>
                  <td>{FIELD_NAMES[id]}</td>
                  <td>{status}</td>
                  <td className="mono">{row?.sourceValue ?? "—"}</td>
                  <td className="mono">{draft[id].value || "—"}</td>
                  <td>{row?.needsCheck ? row.basis : "—"}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
