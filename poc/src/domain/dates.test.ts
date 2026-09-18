import { describe, expect, it } from "vitest"
import { isVagueDateTerm, parseDate } from "./dates.ts"

describe("parseDate", () => {
  it("reads ISO, Korean, and slash forms", () => {
    expect(parseDate("2026-09-25")).toBe("2026-09-25")
    expect(parseDate("9월 26일")).toBe("2026-09-26")
    expect(parseDate("9/28")).toBe("2026-09-28")
  })

  it("does not turn relative phrases into dates", () => {
    expect(parseDate("다음 주")).toBeNull()
    expect(parseDate("ASAP")).toBeNull()
    expect(isVagueDateTerm("다음 주")).toBe(true)
  })
})
