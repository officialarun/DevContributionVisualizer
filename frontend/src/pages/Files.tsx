import { useState } from 'react'
import { useFiles } from '../api/hooks'
import type { FileSort } from '../api/client'
import { Pager } from '../components/Pager'
import { QueryBoundary } from '../components/states/QueryBoundary'
import { useDebounced } from '../hooks/useDebounced'
import { useFilters } from '../hooks/useFilters'
import { useRepoId } from '../hooks/useRepoId'
import { fmtDate, fmtInt, fmtMinus, fmtPlus } from '../lib/format'

const LIMIT = 25
const SORTS: { key: FileSort; label: string }[] = [
  { key: 'commits', label: 'Commits' },
  { key: 'additions', label: 'Lines added' },
  { key: 'deletions', label: 'Lines deleted' },
  { key: 'developers', label: 'Developers' },
  { key: 'last_modified', label: 'Last modified' },
]

export default function Files() {
  const id = useRepoId()
  const F = useFilters()
  const [text, setText] = useState('')
  const q = useDebounced(text.trim())
  const [sort, setSort] = useState<FileSort>('commits')
  const [offset, setOffset] = useState(0)
  const query = useFiles(id, F.apiFilters(), { q: q || undefined, sort, limit: LIMIT, offset })

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>Files</h2>
          <p>Which files are modified most often, and by how many developers?</p>
        </div>
        <div className="row">
          <input
            className="input"
            placeholder="Search path…"
            aria-label="Search file path"
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              setOffset(0)
            }}
          />
          <label className="row muted">
            Sort by
            <select
              className="input"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value as FileSort)
                setOffset(0)
              }}
            >
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <QueryBoundary query={query} isEmpty={(d) => d.total === 0} emptyMessage={q ? `No files match “${q}”` : 'No files modified for these filters'}>
        {(d) => {
          const top = Math.max(1, ...d.items.map((f) => f.commits))
          return (
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Path</th>
                      <th className="num">Commits</th>
                      <th className="num">Lines added</th>
                      <th className="num">Lines deleted</th>
                      <th className="num">Developers</th>
                      <th>Last modified</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.items.map((f) => (
                      <tr key={f.id}>
                        <td className="mono" style={{ wordBreak: 'break-all' }}>{f.path}</td>
                        <td className="num">
                          <span className="inline-bar" style={{ width: Math.max(2, (f.commits / top) * 60) }} />
                          {fmtInt(f.commits)}
                        </td>
                        <td className="num">{fmtPlus(f.additions)}</td>
                        <td className="num">{fmtMinus(f.deletions)}</td>
                        <td className="num">{fmtInt(f.developers)}</td>
                        <td>{fmtDate(f.last_modified_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pager offset={offset} limit={LIMIT} total={d.total} onChange={setOffset} />
            </>
          )
        }}
      </QueryBoundary>
    </section>
  )
}
