import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useActivity, useDevelopers, useSummary } from '../api/hooks'
import type { Granularity } from '../api/client'
import { CommitsActivityCard, ChurnCard } from '../components/charts/ActivityCards'
import { TopFilesCard } from '../components/charts/TopFilesCard'
import { DeveloperTable } from '../components/DeveloperTable'
import { SummaryTiles } from '../components/SummaryTiles'
import { QueryBoundary } from '../components/states/QueryBoundary'
import { useFilters } from '../hooks/useFilters'
import { useRepoId } from '../hooks/useRepoId'

const PREVIEW = 10

export default function Dashboard() {
  const id = useRepoId()
  const F = useFilters()
  const f = F.apiFilters()
  const [g, setG] = useState<Granularity>('auto')

  const summary = useSummary(id, f)
  // The table shows everyone in the date range; the selected developer is highlighted.
  const devs = useDevelopers(id, F.apiFilters({ ignoreDeveloper: true }))
  const activity = useActivity(id, f, g)

  return (
    <div className="stack">
      <QueryBoundary query={summary} height={90}>
        {(s) => <SummaryTiles s={s} />}
      </QueryBoundary>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>Developer contribution</h2>
            <p>Who contributed, and how much activity does each developer have in this range?</p>
          </div>
          <Link to={`/r/${id}/developers${F.dateSearch}`}>All developers →</Link>
        </div>
        <QueryBoundary query={devs} isEmpty={(d) => d.length === 0} emptyMessage="No developers in this date range">
          {(d) => (
            <>
              <DeveloperTable devs={d.slice(0, PREVIEW)} repoId={id} selectedId={F.dev} />
              {d.length > PREVIEW && (
                <p className="muted" style={{ marginBottom: 0 }}>
                  Showing {PREVIEW} of {d.length} developers, ordered by commits.
                </p>
              )}
            </>
          )}
        </QueryBoundary>
      </section>

      <CommitsActivityCard query={activity} granularity={g} onGranularity={setG} />

      <div className="grid-2">
        <ChurnCard query={activity} />
        <TopFilesCard repoId={id} filters={f} filesLink={`/r/${id}/files`} />
      </div>
    </div>
  )
}
