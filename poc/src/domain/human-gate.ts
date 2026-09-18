import type { CheckRow, GateResult, HumanAction } from "./types.ts"

export function valueInSource(sourceText: string, value: string): boolean {
  return sourceText.includes(value)
}

export function applyHumanAction(
  row: CheckRow,
  action: HumanAction,
  sourceText: string,
): GateResult {
  if (action.kind === "confirm_value") {
    if (!valueInSource(sourceText, action.value)) {
      return { ok: false, reason: "원문에 없는 값은 확정할 수 없습니다." }
    }
    return {
      ok: true,
      row: {
        ...row,
        role: { ...row.role, human: action.value },
      },
    }
  }
  if (action.kind === "confirm_check") {
    if (!row.needsCheck) {
      return { ok: false, reason: "확인 필요가 아닌 항목입니다." }
    }
    return {
      ok: true,
      row: {
        ...row,
        role: { ...row.role, human: "확인 필요로 확정" },
      },
    }
  }
  if (action.kind === "reject") {
    return {
      ok: true,
      row: {
        ...row,
        role: { ...row.role, human: "제외 (원문 없음)" },
      },
    }
  }
  return {
    ok: true,
    row: {
      ...row,
      role: { ...row.role, human: "" },
    },
  }
}

export function applyHumanToTable(
  rows: CheckRow[],
  fieldId: CheckRow["fieldId"],
  action: HumanAction,
  sourceText: string,
): { ok: true; rows: CheckRow[] } | { ok: false; reason: string; rows: CheckRow[] } {
  const target = rows.find((row) => row.fieldId === fieldId)
  if (!target) return { ok: false, reason: "해당 항목이 없습니다.", rows }
  const result = applyHumanAction(target, action, sourceText)
  if (!result.ok) return { ok: false, reason: result.reason, rows }
  return {
    ok: true,
    rows: rows.map((row) => (row.fieldId === fieldId ? result.row : row)),
  }
}
