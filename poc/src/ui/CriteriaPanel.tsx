import type { CheckResult, GateViolation } from "../domain/types.ts"

type Props = {
  check: CheckResult
  violations: GateViolation[]
}

export function CriteriaPanel({ check, violations }: Props) {
  const traced = check.rows.filter(
    (row) =>
      row.sourceValue === null ||
      (row.start !== null && row.end !== null && row.excerpt === row.sourceValue),
  ).length
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>성공 기준 미리보기</h2>
        <p>아래 숫자는 교육용 가정이다. 실측이 아니다.</p>
      </div>
      <ul className="metrics">
        <li>
          <strong>누락 탐지율 95%</strong>
          <span>교육용 목표. 이 표본에서 확인 필요 {check.needsCheckFields.length}건.</span>
        </li>
        <li>
          <strong>잘못된 누락 경고 10% 이하</strong>
          <span>교육용 목표. 게이트 위반 {violations.length}건.</span>
        </li>
        <li>
          <strong>중요 오류 0건</strong>
          <span>시험 표본 기준. 운영 무오류가 아니다.</span>
        </li>
        <li>
          <strong>원문 추적 100%</strong>
          <span>
            이 화면 {traced}/{check.rows.length}행이 원문 위치와 값이 같거나 비어 있다.
          </span>
        </li>
      </ul>
      <p className="muted">
        계속: 품질을 지키며 시간이 줄고 검토 담당이 있다. 수정: 중요 오류가 나면 범위를 줄여 다시
        시험. 중단: 검토 비용으로 총시간이 늘거나 정답 검토자를 확보하지 못한다.
      </p>
    </section>
  )
}
