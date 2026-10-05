import { Link } from 'react-router-dom'
import { useFiles } from '../../api/hooks'
import type { ApiFilters } from '../../api/client'
import { fmtDate, fmtInt } from '../../lib/format'
import { QueryBoundary } from '../states/QueryBoundary'
import { ChartCard } from './ChartCard'
import { HBarChart } from './HBarChart'

/** Q: which files change most often? */
export function TopFilesCard({ repoId, filters, filesLink }: { repoId: number; filters: ApiFilters; filesLink: string }) {
  const q = useFiles(repoId, filters, { sort: 'commits', limit: 10 })
  return (
    <ChartCard
      title="Most frequently modified files"
      question="Which files are changed in the most commits?"
      actions={<Link to={filesLink}>All files →</Link>}
      chart={
        <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0} emptyMessage="No files modified for these filters">
          {(d) => (
            <HBarChart
              items={d.items.map((f) => ({
                key: f.id,
                label: f.path,
                value: f.commits,
                title: `${f.path}\n${fmtInt(f.commits)} commits · +${fmtInt(f.additions)} −${fmtInt(f.deletions)} · ${f.developers} developer${f.developers === 1 ? '' : 's'} · last ${fmtDate(f.last_modified_at)}`,
              }))}
            />
          )}
        </QueryBoundary>
      }
    />
  )
}
