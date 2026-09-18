import { FIELD_NAMES, FIELD_ORDER, type FieldId } from "./catalog.ts"
import { emptyEvidence } from "./extract-rule.ts"
import { pastedExtractionSchema } from "./schema.ts"
import type { Evidence, Extraction } from "./types.ts"

const KEY_ALIASES: Record<string, string> = {
  field: "항목ID",
  value: "원문값",
  start: "원문시작",
  end: "원문끝",
  quote: "원문발췌",
  excerpt: "원문발췌",
  candidate: "표준명후보",
  basis: "표준명근거",
  note: "메모",
}

const NAME_TO_ID: Record<string, FieldId> = {
  ...Object.fromEntries(
    FIELD_ORDER.map((id) => [FIELD_NAMES[id].replaceAll(" ", ""), id]),
  ),
  품목ID: "item_id",
  품목: "item_id",
  수량: "qty",
  단위: "unit",
  희망일: "need_date",
  희망납기: "need_date",
  납기: "need_date",
  배송위치: "delivery_location",
  배송지: "delivery_location",
  규격: "spec",
  item_id: "item_id",
  qty: "qty",
  unit: "unit",
  need_date: "need_date",
  delivery_location: "delivery_location",
  spec: "spec",
}

const NULLS = new Set(["", "null", "None", "없음", "N/A", "n/a", "-", "—"])
const QTY_UNIT_SPLIT = /^([0-9][0-9,]*)\s*(개소|개|EA|ea|Ea|pcs|본|미터|메타|롤|roll|ROLL|Roll|m|M)$/

export function stripCodeFence(raw: string): string {
  const trimmed = raw.trim()
  const fenced = trimmed.match(/```(?:json|JSON)?\s*([\s\S]*?)```/)
  if (fenced) return fenced[1].trim()
  const starts = [trimmed.indexOf("{"), trimmed.indexOf("[")].filter((i) => i >= 0)
  const ends = [trimmed.lastIndexOf("}"), trimmed.lastIndexOf("]")].filter((i) => i >= 0)
  if (starts.length > 0 && ends.length > 0 && Math.min(...starts) < Math.max(...ends)) {
    return trimmed.slice(Math.min(...starts), Math.max(...ends) + 1)
  }
  return trimmed
}

function sameClass(a: string, b: string): boolean {
  if (/\d/.test(a) && /\d/.test(b)) return true
  if (/[A-Za-z]/.test(a) && /[A-Za-z]/.test(b)) return true
  return /[가-힣]/.test(a) && /[가-힣]/.test(b)
}

export function findStandalone(text: string, value: string): number {
  if (!value) return -1
  let first = -1
  let start = 0
  while (start <= text.length) {
    const idx = text.indexOf(value, start)
    if (idx < 0) return first
    if (first < 0) first = idx
    const before = idx > 0 ? text[idx - 1] : " "
    const after = idx + value.length < text.length ? text[idx + value.length] : " "
    const gluedBefore =
      sameClass(before, value[0]) || (before === "-" && /\d/.test(value[0]))
    const gluedAfter =
      sameClass(after, value[value.length - 1]) ||
      (after === "-" && /\d/.test(value[value.length - 1]))
    if (!gluedBefore && !gluedAfter) return idx
    start = idx + 1
  }
  return first
}

function normalizeKey(key: string): string {
  return KEY_ALIASES[key.replaceAll(" ", "")] ?? key
}

function asText(value: unknown): string | null {
  if (value === null || value === undefined) return null
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : String(value)
  }
  const text = String(value).trim()
  if (NULLS.has(text)) return null
  return String(value)
}

function resolveFieldId(raw: unknown): FieldId | null {
  if (raw === undefined || raw === null) return null
  const key = String(raw).replaceAll(" ", "")
  return NAME_TO_ID[key] ?? null
}

