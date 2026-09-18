import { FIELD_NAMES, FIELD_ORDER, itemsById, type FieldId } from "./catalog.ts"
import type { CheckRow } from "./types.ts"

export type DraftValue = {
  value: string
  origin: "원문" | "권장" | "수동" | "비움"
  note: string
}

export type WorkingDraft = Record<FieldId, DraftValue>

export type FixSuggestion = {
  fieldId: FieldId
  fieldName: string
  current: string | null
  recommended: string
  reason: string
  autoApplicable: boolean
}

function emptyDraft(): WorkingDraft {
  return Object.fromEntries(
    FIELD_ORDER.map((id) => [
      id,
      { value: "", origin: "비움" as const, note: "" },
    ]),
  ) as WorkingDraft
}

/** 규칙 검사 결과로 작업 초안을 만든다. */
export function draftFromRows(rows: CheckRow[]): WorkingDraft {
  const draft = emptyDraft()
  for (const row of rows) {
    draft[row.fieldId] = {
      value: row.sourceValue ?? "",
      origin: row.sourceValue ? "원문" : "비움",
      note: row.needsCheck ? row.basis : "",
    }
  }
  return draft
}

function toMatCode(itemId: string): string {
  const n = itemId.match(/P-(\d+)/)?.[1]
  return n ? `MAT-${n.padStart(3, "0")}` : itemId
}

/** KS·용어사전 기반 권장 교정안. 희망일은 날짜를 지어내지 않는다. */
export function suggestFixes(rows: CheckRow[], draft: WorkingDraft): FixSuggestion[] {
  const lexicon = itemsById()
  const itemRow = rows.find((r) => r.fieldId === "item_id")
  const out: FixSuggestion[] = []

  let resolvedId: string | null = null
  const rawId = (draft.item_id.value || itemRow?.sourceValue || "").trim().toUpperCase()
  if (/^P-\d{2}$/.test(rawId) && lexicon[rawId]) {
    resolvedId = rawId
  } else if (itemRow?.aliasCandidate) {
    const ids = itemRow.aliasCandidate.match(/P-\d{2}/g) ?? []
    if (ids.length === 1) resolvedId = ids[0]
  }

  if (resolvedId && lexicon[resolvedId]) {
    const item = lexicon[resolvedId]
    const mat = toMatCode(resolvedId)
    if (draft.item_id.value !== mat) {
      out.push({
        fieldId: "item_id",
        fieldName: FIELD_NAMES.item_id,
        current: draft.item_id.value || null,
        recommended: mat,
        reason: `승인 품목 ${item.name} ${item.spec} → ${mat} (${resolvedId})`,
        autoApplicable: true,
      })
    }
    if (!draft.spec.value || draft.spec.value !== item.spec) {
      const row = rows.find((r) => r.fieldId === "spec")
      if (row?.needsCheck || !draft.spec.value) {
        out.push({
          fieldId: "spec",
          fieldName: FIELD_NAMES.spec,
          current: draft.spec.value || null,
          recommended: item.spec,
          reason: `사전 규격 · ${item.note}`,
          autoApplicable: true,
        })
      }
    }
    if (draft.unit.value && draft.unit.value !== item.unit) {
      out.push({
        fieldId: "unit",
        fieldName: FIELD_NAMES.unit,
        current: draft.unit.value,
        recommended: item.unit,
        reason: `공인 거래 단위는 '${item.unit}' (현재 '${draft.unit.value}')`,
        autoApplicable: true,
      })
    } else if (!draft.unit.value) {
      out.push({
        fieldId: "unit",
        fieldName: FIELD_NAMES.unit,
        current: null,
        recommended: item.unit,
        reason: `공인 거래 단위 '${item.unit}'`,
        autoApplicable: true,
      })
    }
  }

  const loc = draft.delivery_location.value
  if (loc && !/(게이트|하역|양중|창고|야적)/.test(loc)) {
    const site = loc.replace(/\s+/g, "")
    out.push({
      fieldId: "delivery_location",
      fieldName: FIELD_NAMES.delivery_location,
      current: loc,
      recommended: `${loc} · 반입 게이트 미정 · 하역/양중 구역 미정`,
      reason: "현장명만으로는 배차 거부. 게이트·하역 구역을 명시해야 한다.",
      autoApplicable: false,
    })
    void site
  } else if (!loc) {
    out.push({
      fieldId: "delivery_location",
      fieldName: FIELD_NAMES.delivery_location,
      current: null,
      recommended: "A현장 · 반입 게이트 ○○ · 하역/양중 ○○",
      reason: "배송 위치 누락. 게이트+하역 구역 형식으로 채운다.",
      autoApplicable: false,
    })
  }

  const dateRow = rows.find((r) => r.fieldId === "need_date")
  if (dateRow?.needsCheck || !draft.need_date.value) {
    out.push({
      fieldId: "need_date",
      fieldName: FIELD_NAMES.need_date,
      current: draft.need_date.value || dateRow?.sourceValue || null,
      recommended: "",
      reason:
        "모호한 희망일('다음 주' 등)은 날짜로 단정하지 않는다. 정확한 연-월-일을 직접 입력한다.",
      autoApplicable: false,
    })
  }

  return out
}

