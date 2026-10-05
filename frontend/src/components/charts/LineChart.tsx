import { useState } from 'react'
import { bisector, extent, max } from 'd3-array'
import { scaleLinear, scaleUtc } from 'd3-scale'
import { line } from 'd3-shape'
import { utcMonth } from 'd3-time'
import { useElementWidth } from '../../hooks/useElementWidth'
import { fmtCompact, fmtInt } from '../../lib/format'

export interface Series {
  key: string
  label: string
  color: string // CSS var, e.g. 'var(--series-1)'
  values: number[]
}

interface Props {
  dates: Date[]
  series: Series[]
  granularity: 'day' | 'week' | 'month'
  label: string // accessible description
  height?: number
}

const M = { top: 10, right: 14, bottom: 26, left: 46 }
const DAY = 86_400_000
const bisectDate = bisector((d: Date) => d.getTime()).center

const SHORT_SPAN = 75 * DAY

/** Ticks at real boundaries: days for short ranges, month starts (every k months) for long ones. */
function makeTicks(x: ReturnType<typeof scaleUtc>, span: number, maxTicks: number) {
  if (span <= SHORT_SPAN) return x.ticks(maxTicks)
  const months = span / (30.4 * DAY)
  return x.ticks(utcMonth.every(Math.max(1, Math.ceil(months / maxTicks)))!)
}

const fmtTick = (d: Date, span: number) =>
  d.toLocaleDateString(
    'en-GB',
    span <= SHORT_SPAN ? { day: 'numeric', month: 'short', timeZone: 'UTC' } : { month: 'short', year: 'numeric', timeZone: 'UTC' },
  )

export const fmtBucket = (d: Date, g: 'day' | 'week' | 'month') =>
  g === 'month'
    ? d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' })
    : (g === 'week' ? 'Week of ' : '') +
      d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })

/** Time-series line chart. D3 does the math, React renders the SVG. */
export function LineChart({ dates, series, granularity, label, height = 260 }: Props) {
  const [ref, width] = useElementWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)

  const iw = Math.max(0, width - M.left - M.right)
  const ih = height - M.top - M.bottom
  const [d0, d1] = extent(dates) as [Date, Date]
  const domain: [Date, Date] = dates.length > 1 ? [d0, d1] : [new Date(+d0 - DAY), new Date(+d0 + DAY)]
  const x = scaleUtc().domain(domain).range([0, iw])
  const yMax = max(series.flatMap((s) => s.values)) || 1
  const y = scaleLinear().domain([0, yMax]).nice().range([ih, 0])
  const path = line<number>().x((_, i) => x(dates[i])).y((v) => y(v))
  const span = +domain[1] - +domain[0]
  const xTicks = makeTicks(x, span, Math.max(2, Math.floor(iw / 96)))

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const px = e.clientX - e.currentTarget.getBoundingClientRect().left
    setHover(bisectDate(dates, x.invert(px)))
  }

  const hx = hover !== null ? x(dates[hover]) : 0
  const flip = hx > iw / 2

  return (
    <div className="chart-root" ref={ref}>
      {series.length > 1 && (
        <div className="legend">
          {series.map((s) => (
            <span key={s.key}>
              <i style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      )}
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label={label}>
          <g transform={`translate(${M.left},${M.top})`}>
            {y.ticks(4).map((t) => (
              <g key={t} transform={`translate(0,${y(t)})`}>
                <line x2={iw} stroke="var(--grid)" />
                <text x={-8} dy="0.32em" textAnchor="end" fontSize={11} fill="var(--text-muted)">
                  {fmtCompact(t)}
                </text>
              </g>
            ))}
            {xTicks.map((t) => (
              <text key={+t} x={x(t)} y={ih + 18} textAnchor="middle" fontSize={11} fill="var(--text-muted)">
                {fmtTick(t, span)}
              </text>
            ))}
            {series.map((s) => (
              <g key={s.key}>
                <path d={path(s.values) ?? ''} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" />
                {dates.length === 1 && <circle cx={x(dates[0])} cy={y(s.values[0])} r={4} fill={s.color} />}
              </g>
            ))}
            {hover !== null && (
              <g>
                <line x1={hx} x2={hx} y1={0} y2={ih} stroke="var(--text-muted)" strokeDasharray="3 3" />
                {series.map((s) => (
                  <circle key={s.key} cx={hx} cy={y(s.values[hover])} r={4.5} fill={s.color} stroke="var(--surface-1)" strokeWidth={2} />
                ))}
              </g>
            )}
            <rect
              width={iw}
              height={ih}
              fill="transparent"
              onPointerMove={onMove}
              onPointerLeave={() => setHover(null)}
            />
          </g>
        </svg>
      )}
      {hover !== null && width > 0 && (
        <div
          className="tooltip"
          style={{
            top: (series.length > 1 ? 30 : 8) + M.top,
            left: M.left + hx + (flip ? -12 : 12),
            transform: flip ? 'translateX(-100%)' : undefined,
          }}
        >
          <b>{fmtBucket(dates[hover], granularity)}</b>
          {series.map((s) => (
            <div key={s.key}>
              <i style={{ background: s.color, display: 'inline-block', width: 8, height: 8, borderRadius: 4, marginRight: 6 }} />
              {s.label}: {fmtInt(s.values[hover])}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** Same data as the chart, as a table (accessibility / exact values). */
export function LineChartTable({ dates, series, granularity }: Omit<Props, 'label' | 'height'>) {
  return (
    <div className="table-wrap" style={{ maxHeight: 300, overflowY: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>Period</th>
            {series.map((s) => (
              <th key={s.key} className="num">{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dates.map((d, i) => (
            <tr key={+d}>
              <td>{fmtBucket(d, granularity)}</td>
              {series.map((s) => (
                <td key={s.key} className="num">{fmtInt(s.values[i])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
