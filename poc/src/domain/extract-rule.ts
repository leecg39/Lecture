import {
  FIELD_NAMES,
  FIELD_ORDER,
  aliasIndex,
  itemsById,
  type FieldId,
} from "./catalog.ts"
import type { Evidence, Extraction } from "./types.ts"

const DIGITISH = "0-9OolISB"
const W = "0-9A-Za-z_가-힣"
const UNIT_TOKENS = "(?:개소|개|EA|ea|Ea|pcs|본|미터|메타|롤|roll|ROLL|Roll|m|M)"
const DETAIL_TOKENS =
  "(?:\\d+동|지하\\d+층|\\d+층|옥상|정문|동측|서측|남측|북측|게이트|자재창고|야적장|하치장|기계실|입구)"

export const ID_RE = new RegExp(`P-[${DIGITISH}]{2}(?![${W}])`, "g")
export const SPEC_RE = new RegExp(
  `(?<![${W}-])(?:[${DIGITISH}]{2,3}A|[${DIGITISH}]{1,2}mm)(?![${W}])`,
  "g",
)
const ISO_RE = new RegExp(
  `(?<![${W}-])[${DIGITISH}]{4}-[${DIGITISH}]{2}-[${DIGITISH}]{2}(?![0-9A-Za-z-])`,
  "g",
)
const KOR_DATE_RE = /(?<!\d)\d{1,2}월\s?\d{1,2}일/g
const SLASH_DATE_RE = /(?<![\d/])\d{1,2}\/\d{1,2}(?![\d/])/g
const DOT_DATE_RE = /(?<![\d.])\d{1,2}\.\d{1,2}(?![\d.])/g
const QTY_UNIT_RE = new RegExp(
  `(?<![${W}-])([${DIGITISH},]+)\\s*(${UNIT_TOKENS})(?![${W}])`,
  "g",
)
const QTY_ONLY_RE = new RegExp(
  `(?<![${W}-])([${DIGITISH},]*[0-9][${DIGITISH},]*)(?![${W}/.\\-])`,
  "g",
)
const UNIT_ONLY_RE = new RegExp(`(?<![${W}])(${UNIT_TOKENS})(?![${W}])`, "g")
export const LOC_RE = new RegExp(`([A-Z]현장)((?:\\s?${DETAIL_TOKENS})*)`, "g")

const VAGUE_SORTED = [
  "가능한 빨리",
  "최대한 빨리",
  "이번 달 안",
  "월말까지",
  "다음 주",
  "이번 주",
  "내주 초",
  "이달 안",
  "급합니다",
  "다음주",
  "이번주",
  "조속히",
  "내주",
  "ASAP",
  "asap",
  "빨리",
  "급함",
]

type Span = readonly [number, number]

type Mask = {
  text: string
  used: readonly Span[]
}

function maskFree(mask: Mask, start: number, end: number): boolean {
  return mask.used.every(([a, b]) => end <= a || start >= b)
}

function maskTake(mask: Mask, start: number, end: number): Mask {
  return { text: mask.text, used: [...mask.used, [start, end]] }
}

function withGlobal(rx: RegExp): RegExp {
  const flags = rx.flags.includes("g") ? rx.flags : `${rx.flags}g`
  return new RegExp(rx.source, flags)
}

function maskSearch(
  mask: Mask,
  rx: RegExp,
): { match: RegExpExecArray; mask: Mask } | null {
  const r = withGlobal(rx)
  r.lastIndex = 0
  let match: RegExpExecArray | null = r.exec(mask.text)
  while (match) {
    const start = match.index
    const end = start + match[0].length
    if (maskFree(mask, start, end)) {
      return { match, mask: maskTake(mask, start, end) }
    }
    if (match[0].length === 0) r.lastIndex += 1
    match = r.exec(mask.text)
  }
  return null
}

export function emptyEvidence(
  fieldId: FieldId,
  extra: Partial<Evidence> = {},
): Evidence {
  return {
    fieldId,
    sourceValue: extra.sourceValue ?? null,
    start: extra.start ?? null,
    end: extra.end ?? null,
    aliasCandidate: extra.aliasCandidate ?? null,
    aliasBasis: extra.aliasBasis ?? null,
    memo: extra.memo ?? null,
    candidateIds: extra.candidateIds ?? [],
    ...(extra.humanFilled ? { humanFilled: extra.humanFilled } : {}),
  }
}

