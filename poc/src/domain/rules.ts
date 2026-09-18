import {
  BASE_DATE,
  FIELD_NAMES,
  FIELD_ORDER,
  itemsById,
  normalizeUnit,
  type FieldId,
} from "./catalog.ts"
import { isVagueDateTerm, parseDate } from "./dates.ts"
import { LOC_RE } from "./extract-rule.ts"
import type { CheckResult, CheckRow, Evidence, Extraction, Status } from "./types.ts"

const ID_FORMAT = /^P-\d{2}$/
const UNREADABLE = "판독 불가"

function asId(value: string | null | undefined): string | null {
  if (value === null || value === undefined) return null
  const normalized = value.trim().toUpperCase().replaceAll("–", "-").replaceAll("—", "-")
  return ID_FORMAT.test(normalized) ? normalized : null
}

function getItem(extraction: Extraction, fieldId: FieldId): Evidence {
  return (
    extraction.items.find((item) => item.fieldId === fieldId) ?? {
      fieldId,
      sourceValue: null,
      start: null,
      end: null,
      aliasCandidate: null,
      aliasBasis: null,
      memo: null,
      candidateIds: [],
    }
  )
}

function unreadable(item: Evidence): boolean {
  return Boolean(item.memo && item.memo.includes(UNREADABLE))
}

function candidatesOf(item: Evidence) {
  const lexicon = itemsById()
  const id = asId(item.sourceValue)
  if (id && lexicon[id]) return [lexicon[id]]
  let ids = item.candidateIds
  if (ids.length === 0 && item.aliasCandidate) {
    ids = item.aliasCandidate.match(/P-\d{2}/g) ?? []
  }
  return ids.flatMap((cand) => (lexicon[cand] ? [lexicon[cand]] : []))
}

function aiLine(src: Evidence): string {
  const parts = [
    src.sourceValue !== null ? `원문 '${src.sourceValue}'` : "값 없음",
  ]
  if (src.aliasCandidate) parts.push(`후보 ${src.aliasCandidate}`)
  if (src.memo) parts.push(src.memo)
  return parts.join(" · ")
}

function pushRow(
  text: string,
  fieldId: FieldId,
  status: Status,
  basis: string,
  src: Evidence,
  cand: string | null = null,
): CheckRow {
  const start = src.start
  const end = src.end
  return {
    fieldId,
    fieldName: FIELD_NAMES[fieldId],
    status,
    needsCheck: status !== "충족",
    sourceValue: src.sourceValue,
    start,
    end,
    excerpt: start !== null && end !== null ? text.slice(start, end) : null,
    aliasCandidate: cand ?? src.aliasCandidate,
    basis,
    followup: null,
    role: { ai: aiLine(src), rule: basis, human: "" },
  }
}

