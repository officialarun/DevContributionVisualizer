import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { DeveloperStats } from '../api/client'
import { fmtDate, fmtInt, fmtMinus, fmtPlus } from '../lib/format'
import { useFilters } from '../hooks/useFilters'

type Key = 'commits' | 'additions' | 'deletions' | 'files_touched' | 'name' | 'last_commit_at'

const COLS: { key: Key; label: string; num?: boolean }[] = [
  { key: 'commits', label: 'Commits', num: true },
  { key: 'additions', label: 'Lines added', num: true },
  { key: 'deletions', label: 'Lines deleted', num: true },
  { key: 'files_touched', label: 'Files touched', num: true },
  { key: 'last_commit_at', label: 'Last active' },
]

export function DeveloperTable({ devs, repoId, selectedId }: { devs: DeveloperStats[]; repoId: number; selectedId?: number | null }) {
  const F = useFilters()
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: 'commits', dir: -1 })
  const rows = [...devs].sort((a, b) => {
    const x = a[sort.key] ?? ''
    const y = b[sort.key] ?? ''
    return (x < y ? -1 : x > y ? 1 : 0) * sort.dir || a.name.localeCompare(b.name)
  })
  const toggle = (key: Key) => setSort((s) => (s.key === key ? { key, dir: (-s.dir) as 1 | -1 } : { key, dir: key === 'name' ? 1 : -1 }))
  const arrow = (k: Key) => (sort.key === k ? (sort.dir === 1 ? ' ▲' : ' ▼') : '')

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th aria-sort={sort.key === 'name' ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}>
              <button onClick={() => toggle('name')}>Developer{arrow('name')}</button>
            </th>
            {COLS.map((c) => (
              <th
                key={c.key}
                className={c.num ? 'num' : undefined}
                aria-sort={sort.key === c.key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}
              >
                <button onClick={() => toggle(c.key)}>
                  {c.label}
                  {arrow(c.key)}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.id} style={d.id === selectedId ? { background: 'var(--hover)' } : undefined}>
              <td>
                <Link to={`/r/${repoId}/developers/${d.id}${F.dateSearch}`}>{d.name}</Link>
                <div className="muted" style={{ fontSize: 12 }}>{d.email}</div>
              </td>
              <td className="num">{fmtInt(d.commits)}</td>
              <td className="num add">{fmtPlus(d.additions)}</td>
              <td className="num del">{fmtMinus(d.deletions)}</td>
              <td className="num">{fmtInt(d.files_touched)}</td>
              <td>{fmtDate(d.last_commit_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
