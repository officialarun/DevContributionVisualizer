import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useActivity, useDeveloper, useSummary } from '../api/hooks'
import type { Granularity } from '../api/client'
import { CommitsActivityCard, ChurnCard } from '../components/charts/ActivityCards'
import { TopFilesCard } from '../components/charts/TopFilesCard'
import { Tile } from '../components/SummaryTiles'
import { QueryBoundary } from '../components/states/QueryBoundary'
import { useFilters } from '../hooks/useFilters'
import { useRepoId } from '../hooks/useRepoId'
import { fmtDate, fmtInt, fmtPct } from '../lib/format'

/** Same endpoints and components as the dashboard, with the developer pinned from the URL. */
export default function DeveloperDetail() {
  const id = useRepoId()
  const devId = Number(useParams().dev)
  const F = useFilters()
  const pinned = F.apiFilters({ developer: devId })
  const dateOnly = F.apiFilters({ ignoreDeveloper: true })
  const [g, setG] = useState<Granularity>('auto')

  const dev = useDeveloper(id, devId, dateOnly)
  const repoSummary = useSummary(id, dateOnly)
  const devSummary = useSummary(id, pinned)
  const activity = useActivity(id, pinned, g)

  return (
    <div className="stack">
      <div>
        <Link to={`/r/${id}/developers${F.dateSearch}`}>← All developers</Link>
      </div>

      <QueryBoundary query={dev} height={110} emptyMessage="">
        {(d) => (
          <>
            <div className="page-head" style={{ marginBottom: 0 }}>
              <h1>{d.name}</h1>
              <p className="muted">{d.email}</p>
            </div>
            <div className="tiles">
              <Tile label="Commits" value={fmtInt(d.commits)} />
              <Tile label="Lines added" value={fmtInt(d.additions)} />
              <Tile label="Lines deleted" value={fmtInt(d.deletions)} />
              <Tile label="Files touched" value={fmtInt(d.files_touched)} />
              <Tile label="First contribution" value={fmtDate(d.first_commit_at)} />
              <Tile label="Last contribution" value={fmtDate(d.last_commit_at)} />
            </div>
          </>
        )}
      </QueryBoundary>

      <CommitsActivityCard
        query={activity}
        granularity={g}
        onGranularity={setG}
        title="Developer activity over time"
      />

      <div className="grid-2">
        <ChurnCard query={activity} />
        <TopFilesCard repoId={id} filters={pinned} filesLink={`/r/${id}/files?dev=${devId}${F.dateSearch.replace('?', '&')}`} />
      </div>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>Contribution summary</h2>
            <p>This developer’s share of all repository activity in the selected range.</p>
          </div>
        </div>
        <QueryBoundary query={repoSummary} height={90}>
          {(all) => (
            <QueryBoundary query={devSummary} height={90}>
              {(me) => (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Measure</th>
                        <th className="num">This developer</th>
                        <th className="num">Repository</th>
                        <th className="num">Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        [
                          ['Commits', me.commits, all.commits],
                          ['Lines added', me.additions, all.additions],
                          ['Lines deleted', me.deletions, all.deletions],
                          ['Files touched', me.files_modified, all.files_modified],
                        ] as const
                      ).map(([label, a, b]) => (
                        <tr key={label}>
                          <td>{label}</td>
                          <td className="num">{fmtInt(a)}</td>
                          <td className="num">{fmtInt(b)}</td>
                          <td className="num">{fmtPct(a, b)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </QueryBoundary>
          )}
        </QueryBoundary>
      </section>
    </div>
  )
}
