import type { WorkingDraft } from "../domain/smart-fix.ts"
import { FIELD_ORDER, FIELD_NAMES } from "../domain/catalog.ts"

type Props = {
  draft: WorkingDraft
  canSubmit: boolean
  poNumber: string | null
  supplier: string
  priority: string
  onSupplier: (v: string) => void
  onPriority: (v: string) => void
  onSubmit: () => void
}

export function SubmitPanel({
  draft,
  canSubmit,
  poNumber,
  supplier,
  priority,
  onSupplier,
  onPriority,
  onSubmit,
}: Props) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>4단계 · 발주신청서 발주요청</h2>
        <p>전자 발주신청서(PO) 미리보기 · 공급업체 견적 접수 전송</p>
      </div>
      {!canSubmit ? (
        <p className="warn-banner">사전 검수에서 검수 책임자 확인이 필요합니다.</p>
      ) : null}
      <div className="po-preview">
        <header>
          <p className="eyebrow">CPMS · 공식 전자 발주신청서</p>
          <h3>{poNumber ?? "발주 번호 미부여"}</h3>
        </header>
        <dl>
          {FIELD_ORDER.map((id) => (
            <div key={id}>
              <dt>{FIELD_NAMES[id]}</dt>
              <dd className="mono">{draft[id].value || "—"}</dd>
            </div>
          ))}
          <div>
            <dt>공급업체</dt>
            <dd>
              <input
                value={supplier}
                onChange={(e) => onSupplier(e.target.value)}
                disabled={!canSubmit || Boolean(poNumber)}
                placeholder="예: ○○상사"
              />
            </dd>
          </div>
          <div>
            <dt>우선순위</dt>
            <dd>
              <select
                value={priority}
                onChange={(e) => onPriority(e.target.value)}
                disabled={!canSubmit || Boolean(poNumber)}
              >
                <option value="보통">보통</option>
                <option value="긴급">긴급</option>
                <option value="초긴급">초긴급 (EMERGENCY)</option>
              </select>
            </dd>
          </div>
        </dl>
        {poNumber ? (
          <p className="ok-banner">
            발주요청 완료 · {poNumber} · 실시간 파이프라인에 등록되었습니다.
          </p>
        ) : (
          <button
            type="button"
            className="btn-filled"
            disabled={!canSubmit || !supplier.trim()}
            onClick={onSubmit}
          >
            발주신청서 전송 및 발주요청 완료
          </button>
        )}
      </div>
    </section>
  )
}