export function loadPasted(
  raw: unknown,
  text: string,
  docId: string | null = null,
): Extraction {
  const parsed = typeof raw === "string" ? JSON.parse(stripCodeFence(raw)) : raw
  const envelope = pastedExtractionSchema.parse(parsed)
  const warnings: string[] = []
  let rawItems: unknown[] = []
  let extraHuman: string | undefined

  if (Array.isArray(envelope)) {
    rawItems = envelope
  } else {
    extraHuman = envelope.사람확정 || envelope.확정
    if (Array.isArray(envelope.항목)) {
      rawItems = envelope.항목
    } else {
      rawItems = Object.entries(envelope.항목)
        .filter(([k]) => !["문서ID", "사람확정", "확정"].includes(k))
        .map(([k, v]) =>
          v && typeof v === "object"
            ? { 항목ID: k, ...(v as Record<string, unknown>) }
            : { 항목ID: k, 원문값: v },
        )
    }
  }

  const byField: Partial<Record<FieldId, Evidence>> = {}
  for (const row of rawItems) {
    if (!row || typeof row !== "object") continue
    const mapped = Object.fromEntries(
      Object.entries(row as Record<string, unknown>).map(([k, v]) => [normalizeKey(k), v]),
    )
    const fieldId = resolveFieldId(mapped.항목ID)
    if (!fieldId) continue
    if (byField[fieldId]) {
      warnings.push(`${FIELD_NAMES[fieldId]} 항목이 중복 출력됨 — 뒤의 값 사용`)
    }
    const value = asText(mapped.원문값)
    let start = typeof mapped.원문시작 === "number" ? mapped.원문시작 : null
    let end = typeof mapped.원문끝 === "number" ? mapped.원문끝 : null
    if (value !== null && (start === null || end === null || text.slice(start, end) !== value)) {
      const probe = typeof mapped.원문발췌 === "string" ? mapped.원문발췌 : value
      const idx = findStandalone(text, String(probe))
      if (idx >= 0 && text.slice(idx, idx + String(probe).length) === value) {
        start = idx
        end = idx + String(probe).length
      } else {
        const valueIdx = findStandalone(text, value)
        if (valueIdx >= 0) {
          start = valueIdx
          end = valueIdx + value.length
        } else {
          start = null
          end = null
        }
      }
    }
    const human =
      asText(mapped.사람확정) ?? asText(mapped.확정) ?? asText(mapped.최종) ?? undefined
    byField[fieldId] = emptyEvidence(fieldId, {
      sourceValue: value,
      start,
      end,
      aliasCandidate: asText(mapped.표준명후보),
      aliasBasis: asText(mapped.표준명근거),
      memo: asText(mapped.메모),
      ...(human ? { humanFilled: human } : {}),
    })
  }

  const qty = byField.qty
  if (qty?.sourceValue && qty.start !== null) {
    const split = qty.sourceValue.match(QTY_UNIT_SPLIT)
    if (split && !byField.unit?.sourceValue) {
      const base = qty.start
      byField.qty = emptyEvidence("qty", {
        sourceValue: split[1],
        start: base,
        end: base + split[1].length,
        memo: qty.memo,
      })
      const unitStart = base + split[0].indexOf(split[2])
      byField.unit = emptyEvidence("unit", {
        sourceValue: split[2],
        start: unitStart,
        end: unitStart + split[2].length,
        memo: "수량 칸에서 분리",
      })
      warnings.push(`수량 '${split[0]}'을 수량 '${split[1]}'과 단위 '${split[2]}'로 분리`)
    }
  }

  const items = FIELD_ORDER.map((id) => byField[id] ?? emptyEvidence(id))
  if (items.every((item) => item.sourceValue === null)) {
    warnings.push("추출된 값이 하나도 없음 — 출력 형식 또는 원문 입력을 확인")
  }

  const docFromObj =
    envelope && !Array.isArray(envelope) && "문서ID" in envelope
      ? envelope.문서ID ?? null
      : null

  return {
    docId: docId ?? docFromObj ?? null,
    backend: "paste",
    items,
    warnings,
    ...(extraHuman ? { humanFilled: extraHuman } : {}),
  }
}
