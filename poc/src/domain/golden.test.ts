import { describe, expect, it } from "vitest"
import { goldenExtract } from "../extract/golden-extract.ts"
import { DEMO_TEXT, sampleById } from "../fixtures/samples.ts"
import { evaluateText } from "./pipeline.ts"

describe("golden fixtures", () => {
  it("returns a deterministic extraction for the demo id", () => {
    const golden = goldenExtract("D04-13", DEMO_TEXT)
    expect(golden?.backend).toBe("golden")
    expect(golden?.items.find((item) => item.fieldId === "need_date")?.sourceValue).toBe(
      "다음 주",
    )
  })

  it("returns null for an unknown id", () => {
    expect(goldenExtract("NOPE", DEMO_TEXT)).toBeNull()
  })

  it("keeps a complete request at zero needs-check on required fields", () => {
    const sample = sampleById("D04-01")
    expect(sample).toBeDefined()
    const { check } = evaluateText(sample!.text, sample!.id)
    expect(
      check.rows
        .filter((row) => ["item_id", "qty", "unit", "need_date", "delivery_location"].includes(row.fieldId))
        .every((row) => row.status === "충족"),
    ).toBe(true)
  })
})
