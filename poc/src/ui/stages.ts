/** MAN-02 · 4단계 발주요청 프로세스 */
export const STAGES = [
  {
    id: 0,
    key: "1",
    title: "자동 체크",
    en: "Auto Check",
    goal: "6대 필수 항목의 누락·모호 표현·단위 오류를 실시간으로 전수 검사한다",
  },
  {
    id: 1,
    key: "2",
    title: "스마트 수정",
    en: "Smart Correction",
    goal: "KS·현장 시방 기반 권장값으로 일괄 또는 개별 교정한다",
  },
  {
    id: 2,
    key: "3",
    title: "사전 검수",
    en: "Pre-flight",
    goal: "6대 항목 적합 판정과 현장 공무담당자 확인 서명을 받는다",
  },
  {
    id: 3,
    key: "4",
    title: "발주요청",
    en: "Submit Order",
    goal: "전자 발주신청서(PO)를 미리보고 공급업체 견적 접수로 전송한다",
  },
] as const

export type StageId = (typeof STAGES)[number]["id"]
