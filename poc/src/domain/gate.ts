import { itemsById } from "./catalog.ts"
import { DATE_LIKE, parseDate, vagueTermsIn } from "./dates.ts"
import { SPEC_RE } from "./extract-rule.ts"
import type { Extraction, FieldId, GateCode, GateViolation } from "./types.ts"

export const GATE_TEXT: Record<GateCode, string> = {
  G1: "값이 없으면 비우거나 '확인 필요'. 원문 없는 값을 채우지 않는다.",
  G2: "'다음 주' 같은 모호 표현을 날짜로 단정하지 않는다.",
  G3: "별칭이 비슷하다는 이유만으로 다른 규격을 합치지 않는다.",
  G4: "원문에 없는 규격을 채우지 않는다.",
  G5: "최종 확정은 사람이 한다. AI 출력은 '제안' 열에만 둔다.",
}

const ID_TOKEN = /P-\d{2}/g
const SPEC_TOKEN = /\b\d{2,3}A\b|\b\d{1,2}mm\b/g

function violation(
  code: GateCode,
  fieldId: FieldId | null,
  detail: string,
): GateViolation {
  return { code, fieldId, detail, gate: GATE_TEXT[code] }
}

function inText(text: string, value: string | null | undefined): boolean {
  return value !== null && value !== undefined && text.includes(String(value))
}

export function auditExtraction(extraction: Extraction, text: string): GateViolation[] {
  const viol: GateViolation[] = []
  const vagueInText = vagueTermsIn(text)
  const specInText = new RegExp(SPEC_RE.source).test(text)
  const lexicon = itemsById()

  for (const item of extraction.items) {
    const fieldId = item.fieldId
    const value = item.sourceValue
    const start = item.start
    const end = item.end

    if (fieldId === "spec" && value !== null && !inText(text, value)) {
      viol.push(violation("G4", fieldId, `규격 '${value}'이 원문에 없음`))
      continue
    }

    if (fieldId === "need_date") {
      const texts = [value, item.aliasCandidate, item.memo].filter(Boolean).map(String)
      let fabricated: string | null = null
      for (const tx of texts) {
        const matches = tx.match(new RegExp(DATE_LIKE.source, "g")) ?? []
        for (const token of matches) {
          if (!inText(text, token) && parseDate(token) !== null) {
            fabricated = token
            break
          }
        }
        if (fabricated) break
      }
      if (fabricated) {
        const why = vagueInText[0] ?? "원문"
        viol.push(
          violation("G2", fieldId, `'${why}'을(를) 날짜 '${fabricated}'로 단정 (원문에 없음)`),
        )
        continue
      }
    }

    if (value !== null) {
      if (start === null || end === null) {
        viol.push(violation("G1", fieldId, `'${value}'에 원문 위치가 없음`))
      } else if (text.slice(start, end) !== String(value)) {
        viol.push(
          violation(
            "G1",
            fieldId,
            `원문 위치 [${start}:${end}]='${text.slice(start, end)}' ≠ 값 '${value}'`,
          ),
        )
      }
    }

    if (fieldId === "item_id" && value !== null && !/^P-\d{2}$/.test(value.toUpperCase())) {
      const aliasCands = Object.values(lexicon).filter(
        (entry) => entry.aliases.includes(value) || entry.name === value,
      )
      const candTxt = item.aliasCandidate ?? ""
      const single = new Set(candTxt.match(ID_TOKEN) ?? [])
      const candSpecs = [...(candTxt.match(SPEC_TOKEN) ?? [])].filter((s) => !text.includes(s))
      if (aliasCands.length > 1 && !specInText) {
        if (single.size === 1) {
          const only = [...single][0]
          viol.push(
            violation(
              "G3",
              fieldId,
              `별칭 '${value}'은 ${aliasCands.length}개 품목에 해당하나 규격 없이 ${only}로 확정`,
            ),
          )
        } else if (candSpecs.length === 1 && new Set(aliasCands.map((c) => c.spec)).size > 1) {
          viol.push(
            violation(
              "G3",
              fieldId,
              `별칭 '${value}'의 후보에 원문에 없는 규격 '${candSpecs[0]}'을 붙여 한 품목으로 좁힘`,
            ),
          )
        }
      }
    }

    if (item.humanFilled) {
      viol.push(violation("G5", fieldId, `사람 확정 칸에 AI 값 '${item.humanFilled}'`))
    }
  }

  if (extraction.humanFilled) {
    viol.push(violation("G5", null, "문서 수준 사람 확정 칸이 채워져 있음"))
  }

  return viol
}
