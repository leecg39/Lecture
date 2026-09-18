import { BASE_DATE, VAGUE_DATE_TERMS } from "./catalog.ts"

function safeDate(year: number, month: number, day: number): string | null {
  const dt = new Date(Date.UTC(year, month - 1, day))
  if (
    dt.getUTCFullYear() !== year ||
    dt.getUTCMonth() !== month - 1 ||
    dt.getUTCDate() !== day
  ) {
    return null
  }
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
}

export function parseDate(token: string, base: string = BASE_DATE): string | null {
  const year = Number(base.slice(0, 4))
  const iso = token.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (iso) return safeDate(Number(iso[1]), Number(iso[2]), Number(iso[3]))
  const kor = token.match(/^(\d{1,2})월\s?(\d{1,2})일$/)
  if (kor) return safeDate(year, Number(kor[1]), Number(kor[2]))
  const slash = token.match(/^(\d{1,2})[/.](\d{1,2})$/)
  if (slash) return safeDate(year, Number(slash[1]), Number(slash[2]))
  return null
}

export function isVagueDateTerm(token: string): boolean {
  return VAGUE_DATE_TERMS.some((term) => token.includes(term))
}

export function vagueTermsIn(text: string): string[] {
  return VAGUE_DATE_TERMS.filter((term) => text.includes(term))
}

export const DATE_LIKE = /\d{4}-\d{2}-\d{2}|\d{1,2}월\s?\d{1,2}일|\b\d{1,2}[/.]\d{1,2}\b/g