export function checkExtraction(
  extraction: Extraction,
  text: string,
  baseDate: string = BASE_DATE,
): CheckResult {
  const lexicon = itemsById()
  const item = getItem(extraction, "item_id")
  const cands = candidatesOf(item)
  const vid = asId(item.sourceValue)
  const explicit = Boolean(vid && lexicon[vid])
  const rows: CheckRow[] = []

  const value = item.sourceValue
  if (value === null) {
    rows.push(pushRow(text, "item_id", "누락", "품목 ID·품명 모두 없음", item))
  } else if (unreadable(item)) {
    rows.push(pushRow(text, "item_id", "모호", "글자 판독 불가 — 원문 재확인", item))
  } else if (vid) {
    if (lexicon[vid]) {
      rows.push(
        pushRow(
          text,
          "item_id",
          "충족",
          `사전 품목 ${lexicon[vid].name} ${lexicon[vid].spec}`,
          item,
          `${lexicon[vid].name} ${lexicon[vid].spec}`,
        ),
      )
    } else {
      rows.push(pushRow(text, "item_id", "불일치", "사전에 없는 품목 ID", item))
    }
  } else {
    const ids = cands.map((c) => c.itemId).join(", ") || "없음"
    rows.push(
      pushRow(
        text,
        "item_id",
        "모호",
        `별칭만 있음 → 표준명 후보(${ids}), 사람 확정 필요`,
        item,
      ),
    )
  }

  const qty = getItem(extraction, "qty")
  const qtyVal = qty.sourceValue
  if (qtyVal === null) {
    rows.push(pushRow(text, "qty", "누락", "수량 없음", qty))
  } else if (unreadable(qty) || !/^[0-9,]+$/.test(qtyVal)) {
    rows.push(pushRow(text, "qty", "모호", "글자 판독 불가 — 원문 재확인", qty))
  } else if (Number(qtyVal.replaceAll(",", "")) <= 0) {
    rows.push(pushRow(text, "qty", "불일치", "수량이 0 이하", qty))
  } else {
    rows.push(pushRow(text, "qty", "충족", "양의 정수", qty))
  }

  const unit = getItem(extraction, "unit")
  const unitVal = unit.sourceValue
  if (unitVal === null) {
    rows.push(pushRow(text, "unit", "누락", "단위 없음", unit))
  } else {
    const std = normalizeUnit(unitVal)
    const units = new Set(cands.map((c) => c.unit))
    if (cands.length === 0) {
      rows.push(pushRow(text, "unit", "모호", "품목 미확정으로 표준 단위 비교 불가", unit))
    } else if (units.size > 1) {
      rows.push(pushRow(text, "unit", "모호", "후보 품목의 표준 단위가 서로 다름", unit))
    } else {
      const want = [...units][0]
      if (std === want) {
        rows.push(pushRow(text, "unit", "충족", "표준 단위와 일치", unit, want))
      } else {
        rows.push(pushRow(text, "unit", "불일치", `표준 단위 '${want}'와 다름`, unit, want))
      }
    }
  }

  const date = getItem(extraction, "need_date")
  const dateVal = date.sourceValue
  if (dateVal === null) {
    rows.push(pushRow(text, "need_date", "누락", "희망일 없음", date))
  } else if (unreadable(date)) {
    rows.push(pushRow(text, "need_date", "모호", "글자 판독 불가 — 원문 재확인", date))
  } else if (isVagueDateTerm(dateVal) && parseDate(dateVal) === null) {
    rows.push(
      pushRow(text, "need_date", "모호", `모호 표현 '${dateVal}' → 날짜로 단정하지 않음`, date),
    )
  } else {
    const parsed = parseDate(dateVal, baseDate)
    if (parsed === null) {
      rows.push(pushRow(text, "need_date", "모호", "날짜 형식으로 읽을 수 없음", date))
    } else if (parsed < baseDate) {
      rows.push(
        pushRow(text, "need_date", "불일치", `기준일 ${baseDate} 이전 날짜`, date, parsed),
      )
    } else {
      rows.push(pushRow(text, "need_date", "충족", "특정 날짜", date, parsed))
    }
  }

  const loc = getItem(extraction, "delivery_location")
  const locVal = loc.sourceValue
  if (locVal === null) {
    rows.push(pushRow(text, "delivery_location", "누락", "배송 위치 없음", loc))
  } else {
    const locRe = new RegExp(`^${LOC_RE.source}$`)
    const match = locVal.trim().match(locRe)
    if (match && match[2]?.trim()) {
      rows.push(pushRow(text, "delivery_location", "충족", "현장명 + 세부 위치", loc))
    } else if (match) {
      rows.push(
        pushRow(text, "delivery_location", "모호", "현장명만 있고 세부 위치 없음", loc),
      )
    } else {
      rows.push(pushRow(text, "delivery_location", "모호", "현장명 형식이 아님 — 확인", loc))
    }
  }

  const spec = getItem(extraction, "spec")
  const specVal = spec.sourceValue
  if (specVal !== null) {
    if (unreadable(spec)) {
      rows.push(pushRow(text, "spec", "모호", "글자 판독 불가 — 원문 재확인", spec))
    } else if (explicit && lexicon[vid as string].spec !== specVal) {
      rows.push(
        pushRow(
          text,
          "spec",
          "불일치",
          `품목 ID 사전 규격 '${lexicon[vid as string].spec}'과 다름`,
          spec,
          lexicon[vid as string].spec,
        ),
      )
    } else {
      rows.push(pushRow(text, "spec", "충족", "규격 원문 존재", spec))
    }
  } else if (explicit) {
    const catalogSpec = lexicon[vid as string].spec
    rows.push(
      pushRow(
        text,
        "spec",
        "충족",
        `품목 ID 확정 → 사전 규격 '${catalogSpec}' 적용(원문값 없음)`,
        spec,
        catalogSpec,
      ),
    )
  } else {
    rows.push(pushRow(text, "spec", "누락", "규격 없음(품목 ID 미확정)", spec))
  }

  const ordered = [...rows].sort(
    (a, b) => FIELD_ORDER.indexOf(a.fieldId) - FIELD_ORDER.indexOf(b.fieldId),
  )
  return {
    docId: extraction.docId,
    backend: extraction.backend,
    rows: ordered,
    needsCheckFields: ordered.filter((row) => row.needsCheck).map((row) => row.fieldId),
    followups: [],
  }
}
