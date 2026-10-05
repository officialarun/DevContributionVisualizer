import { useState } from 'react'
import type { ReactNode } from 'react'

interface Props {
  title: string
  question: string // the one question this chart answers
  actions?: ReactNode
  chart: ReactNode
  table?: ReactNode
}

export function ChartCard({ title, question, actions, chart, table }: Props) {
  const [asTable, setAsTable] = useState(false)
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>{title}</h2>
          <p>{question}</p>
        </div>
        <div className="row">
          {actions}
          {table && (
            <button className="btn" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
              {asTable ? 'Chart' : 'Table'}
            </button>
          )}
        </div>
      </div>
      {asTable && table ? table : chart}
    </section>
  )
}
