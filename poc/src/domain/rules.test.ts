import { describe, expect, it } from "vitest"
import { DEMO_TEXT } from "../fixtures/samples.ts"
import { extractRule } from "./extract-rule.ts"
import { checkExtraction } from "./rules.ts"

function byField(text: string) {
  const extraction = extractRule(text, "t")
  const items = Object.fromEntries(extraction.items.map((item) => [item.fieldId, item]))
  const status = Object.fromEntries(
    checkExtraction(extraction, text).rows.map((row) => [row.fieldId, row.status]),
  )
  return { extraction, items, status }
}

describe("extract + check", () => {
  it("marks demo request date and site as needs-check, never as a calendar date", () => {
    const { items, status } = byField(DEMO_TEXT)
    expect(items.item_id.sourceValue).toBe("P-01")
    expect(items.qty.sourceValue).toBe("20")
    expect(items.unit.sourceValue).toBe("개")
    expect(items.need_date.sourceValue).toBe("다음 주")
    expect(items.need_date.memo).toContain("변환하지 않음")
    expect(items.delivery_location.sourceValue).toBe("A현장")
    expect(items.spec.sourceValue).toBeNull()
    for (const item of Object.values(items)) {
      if (item.sourceValue !== null && item.start !== null && item.end !== null) {
        expect(DEMO_TEXT.slice(item.start, item.end)).toBe(item.sourceValue)
      }
    }
    expect(status).toEqual({
      item_id: "충족",
      qty: "충족",
      unit: "충족",
      need_date: "모호",
      delivery_location: "모호",
      spec: "충족",
    })
    expect(status.need_date).not.toBe("충족")
  })

  it("does not merge an alias into one item without a spec", () => {
    const text = "볼밸브 12개 2026-09-29 B현장 1동 야적장"
    const { items, status } = byField(text)
    expect(items.item_id.sourceValue).toBe("볼밸브")
    expect(new Set(items.item_id.candidateIds)).toEqual(new Set(["P-01", "P-02"]))
    expect(items.item_id.aliasBasis).toContain("병합 금지")
    expect(status.item_id).toBe("모호")
    expect(status.spec).toBe("누락")
    expect(status.unit).toBe("충족")
  })

  it("flags unreadable OCR tokens instead of guessing", () => {
    const text = "품목:P-Ol 5OA\n수량:2O 개\n희망 납기:2O26-O9-25\n배송지:A현장 3동"
    const { items, status } = byField(text)
    expect(items.item_id.sourceValue).toBe("P-Ol")
    expect(items.item_id.memo).toContain("판독")
    expect(items.qty.sourceValue).toBe("2O")
    expect(items.spec.sourceValue).toBe("5OA")
    expect(items.need_date.sourceValue).toBe("2O26-O9-25")
    expect(status.item_id).toBe("모호")
    expect(status.qty).toBe("모호")
    expect(status.spec).toBe("모호")
    expect(status.need_date).toBe("모호")
    expect(status.unit).toBe("모호")
  })

  it("detects unit mismatch and synonym match", () => {
    const mismatch = "P-03 50A 40m 2026-09-27 A현장 3동 자재창고"
    expect(byField(mismatch).status.unit).toBe("불일치")
    const synonym = "P-07 50A 15 EA 2026-09-30 A현장 2동 기계실"
    expect(byField(synonym).status.unit).toBe("충족")
  })

  it("treats a past date as mismatch", () => {
    const text = "P-01 50A 20개 2026-09-10 A현장 3동 창고"
    expect(byField(text).status.need_date).toBe("불일치")
  })

  it("prefers a detailed location over a bare site name", () => {
    const text =
      "[구매 요청서] A현장 현장지원팀 / 요청자 김현장\n품목: P-01 50A\n수량: 20 개\n배송지: A현장 3동 지하1층 자재창고\n"
    expect(byField(text).items.delivery_location.sourceValue).toBe(
      "A현장 3동 지하1층 자재창고",
    )
  })

  it("flags a spec that disagrees with the catalog item", () => {
    const text = "P-01 100A 20개 2026-09-25 A현장 3동 창고"
    expect(byField(text).status.spec).toBe("불일치")
  })
})
