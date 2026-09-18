import { itemsById } from "./catalog.ts"
import type { CheckResult, CheckRow } from "./types.ts"

function questionFor(row: CheckRow): string {
  const { fieldId, status, sourceValue: value, aliasCandidate: cand, basis } = row
  if (fieldId === "item_id") {
    if (status === "누락") {
      return "요청하신 자재의 품목 ID(P-NN) 또는 정확한 품명과 규격을 알려주세요."
    }
    if (status === "불일치") {
      return `품목 ID '${value}'가 자재 목록에 없습니다. 정확한 품목 ID를 확인해 주세요.`
    }
    if (basis.includes("판독")) {
      return `품목 ID 글자 '${value}'가 명확하지 않습니다. 정확한 품목 ID를 알려주세요.`
    }
    const lexicon = itemsById()
    const ids = String(cand ?? "").match(/P-\d{2}/g) ?? []
    const opts =
      ids
        .filter((id) => lexicon[id])
        .map((id) => `${id} ${lexicon[id].name} ${lexicon[id].spec}`)
        .join(" / ") || "자재 목록의 해당 품목"
    return `'${value}'은(는) ${opts} 중 어느 것인가요? 규격(예: 50A/100A)을 함께 알려주세요.`
  }
  if (fieldId === "qty") {
    return status === "누락"
      ? "필요 수량을 알려주세요."
      : `수량 '${value}' 글자가 명확하지 않습니다. 정확한 수량을 확인해 주세요.`
  }
  if (fieldId === "unit") {
    if (status === "누락") return `수량의 단위(${cand || "개/본/m/롤"})를 확인해 주세요.`
    if (status === "불일치") {
      return `이 품목의 표준 단위는 '${cand}'입니다. 요청하신 '${value}'이(가) 맞는지, 환산이 필요한지 확인해 주세요.`
    }
    return `품목이 확정되면 단위 '${value}'를 다시 확인하겠습니다. 품목 ID를 알려주세요.`
  }
  if (fieldId === "need_date") {
    if (status === "누락") return "희망 납기일을 날짜로 알려주세요(예: 2026-09-25)."
    if (status === "불일치") return `희망일 '${value}'이(가) 요청일 이전입니다. 날짜를 확인해 주세요.`
    if (basis.includes("판독")) {
      return `희망일 글자 '${value}'가 명확하지 않습니다. 정확한 날짜를 알려주세요.`
    }
    return `'${value}'는 구체적인 날짜가 아닙니다. 희망 납기일을 정확한 날짜(예: 2026-09-25)로 알려주세요.`
  }
  if (fieldId === "delivery_location") {
    if (status === "누락") return "배송 현장과 세부 위치(동·층·창고·게이트)를 알려주세요."
    return `'${value}' 내 세부 배송 위치(동·층·창고·게이트)를 알려주세요.`
  }
  if (status === "누락") return "규격(예: 50A/100A/12mm)을 알려주세요."
  if (status === "불일치") {
    return `품목 ID의 사전 규격은 '${cand}'인데 요청 규격은 '${value}'입니다. 어느 쪽이 맞는지 확인해 주세요.`
  }
  return `규격 글자 '${value}'가 명확하지 않습니다. 정확한 규격을 알려주세요.`
}

export function draftFollowups(result: CheckResult): CheckResult {
  const rows = result.rows.map((row) => {
    if (!row.needsCheck) return { ...row, followup: null }
    return { ...row, followup: questionFor(row) }
  })
  return {
    ...result,
    rows,
    followups: rows.flatMap((row) => (row.followup ? [row.followup] : [])),
  }
}
