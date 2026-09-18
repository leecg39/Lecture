export type Sample = {
  id: string
  label: string
  kind: "demo" | "complete" | "unit" | "alias" | "scan" | "wrong" | "vague"
  text: string
  note: string
}

export const DEMO_TEXT = "A현장, 품목 P-01 20개, 다음 주 필요."

/** MAN-02 · 모호한 표현 / 틀린 단위 테스트용 샘플 */
export const VAGUE_UNIT_SAMPLE =
  "현장 알아서 좋은 거 볼밸브 좀 보내주세요. 수량 20kg. 빨리 필요. 배송은 서울."

export type KsPreset = {
  id: string
  label: string
  text: string
}

/** MAN-02 · KS 표준 자재 프리셋 (교육용 가상, 배관·설비 대용) */
export const KS_PRESETS: readonly KsPreset[] = [
  {
    id: "ks-valve",
    label: "볼밸브 50A",
    text: "[발주신청서] A현장 / 요청자 김현장\n품목: P-01 50A\n수량: 20 개\n희망 납기: 2026-09-25\n배송지: A현장 3동 반입 게이트 B · 지하1층 자재창고 하역\n",
  },
  {
    id: "ks-pvc",
    label: "PVC 파이프",
    text: "[발주신청서] A현장 / 요청자 김현장\n품목: P-03 50A\n수량: 40 본\n희망 납기: 2026-09-27\n배송지: A현장 1동 반입 게이트 A · 야적장 하역\n",
  },
  {
    id: "ks-pipe",
    label: "강관 100A",
    text: "[발주신청서] B현장 / 요청자 이공무\n품목: P-06 100A\n수량: 15 본\n희망 납기: 2026-09-30\n배송지: B현장 2동 반입 게이트 C · 1층 양중 구역\n",
  },
  {
    id: "ks-elbow",
    label: "PVC 엘보 90도",
    text: "[발주신청서] A현장 / 요청자 김현장\n품목: P-07 50A\n수량: 30 개\n희망 납기: 2026-09-26\n배송지: A현장 3동 반입 게이트 B · 지하1층 자재창고\n",
  },
]

export const SAMPLES: readonly Sample[] = [
  {
    id: "D04-13",
    label: "시연 · 다음 주 / 현장명만",
    kind: "demo",
    text: DEMO_TEXT,
    note: "희망일·배송 위치가 확인 대상.",
  },
  {
    id: "MAN-02-vague",
    label: "MAN-02 · 모호/틀린 단위",
    kind: "vague",
    text: VAGUE_UNIT_SAMPLE,
    note: "모호 표현·단위 오류·위치 부실 — 자동 체크 시험용.",
  },
  {
    id: "D04-01",
    label: "정상 · 필수 항목 충족",
    kind: "complete",
    text: "[구매 요청서] A현장 현장지원팀 / 요청자 김현장\n품목: P-01 50A\n수량: 20 개\n희망 납기: 2026-09-25\n배송지: A현장 3동 지하1층 자재창고\n비고: 현장 소장 확인 완료\n",
    note: "누락 0.",
  },
  {
    id: "D04-19",
    label: "단위 불일치 · 본 vs m",
    kind: "unit",
    text: "[구매 요청서] A현장 현장지원팀 / 요청자 김현장\n품목: P-03 50A\n수량: 40 m\n희망 납기: 2026-09-27\n배송지: A현장 3동 지하1층 자재창고\n",
    note: "표준 단위 '본'인데 'm'.",
  },
  {
    id: "D04-08",
    label: "별칭만 · 병합 금지",
    kind: "alias",
    text: "제목: 자재 구매 요청\n\n구매팀 담당자님, 박지원입니다.\n아래 자재 구매를 요청합니다.\n- 품명/규격: 볼밸브\n- 수량: 12개\n- 희망 납기: 2026-09-29\n- 납품 장소: B현장 1동 1층 야적장\n기존 것과 같은 걸로\n",
    note: "볼밸브는 P-01/P-02 후보.",
  },
  {
    id: "D04-03S",
    label: "저품질 스캔 · 판독 불가",
    kind: "scan",
    text: "품목:P-Ol 5OA\n수량:2O 개\n희망 납기:2O26-O9-25\n배송지:A현장 3동",
    note: "O/l 혼동을 추측해 채우지 않는다.",
  },
]

export const BAD_DRAFT = {
  문서ID: "D04-13",
  항목: [
    { 항목ID: "품목 ID", 원문값: "P-01", 원문발췌: "P-01", 표준명후보: "볼밸브 50A" },
    { 항목ID: "수량", 원문값: "20", 원문발췌: "20" },
    { 항목ID: "단위", 원문값: "개", 원문발췌: "개" },
    {
      항목ID: "희망일",
      원문값: "2026-09-24",
      원문발췌: "다음 주",
      메모: "다음 주 → 수요일 기준 9/24로 정리",
    },
    {
      항목ID: "배송 위치",
      원문값: "A현장 3동 자재창고",
      원문발췌: "A현장",
      메모: "통상 자재창고로 배송",
    },
    { 항목ID: "규격", 원문값: "50A", 원문발췌: "", 메모: "P-01은 50A이므로 기재" },
  ],
  사람확정: "이상 없음, 발주 진행 가능",
}

export function sampleById(id: string): Sample | undefined {
  return SAMPLES.find((sample) => sample.id === id)
}
