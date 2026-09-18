import { describe, expect, it } from "vitest"
import { DEMO_TEXT } from "../fixtures/samples.ts"
import { evaluateText } from "./pipeline.ts"

describe("follow-up questions", () => {
  it("asks only about needs-check fields and quotes the source phrase", () => {
    const { check } = evaluateText(DEMO_TEXT, "D04-13")
    expect(check.needsCheckFields).toEqual(["need_date", "delivery_location"])
    expect(check.followups).toHaveLength(2)
    expect(check.followups[0]).toContain("다음 주")
    expect(check.followups[1]).toContain("A현장")
    const filled = check.rows.filter((row) => !row.needsCheck)
    expect(filled.every((row) => row.followup === null)).toBe(true)
  })
})
