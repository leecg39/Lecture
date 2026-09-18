import type { FieldId } from "./catalog.ts"

export type { FieldId }

export type Backend = "rule" | "paste" | "llm" | "golden"

export type Status = "충족" | "누락" | "모호" | "불일치"

export type Evidence = {
  fieldId: FieldId
  sourceValue: string | null
  start: number | null
  end: number | null
  aliasCandidate: string | null
  aliasBasis: string | null
  memo: string | null
  candidateIds: string[]
  humanFilled?: string
}

export type Extraction = {
  docId: string | null
  backend: Backend
  items: Evidence[]
  warnings: string[]
  humanFilled?: string
}

export type RoleLine = {
  ai: string
  rule: string
  human: string
}

export type CheckRow = {
  fieldId: FieldId
  fieldName: string
  status: Status
  needsCheck: boolean
  sourceValue: string | null
  start: number | null
  end: number | null
  excerpt: string | null
  aliasCandidate: string | null
  basis: string
  followup: string | null
  role: RoleLine
}

export type CheckResult = {
  docId: string | null
  backend: Backend
  rows: CheckRow[]
  needsCheckFields: FieldId[]
  followups: string[]
}

export type GateCode = "G1" | "G2" | "G3" | "G4" | "G5"

export type GateViolation = {
  code: GateCode
  fieldId: FieldId | null
  detail: string
  gate: string
}

export type HumanAction =
  | { kind: "confirm_check" }
  | { kind: "confirm_value"; value: string }
  | { kind: "reject" }
  | { kind: "clear" }

export type GateResult =
  | { ok: true; row: CheckRow }
  | { ok: false; reason: string }
