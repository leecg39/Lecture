export const BASE_DATE = "2026-09-17"

export const FIELD_ORDER = [
  "item_id",
  "qty",
  "unit",
  "need_date",
  "delivery_location",
  "spec",
] as const

export type FieldId = (typeof FIELD_ORDER)[number]

export const FIELD_NAMES: Record<FieldId, string> = {
  item_id: "품목 ID",
  qty: "수량",
  unit: "단위",
  need_date: "희망일",
  delivery_location: "배송 위치",
  spec: "규격",
}

export const CRITICAL_FIELDS: ReadonlySet<FieldId> = new Set([
  "item_id",
  "qty",
  "unit",
  "need_date",
])

export type CatalogItem = {
  itemId: string
  name: string
  spec: string
  unit: string
  aliases: readonly string[]
  note: string
}

export function displayItem(item: CatalogItem): string {
  return `${item.name} ${item.spec}`
}

export const LEXICON: readonly CatalogItem[] = [
  {
    itemId: "P-01",
    name: "볼밸브",
    spec: "50A",
    unit: "개",
    aliases: ["볼밸브", "볼발브", "밸브", "ball valve"],
    note: "P-02(100A)와 별칭이 같음 → 규격 없으면 병합 금지",
  },
  {
    itemId: "P-02",
    name: "볼밸브",
    spec: "100A",
    unit: "개",
    aliases: ["볼밸브", "볼발브", "밸브", "ball valve"],
    note: "P-01(50A)와 별칭이 같음 → 규격 없으면 병합 금지",
  },
  {
    itemId: "P-03",
    name: "PVC 파이프",
    spec: "50A",
    unit: "본",
    aliases: ["PVC 파이프", "PVC관", "PVC파이프", "피브이씨 파이프", "pvc pipe"],
    note: "P-04(100A)와 별칭이 같음 → 규격 없으면 병합 금지",
  },
  {
    itemId: "P-04",
    name: "PVC 파이프",
    spec: "100A",
    unit: "본",
    aliases: ["PVC 파이프", "PVC관", "PVC파이프", "피브이씨 파이프", "pvc pipe"],
    note: "P-03(50A)와 별칭이 같음",
  },
  {
    itemId: "P-05",
    name: "강관",
    spec: "50A",
    unit: "본",
    aliases: ["강관", "백관", "스틸파이프", "steel pipe"],
    note: "P-06(100A)와 별칭이 같음",
  },
  {
    itemId: "P-06",
    name: "강관",
    spec: "100A",
    unit: "본",
    aliases: ["강관", "백관", "스틸파이프", "steel pipe"],
    note: "P-05(50A)와 별칭이 같음",
  },
  {
    itemId: "P-07",
    name: "PVC 엘보 90도",
    spec: "50A",
    unit: "개",
    aliases: ["엘보", "엘보우", "90도 엘보", "elbow"],
    note: "P-08(45도)과 '엘보' 별칭 공유 → 각도 확인",
  },
  {
    itemId: "P-08",
    name: "PVC 엘보 45도",
    spec: "50A",
    unit: "개",
    aliases: ["엘보", "엘보우", "45도 엘보", "45엘보"],
    note: "P-07(90도)과 '엘보' 별칭 공유 → 각도 확인",
  },
  {
    itemId: "P-09",
    name: "배관 보온재",
    spec: "50A",
    unit: "m",
    aliases: ["보온재", "단열재", "인슐레이션"],
    note: "길이 단위(m). 개수로 요청 오면 불일치",
  },
  {
    itemId: "P-10",
    name: "테프론 테이프",
    spec: "12mm",
    unit: "롤",
    aliases: ["테프론", "테플론 테이프", "씰테이프", "테프론 테이프"],
    note: "롤 단위. 개수로 요청 오면 불일치",
  },
]

export const UNIT_SYNONYMS: Record<string, ReadonlySet<string>> = {
  개: new Set(["개", "EA", "ea", "Ea", "개소", "pcs"]),
  본: new Set(["본"]),
  m: new Set(["m", "M", "미터", "메타", "meter"]),
  롤: new Set(["롤", "roll", "ROLL", "Roll"]),
}

export const VAGUE_DATE_TERMS = [
  "다음 주",
  "다음주",
  "내주 초",
  "내주",
  "이번 주",
  "이번주",
  "이번 달 안",
  "이달 안",
  "월말까지",
  "ASAP",
  "asap",
  "빨리",
  "급함",
  "급합니다",
  "조속히",
  "가능한 빨리",
  "최대한 빨리",
] as const

export function normalizeUnit(token: string | null): string | null {
  if (token === null) return null
  for (const [std, syns] of Object.entries(UNIT_SYNONYMS)) {
    if (syns.has(token)) return std
  }
  return null
}

export function itemsById(): Record<string, CatalogItem> {
  return Object.fromEntries(LEXICON.map((item) => [item.itemId, item]))
}

export function aliasIndex(): Array<[string, CatalogItem[]]> {
  const idx = new Map<string, CatalogItem[]>()
  for (const item of LEXICON) {
    const aliases = [...new Set([...item.aliases, item.name])]
    for (const alias of aliases) {
      const list = idx.get(alias) ?? []
      if (!list.includes(item)) {
        idx.set(alias, [...list, item])
      }
    }
  }
  return [...idx.entries()].sort((a, b) => b[0].length - a[0].length)
}