export function digitsOnly(token: string): boolean {
  return /^[0-9,]+$/.test(token)
}

function evidence(
  fieldId: FieldId,
  value: string | null = null,
  span: Span | null = null,
  extra: Partial<Evidence> = {},
): Evidence {
  return emptyEvidence(fieldId, {
    sourceValue: value,
    start: span ? span[0] : null,
    end: span ? span[1] : null,
    ...extra,
  })
}

export function extractRule(text: string, docId: string | null = null): Extraction {
  let mask: Mask = { text, used: [] }
  const items: Partial<Record<FieldId, Evidence>> = {}
  const lexicon = itemsById()
  const warnings: string[] = []

  const idHit = maskSearch(mask, ID_RE)
  const specHit = maskSearch(idHit ? idHit.mask : mask, SPEC_RE)
  mask = specHit?.mask ?? idHit?.mask ?? mask
  const specVal = specHit ? specHit.match[0] : null

  if (idHit) {
    mask = idHit.mask
    const tok = idHit.match[0]
    const span: Span = [idHit.match.index, idHit.match.index + tok.length]
    if (digitsOnly(tok.slice(2))) {
      const item = lexicon[tok]
      items.item_id = evidence( "item_id", tok, span, {
        aliasCandidate: item ? displayOf(item) : null,
        aliasBasis: item ? "품목 ID 사전 일치" : "사전에 없는 품목 ID",
        candidateIds: item ? [tok] : [],
      })
    } else {
      items.item_id = evidence("item_id", tok, span, {
        memo: `판독 불가 후보: '${tok}'`,
        candidateIds: [],
      })
    }
  } else {
    let found: { match: RegExpExecArray; mask: Mask; alias: string; cands: typeof lexicon[string][] } | null =
      null
    for (const [alias, cands] of aliasIndex()) {
      const hit = maskSearch(mask, new RegExp(escapeRegExp(alias), "gi"))
      if (hit) {
        found = { ...hit, alias, cands }
        break
      }
    }
    if (found) {
      mask = found.mask
      let cands = found.cands
      if (specVal && digitsOnly(specBody(specVal))) {
        const narrowed = cands.filter((c) => c.spec === specVal)
        if (narrowed.length > 0) cands = narrowed
      }
      const ids = cands.map((c) => c.itemId)
      const single = cands.length === 1
      items.item_id = evidence("item_id", found.match[0], [
        found.match.index,
        found.match.index + found.match[0].length,
      ], {
        aliasCandidate: single
          ? `${cands[0].itemId} ${displayOf(cands[0])}`
          : `${cands.map((c) => `${c.itemId} ${displayOf(c)}`).join(" / ")} (규격 확인)`,
        aliasBasis: single
          ? "사전 별칭 일치 + 규격 일치 (사람 확정 필요)"
          : "별칭 일치, 규격 미확인 → 병합 금지",
        candidateIds: ids,
      })
    } else {
      items.item_id = emptyEvidence("item_id")
    }
  }

  if (specHit) {
    const tok = specHit.match[0]
    const body = specBody(tok)
    items.spec = evidence("spec", tok, [
      specHit.match.index,
      specHit.match.index + tok.length,
    ], {
      memo: digitsOnly(body) ? null : `판독 불가 후보: '${tok}'`,
    })
  } else {
    items.spec = emptyEvidence("spec")
  }

  const dateRegexes = [ISO_RE, KOR_DATE_RE, SLASH_DATE_RE, DOT_DATE_RE]
  let dateHit: { match: RegExpExecArray; mask: Mask; iso: boolean } | null = null
  for (const rx of dateRegexes) {
    const hit = maskSearch(mask, rx)
    if (hit) {
      dateHit = { ...hit, iso: rx === ISO_RE }
      break
    }
  }
  if (dateHit) {
    mask = dateHit.mask
    const tok = dateHit.match[0]
    const memo =
      dateHit.iso && !digitsOnly(tok.replaceAll("-", ""))
        ? `판독 불가 후보: '${tok}'`
        : null
    items.need_date = evidence("need_date", tok, [
      dateHit.match.index,
      dateHit.match.index + tok.length,
    ], { memo })
  } else {
    let vagueHit: { match: RegExpExecArray; mask: Mask } | null = null
    for (const term of VAGUE_SORTED) {
      vagueHit = maskSearch(mask, new RegExp(escapeRegExp(term)))
      if (vagueHit) break
    }
    if (vagueHit) {
      mask = vagueHit.mask
      items.need_date = evidence("need_date", vagueHit.match[0], [
        vagueHit.match.index,
        vagueHit.match.index + vagueHit.match[0].length,
      ], { memo: "모호 표현 — 날짜로 변환하지 않음(사람 확인)" })
    } else {
      items.need_date = emptyEvidence("need_date")
    }
  }

  let best: { match: RegExpExecArray; hasDetail: boolean } | null = null
  const locRe = withGlobal(LOC_RE)
  locRe.lastIndex = 0
  let locMatch = locRe.exec(text)
  while (locMatch) {
    const hasDetail = Boolean(locMatch[2]?.trim())
    if (!best || (hasDetail && !best.hasDetail)) {
      best = { match: locMatch, hasDetail }
    }
    if (hasDetail) break
    locMatch = locRe.exec(text)
  }
  if (best) {
    const val = best.match[0].trimEnd()
    const start = best.match.index
    const end = start + val.length
    mask = maskTake(mask, start, end)
    items.delivery_location = evidence("delivery_location", val, [start, end], {
      memo: best.hasDetail ? null : "현장명만 있음 — 세부 위치 확인",
    })
  } else {
    items.delivery_location = emptyEvidence("delivery_location")
  }

  const qtyUnit = maskSearch(mask, QTY_UNIT_RE)
  if (qtyUnit) {
    mask = qtyUnit.mask
    const qty = qtyUnit.match[1]
    const unit = qtyUnit.match[2]
    const qtyStart = qtyUnit.match.index
    const qtyEnd = qtyStart + qty.length
    items.qty = evidence("qty", qty, [qtyStart, qtyEnd], {
      memo: digitsOnly(qty) ? null : `판독 불가 후보: '${qty}'`,
    })
    const unitStart = qtyUnit.match.index + qtyUnit.match[0].indexOf(unit)
    items.unit = evidence("unit", unit, [unitStart, unitStart + unit.length])
  } else {
    const qtyOnly = maskSearch(mask, QTY_ONLY_RE)
    if (qtyOnly) {
      mask = qtyOnly.mask
      const qty = qtyOnly.match[1]
      items.qty = evidence("qty", qty, [
        qtyOnly.match.index,
        qtyOnly.match.index + qty.length,
      ], {
        memo: digitsOnly(qty) ? null : `판독 불가 후보: '${qty}'`,
      })
    } else {
      items.qty = emptyEvidence("qty")
    }
    const unitOnly = maskSearch(mask, UNIT_ONLY_RE)
    if (unitOnly) {
      mask = unitOnly.mask
      items.unit = evidence("unit", unitOnly.match[1], [
        unitOnly.match.index,
        unitOnly.match.index + unitOnly.match[1].length,
      ], { memo: "수량 없이 단위만 있음" })
    } else {
      items.unit = emptyEvidence("unit", { memo: "단위 토큰 없음" })
    }
  }

  const extraIds = [...text.matchAll(withGlobal(ID_RE))]
    .filter((m) => maskFree(mask, m.index, m.index + m[0].length))
    .map((m) => m[0])
  const extraQty = [...text.matchAll(withGlobal(QTY_UNIT_RE))]
    .filter((m) => maskFree(mask, m.index, m.index + m[0].length))
    .map((m) => m[0])
  if (extraIds.length > 0 || extraQty.length > 0) {
    const note = `복수 품목 의심(추가 토큰: ${[...extraIds, ...extraQty].join(", ")}) — 이 PoC는 요청서당 1품목 기준, 사람 확인`
    const current = items.item_id ?? emptyEvidence("item_id")
    items.item_id = {
      ...current,
      memo: current.memo ? `${current.memo} · ${note}` : note,
    }
    warnings.push(note)
  }

  return {
    docId,
    backend: "rule",
    items: FIELD_ORDER.map((fieldId) => items[fieldId] ?? emptyEvidence(fieldId)),
    warnings,
  }
}

function displayOf(item: { name: string; spec: string }): string {
  return `${item.name} ${item.spec}`
}

function specBody(specVal: string): string {
  if (specVal.endsWith("A")) return specVal.slice(0, -1)
  if (specVal.endsWith("mm")) return specVal.slice(0, -2)
  return specVal
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

export function fieldName(fieldId: FieldId): string {
  return FIELD_NAMES[fieldId]
}
