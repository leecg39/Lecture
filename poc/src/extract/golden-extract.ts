import { extractRule } from "../domain/extract-rule.ts"
import { sampleById } from "../fixtures/samples.ts"
import type { Extraction } from "../domain/types.ts"

export function goldenExtract(docId: string, text: string): Extraction | null {
  const sample = sampleById(docId)
  if (!sample) return null
  return { ...extractRule(text, docId), backend: "golden" }
}
