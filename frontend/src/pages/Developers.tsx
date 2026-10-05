import { useState } from 'react'
import { useDevelopers } from '../api/hooks'
import type { DeveloperStats } from '../api/client'
import { ChartCard } from '../components/charts/ChartCard'
import { HBarChart } from '../components/charts/HBarChart'
import { DeveloperTable } from '../components/DeveloperTable'
import { QueryBoundary } from '../components/states/QueryBoundary'
import { useFilters } from '../hooks/useFilters'
import { useRepoId } from '../hooks/useRepoId'
import { fmtInt } from '../lib/format'

const METRICS = [
  { key: 'commits', label: 'Commits' },
  { key: 'additions', label: 'Lines added' },
  { key: 'deletions', label: 'Lines deleted' },
  { key: 'files_touched', label: 'Files touched' },
] as const
type Metric = (typeof METRICS)[number]['key']
const SHOWN = 15

export default function Developers() {
  const id = useRepoId()
  const F = useFilters()
  const devs = useDevelopers(id, F.apiFilters({ ignoreDeveloper: true }))
  const [metric, setMetric] = useState<Metric>('commits')
  const label = METRICS.find((m) => m.key === metric)!.label

  const bars = (all: DeveloperStats[]) => {
    const sorted = [...all].sort((a, b) => b[metric] - a[metric] || a.name.localeCompare(b.name))
    return sorted.slice(0, SHOWN).map((d) => ({
      key: d.id,
      label: d.name,
      value: d[metric],
      to: `/r/${id}/developers/${d.id}${F.dateSearch}`,
      title: `${d.name} <${d.email}>\n${fmtInt(d.commits)} commits · +${fmtInt(d.additions)} −${fmtInt(d.deletions)} · ${fmtInt(d.files_touched)} files`,
    }))
  }

  return (
    <div className="stack">
      <ChartCard
        title="Developer comparison"
        question={`How does ${label.toLowerCase()} compare across developers?`}
        actions={
          <div className="seg" role="group" aria-label="Metric">
            {METRICS.map((m) => (
              <button key={m.key} aria-pressed={metric === m.key} onClick={() => setMetric(m.key)}>
                {m.label}
              </button>
            ))}
          </div>
        }
        chart={
          <QueryBoundary query={devs} isEmpty={(d) => d.length === 0} emptyMessage="No developers in this date range">
            {(d) => (
              <>
                <HBarChart items={bars(d)} />
                {d.length > SHOWN && (
                  <p className="muted" style={{ marginBottom: 0 }}>
                    Showing {SHOWN} of {d.length} developers, ordered by {label.toLowerCase()}. All developers are in the table below.
                  </p>
                )}
              </>
            )}
          </QueryBoundary>
        }
      />
      <section className="card">
        <div className="card-head">
          <h2>All developers</h2>
        </div>
        <QueryBoundary query={devs} isEmpty={(d) => d.length === 0} emptyMessage="No developers in this date range">
          {(d) => <DeveloperTable devs={d} repoId={id} />}
        </QueryBoundary>
      </section>
    </div>
  )
}
