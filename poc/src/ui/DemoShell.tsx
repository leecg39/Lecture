import { STAGES, type StageId } from "./stages.ts"

type Props = {
  stage: StageId
  onStage: (stage: StageId) => void
  score: number
  badge?: string
  onRecheck?: () => void
  onVagueSample?: () => void
}

export function DemoShell({
  stage,
  onStage,
  score,
  badge,
  onRecheck,
  onVagueSample,
}: Props) {
  const current = STAGES[stage]
  return (
    <>
      <div className="global-nav">
        <div className="brand">
          <strong>CPMS</strong>
          <span>MAN-02</span>
        </div>
        {badge ? <p className="crumb">{badge}</p> : <span />}
      </div>

      <header className="hero">
        <p className="eyebrow">현장 관리자 · 발주 관리</p>
        <h1>발주신청서 정밀 체크</h1>
        <p className="lede">6대 항목을 자동으로 검사하고, 교정한 뒤 발주합니다.</p>
        <span className="signal">auto → smart → preflight → submit</span>
        <div className="hero-actions">
          {onRecheck ? (
            <button type="button" className="btn-filled" onClick={onRecheck}>
              자동 체크 실행
            </button>
          ) : null}
          {onVagueSample ? (
            <button type="button" className="btn-outlined" onClick={onVagueSample}>
              테스트 샘플 불러오기
            </button>
          ) : null}
        </div>
      </header>

      <div className="mini-nav">
        <p className="product-name">
          발주신청서<em>MAN-02</em>
        </p>
        <nav className="stage-nav" aria-label="4단계 발주요청">
          {STAGES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={item.id === stage ? "stage-tab is-active" : "stage-tab"}
              onClick={() => onStage(item.id)}
            >
              <span className="stage-key">{item.key}</span>
              <strong>{item.title}</strong>
            </button>
          ))}
        </nav>
      </div>

      <div className="shell-goal">
        <p>
          <strong>이 단계</strong> · {current.goal}
        </p>
        <p className="score-chip" aria-label="적합도 점수">
          적합도 <b>{score}</b>
          <span>/100</span>
        </p>
      </div>
    </>
  )
}
