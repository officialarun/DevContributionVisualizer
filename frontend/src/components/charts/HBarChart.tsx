import { Link } from 'react-router-dom'
import { fmtInt } from '../../lib/format'

export interface BarItem {
  key: string | number
  label: string
  value: number
  title?: string // hover detail
  to?: string
}

interface Props {
  items: BarItem[]
  format?: (n: number) => string
  color?: string
}

/** Horizontal bar chart: one bar per row, sorted by the caller. HTML/CSS so labels truncate and wrap responsively. */
export function HBarChart({ items, format = fmtInt, color }: Props) {
  const top = Math.max(1, ...items.map((i) => i.value))
  return (
    <div className="hbar" role="list">
      {items.map((it) => (
        <div className="hbar-row" role="listitem" key={it.key} title={it.title ?? `${it.label}: ${format(it.value)}`}>
          <div className="hbar-label">{it.to ? <Link to={it.to}>{it.label}</Link> : it.label}</div>
          <div className="hbar-track">
            <div className="hbar-bar" style={{ width: `${(it.value / top) * 100}%`, background: color }} />
          </div>
          <div className="hbar-val">{format(it.value)}</div>
        </div>
      ))}
    </div>
  )
}
