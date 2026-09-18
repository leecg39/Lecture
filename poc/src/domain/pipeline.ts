import { auditExtraction } from "./gate.ts"
import { draftFollowups } from "./followup.ts"
import { extractRule } from "./extract-rule.ts"
import { loadPasted } from "./extract-paste.ts"
import { checkExtraction } from "./rules.ts"
import type { CheckResult, Extraction, GateViolation } from "./types.ts"

export type Evaluation = {
  extraction: Extraction
  check: CheckResult
  violations: GateViolation[]
}

export function evaluateText(text: string, docId: string | null = null): Evaluation {
  const extraction = extractRule(text, docId)
  return finish(extraction, text)
}

export function evaluatePasted(
  raw: unknown,
  text: string,
  docId: string | null = null,
): Evaluation {
  const extraction = loadPasted(raw, text, docId)
  return finish(extraction, text)
}

function finish(extraction: Extraction, text: string): Evaluation {
  const check = draftFollowups(checkExtraction(extraction, text))
  const violations = auditExtraction(extraction, text)
  return { extraction, check, violations }
}
