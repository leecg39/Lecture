import { describe, expect, it } from "vitest"
import { evaluateText } from "./pipeline.ts"
import {
  applyAllAuto,
  checklist,
  draftFromRows,
  fitnessScore,
  suggestFixes,
} from "./smart-fix.ts"

describe("smart-fix / MAN-02", () => {
  it("suggests unit and location fixes for demo text without inventing a date", () => {
    const text = "A현장, 품목 P-01 20개, 다음 주 필요."
    const { check } = evaluateText(text, "D04-13")
    const draft = draftFromRows(check.rows)
    const fixes = suggestFixes(check.rows, draft)
    expect(fixes.some((f) => f.fieldId === "item_id" && f.recommended.startsWith("MAT-"))).toBe(
      true,
    )
    expect(fixes.some((f) => f.fieldId === "spec" && f.recommended === "50A")).toBe(true)
    const dateFix = fixes.find((f) => f.fieldId === "need_date")
    expect(dateFix?.autoApplicable).toBe(false)
    expect(dateFix?.recommended).toBe("")
  })

  it("raises fitness after applying auto fixes", () => {
    const text = "A현장, 품목 P-01 20개, 다음 주 필요."
    const { check } = evaluateText(text, "D04-13")
    let draft = draftFromRows(check.rows)
    const before = fitnessScore(check.rows, draft)
    draft = applyAllAuto(draft, suggestFixes(check.rows, draft))
    const after = fitnessScore(check.rows, draft)
    expect(after).toBeGreaterThanOrEqual(before)
    expect(draft.spec.value).toBe("50A")
  })

  it("blocks preflight until date and gate location are concrete", () => {
    const text = "A현장, 품목 P-01 20개, 다음 주 필요."
    const { check } = evaluateText(text, "D04-13")
    let draft = draftFromRows(check.rows)
    draft = applyAllAuto(draft, suggestFixes(check.rows, draft))
    const mid = checklist(draft, check.rows)
    expect(mid.some((c) => !c.ok)).toBe(true)
    draft = {
      ...draft,
      need_date: { value: "2026-09-25", origin: "수동", note: "" },
      delivery_location: {
        value: "A현장 · 반입 게이트 B · 지하1층 자재창고 하역",
        origin: "수동",
        note: "",
      },
    }
    expect(checklist(draft, check.rows).every((c) => c.ok)).toBe(true)
  })
})
