type Props = {
  questions: string[]
}

export function FollowUpList({ questions }: Props) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>보완 질문 초안</h2>
        <p>확인 필요 칸만. 값을 대신 채우지 않는다.</p>
      </div>
      {questions.length === 0 ? (
        <p className="muted">물어볼 항목이 없습니다.</p>
      ) : (
        <ol className="questions">
          {questions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ol>
      )}
    </section>
  )
}
