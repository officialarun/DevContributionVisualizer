import type { UseQueryResult } from '@tanstack/react-query'
import type { Activity, Granularity } from '../../api/client'
import { parseDay } from '../../lib/format'
import { ChartCard } from './ChartCard'
import { LineChart, LineChartTable } from './LineChart'
import type { Series } from './LineChart'
import { QueryBoundary } from '../states/QueryBoundary'

export function GranularityControl({ value, onChange }: { value: Granularity; onChange: (g: Granularity) => void }) {
  return (
    <div className="seg" role="group" aria-label="Time bucket">
      {(['auto', 'day', 'week', 'month'] as const).map((g) => (
        <button key={g} aria-pressed={value === g} onClick={() => onChange(g)}>
          {g === 'auto' ? 'Auto' : g[0].toUpperCase() + g.slice(1)}
        </button>
      ))}
    </div>
  )
}

function build(a: Activity, pick: { key: 'commits' | 'additions' | 'deletions'; label: string; color: string }[]) {
  const dates = a.buckets.map((b) => parseDay(b.date))
  const series: Series[] = pick.map((p) => ({
    key: p.key,
    label: p.label,
    color: p.color,
    values: a.buckets.map((b) => b[p.key]),
  }))
  return { dates, series }
}

interface Props {
  query: UseQueryResult<Activity>
  granularity: Granularity
  onGranularity: (g: Granularity) => void
  title?: string
}

/** Q: when was activity high or low? */
export function CommitsActivityCard({ query, granularity, onGranularity, title = 'Activity over time' }: Props) {
  return (
    <ChartCard
      title={title}
      question={`How many commits per ${query.data?.granularity ?? 'period'}, and when was activity high or low?`}
      actions={<GranularityControl value={granularity} onChange={onGranularity} />}
      chart={
        <QueryBoundary query={query} isEmpty={(a) => a.buckets.length === 0} emptyMessage="No commits match these filters" height={260}>
          {(a) => {
            const { dates, series } = build(a, [{ key: 'commits', label: 'Commits', color: 'var(--series-1)' }])
            return <LineChart dates={dates} series={series} granularity={a.granularity} label="Commits over time" />
          }}
        </QueryBoundary>
      }
      table={
        <QueryBoundary query={query} isEmpty={(a) => a.buckets.length === 0}>
          {(a) => {
            const { dates, series } = build(a, [{ key: 'commits', label: 'Commits', color: 'var(--series-1)' }])
            return <LineChartTable dates={dates} series={series} granularity={a.granularity} />
          }}
        </QueryBoundary>
      }
    />
  )
}

const CHURN = [
  { key: 'additions', label: 'Lines added', color: 'var(--series-1)' },
  { key: 'deletions', label: 'Lines deleted', color: 'var(--series-2)' },
] as const

/** Q: how did the volume of code change over time? */
export function ChurnCard({ query }: { query: UseQueryResult<Activity> }) {
  return (
    <ChartCard
      title="Lines added vs deleted"
      question="How much code was added and removed over time?"
      chart={
        <QueryBoundary query={query} isEmpty={(a) => a.buckets.length === 0} emptyMessage="No commits match these filters" height={260}>
          {(a) => {
            const { dates, series } = build(a, [...CHURN])
            return <LineChart dates={dates} series={series} granularity={a.granularity} label="Lines added and deleted over time" />
          }}
        </QueryBoundary>
      }
      table={
        <QueryBoundary query={query} isEmpty={(a) => a.buckets.length === 0}>
          {(a) => {
            const { dates, series } = build(a, [...CHURN])
            return <LineChartTable dates={dates} series={series} granularity={a.granularity} />
          }}
        </QueryBoundary>
      }
    />
  )
}
