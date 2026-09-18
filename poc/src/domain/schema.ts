import { z } from "zod"
import { FIELD_ORDER } from "./catalog.ts"

export const fieldIdSchema = z.enum(FIELD_ORDER)

export const evidenceSchema = z.object({
  fieldId: fieldIdSchema,
  sourceValue: z.string().nullable(),
  start: z.number().int().nullable(),
  end: z.number().int().nullable(),
  aliasCandidate: z.string().nullable(),
  aliasBasis: z.string().nullable(),
  memo: z.string().nullable(),
  candidateIds: z.array(z.string()),
  humanFilled: z.string().optional(),
})

export const extractionSchema = z.object({
  docId: z.string().nullable(),
  backend: z.enum(["rule", "paste", "llm", "golden"]),
  items: z.array(evidenceSchema),
  warnings: z.array(z.string()),
  humanFilled: z.string().optional(),
})

const nullishText = z.union([z.string(), z.number(), z.null()]).optional()

export const pastedItemSchema = z
  .object({
    항목ID: z.string().optional(),
    항목명: z.string().optional(),
    원문값: nullishText,
    원문시작: z.number().int().optional(),
    원문끝: z.number().int().optional(),
    원문발췌: z.string().optional(),
    표준명후보: z.string().nullable().optional(),
    표준명근거: z.string().nullable().optional(),
    메모: z.string().nullable().optional(),
    field: z.string().optional(),
    value: nullishText,
    start: z.number().int().optional(),
    end: z.number().int().optional(),
    quote: z.string().optional(),
    excerpt: z.string().optional(),
    candidate: z.string().optional(),
    note: z.string().optional(),
    사람확정: z.string().optional(),
    확정: z.string().optional(),
  })
  .passthrough()

export const pastedExtractionSchema = z.union([
  z.object({
    문서ID: z.string().optional(),
    항목: z.union([z.array(pastedItemSchema), z.record(z.string(), z.unknown())]),
    사람확정: z.string().optional(),
    확정: z.string().optional(),
  }),
  z.array(pastedItemSchema),
])