export function applyFix(draft: WorkingDraft, fix: FixSuggestion, manualValue?: string): WorkingDraft {
  const value = manualValue !== undefined ? manualValue : fix.recommended
  if (!value) return draft
  return {
    ...draft,
    [fix.fieldId]: {
      value,
      origin: manualValue !== undefined ? "수동" : "권장",
      note: fix.reason,
    },
  }
}

export function applyAllAuto(draft: WorkingDraft, fixes: FixSuggestion[]): WorkingDraft {
  let next = draft
  for (const fix of fixes) {
    if (fix.autoApplicable && fix.recommended) next = applyFix(next, fix)
  }
  return next
}

/** 6대 항목 적합도(0–100). 값이 채워지고 원문 모호 플래그가 없으면 만점. */
export function fitnessScore(rows: CheckRow[], draft: WorkingDraft): number {
  let pts = 0
  for (const id of FIELD_ORDER) {
    const row = rows.find((r) => r.fieldId === id)
    const v = draft[id].value.trim()
    if (!v) continue
    if (id === "need_date" && row?.status === "모호" && draft[id].origin === "원문") continue
    if (id === "delivery_location" && !/(게이트|하역|양중|창고|야적|동)/.test(v)) {
      pts += 8
      continue
    }
    pts += 100 / FIELD_ORDER.length
  }
  return Math.round(pts)
}

export function allFieldsFilled(draft: WorkingDraft): boolean {
  return FIELD_ORDER.every((id) => draft[id].value.trim().length > 0)
}

export function checklist(draft: WorkingDraft, rows: CheckRow[]): {
  fieldId: FieldId
  fieldName: string
  ok: boolean
  detail: string
}[] {
  return FIELD_ORDER.map((id) => {
    const v = draft[id].value.trim()
    const row = rows.find((r) => r.fieldId === id)
    if (!v) {
      return { fieldId: id, fieldName: FIELD_NAMES[id], ok: false, detail: "값 없음" }
    }
    if (id === "need_date" && row?.status === "모호" && draft[id].origin === "원문") {
      return {
        fieldId: id,
        fieldName: FIELD_NAMES[id],
        ok: false,
        detail: "모호 표현 그대로 — 정확한 날짜 필요",
      }
    }
    if (id === "delivery_location" && !/(게이트|하역|양중|창고|야적|동)/.test(v)) {
      return {
        fieldId: id,
        fieldName: FIELD_NAMES[id],
        ok: false,
        detail: "게이트·하역 구역 미기재",
      }
    }
    return {
      fieldId: id,
      fieldName: FIELD_NAMES[id],
      ok: true,
      detail: `${v} · ${draft[id].origin}`,
    }
  })
}

export function issuePoNumber(now = new Date()): string {
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, "0")
  const d = String(now.getDate()).padStart(2, "0")
  const r = String(Math.floor(Math.random() * 900) + 100)
  return `PO-${y}${m}${d}-${r}`
}
