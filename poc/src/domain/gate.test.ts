import { describe, expect, it } from "vitest"
import { BAD_DRAFT, DEMO_TEXT } from "../fixtures/samples.ts"
import { loadPasted } from "./extract-paste.ts"
import { auditExtraction } from "./gate.ts"
import { applyHumanAction } from "./human-gate.ts"
import { evaluateText } from "./pipeline.ts"

describe("gates", () => {
  it("rejects a draft that invents a date, location, spec, and human sign-off", () => {
    const extraction = loadPasted(BAD_DRAFT, DEMO_TEXT, "D04-13")
    const codes = auditExtraction(extraction, DEMO_TEXT).map((v) => v.code)
    expect(codes).toContain("G2")
    expect(codes).toContain("G1")
    expect(codes).toContain("G4")
    expect(codes).toContain("G5")
  })

  it("does not let a person confirm a spec that is not in the source", () => {
    const { check } = evaluateText(DEMO_TEXT, "D04-13")
    const spec = check.rows.find((row) => row.fieldId === "spec")
    expect(spec).toBeDefined()
    const result = applyHumanAction(
      spec!,
      { kind: "confirm_value", value: "50A" },
      DEMO_TEXT,
    )
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.reason).toContain("원문에 없는 값")
  })

  it("lets a person confirm that a relative date still needs a check", () => {
    const { check } = evaluateText(DEMO_TEXT, "D04-13")
    const date = check.rows.find((row) => row.fieldId === "need_date")
    expect(date?.needsCheck).toBe(true)
    const result = applyHumanAction(date!, { kind: "confirm_check" }, DEMO_TEXT)
    expect(result.ok).toBe(true)
    if (result.ok) expect(result.row.role.human).toBe("확인 필요로 확정")
  })
})
