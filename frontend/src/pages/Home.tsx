import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAddRepository, useRepositories } from '../api/hooks'
import { QueryBoundary } from '../components/states/QueryBoundary'
import { fmtDateTime, fmtInt } from '../lib/format'

export default function Home() {
  const [path, setPath] = useState('')
  const add = useAddRepository()
  const repos = useRepositories()
  const nav = useNavigate()

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!path.trim()) return
    add.mutate(path.trim(), { onSuccess: (r) => nav(`/r/${r.id}`) })
  }

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Repositories</h1>
        <p>Analyze a Git repository on this machine to see who contributed, when, and where.</p>
      </div>

      <form className="card" onSubmit={submit}>
        <h2>Analyze a repository</h2>
        <p className="muted" style={{ margin: '2px 0 12px' }}>
          Absolute path to a local repository. Analyzing again later only reads new commits.
        </p>
        <div className="row">
          <input
            className="input"
            style={{ flex: 1, minWidth: 260 }}
            placeholder="/home/you/projects/my-repo"
            aria-label="Repository path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
          />
          <button className="btn primary" disabled={add.isPending || !path.trim()}>
            {add.isPending ? 'Starting…' : 'Analyze'}
          </button>
        </div>
        {add.isError && (
          <p role="alert" style={{ color: 'var(--critical)', margin: '8px 0 0' }}>
            {add.error.message}
          </p>
        )}
      </form>

      <section className="card">
        <div className="card-head">
          <h2>Analyzed repositories</h2>
        </div>
        <QueryBoundary query={repos} isEmpty={(r) => r.length === 0} emptyMessage="No repositories yet. Add one above." >
          {(list) => (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Repository</th>
                    <th>Status</th>
                    <th className="num">Commits analyzed</th>
                    <th>Last analyzed</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link to={`/r/${r.id}`}>{r.name}</Link>
                        <div className="muted mono">{r.path}</div>
                      </td>
                      <td>
                        <span className={`badge ${r.status}`}>
                          {r.status === 'running'
                            ? `analyzing ${fmtInt(r.commits_processed)}/${fmtInt(r.commits_total)}`
                            : r.status}
                        </span>
                      </td>
                      <td className="num">{fmtInt(r.commits_processed)}</td>
                      <td>{r.last_analyzed_at ? fmtDateTime(r.last_analyzed_at) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryBoundary>
      </section>
    </div>
  )
}
