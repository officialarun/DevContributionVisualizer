import { Fragment, useState } from 'react'
import { useCommit, useCommits } from '../api/hooks'
import { Pager } from '../components/Pager'
import { QueryBoundary } from '../components/states/QueryBoundary'
import { useDebounced } from '../hooks/useDebounced'
import { useFilters } from '../hooks/useFilters'
import { useRepoId } from '../hooks/useRepoId'
import { fmtDateTime, fmtInt, fmtMinus, fmtPlus, subject } from '../lib/format'

const LIMIT = 50

function CommitDetailRow({ repoId, sha }: { repoId: number; sha: string }) {
  const q = useCommit(repoId, sha)
  return (
    <tr className="detail">
      <td colSpan={6}>
        <QueryBoundary query={q} height={80}>
          {(c) => (
            <>
              <pre className="msg">{c.message}</pre>
              <p className="muted mono" style={{ margin: '0 0 8px' }}>
                {c.sha} · {c.author_name} &lt;{c.author_email}&gt; · {fmtDateTime(c.authored_at)}
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>File</th>
                      <th className="num">Lines added</th>
                      <th className="num">Lines deleted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.files.map((f) => (
                      <tr key={f.path}>
                        <td className="mono" style={{ wordBreak: 'break-all' }}>
                          {f.old_path ? `${f.old_path} → ${f.path}` : f.path}
                          {f.is_binary && <span className="badge" style={{ marginLeft: 8 }}>binary</span>}
                        </td>
                        <td className="num">{fmtPlus(f.additions)}</td>
                        <td className="num">{fmtMinus(f.deletions)}</td>
                      </tr>
                    ))}
                    {c.files.length === 0 && (
                      <tr>
                        <td colSpan={3} className="muted">No file changes recorded.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </QueryBoundary>
      </td>
    </tr>
  )
}

export default function Commits() {
  const id = useRepoId()
  const F = useFilters()
  const [text, setText] = useState('')
  const q = useDebounced(text.trim())
  const [offset, setOffset] = useState(0)
  const [open, setOpen] = useState<string | null>(null)
  const query = useCommits(id, F.apiFilters(), { q: q || undefined, limit: LIMIT, offset })

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>Commits</h2>
          <p>What changed, when, and by whom? Select a commit to see its files.</p>
        </div>
        <input
          className="input"
          placeholder="Search message, author or hash…"
          aria-label="Search commits"
          style={{ minWidth: 260 }}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            setOffset(0)
          }}
        />
      </div>
      <QueryBoundary query={query} isEmpty={(d) => d.total === 0} emptyMessage={q ? `No commits match “${q}”` : 'No commits match these filters'}>
        {(d) => (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Hash</th>
                    <th>Message</th>
                    <th>Author</th>
                    <th>Date</th>
                    <th className="num">Files</th>
                    <th className="num">Lines</th>
                  </tr>
                </thead>
                <tbody>
                  {d.items.map((c) => (
                    <Fragment key={c.sha}>
                      <tr
                        className="clickable"
                        tabIndex={0}
                        aria-expanded={open === c.sha}
                        onClick={() => setOpen(open === c.sha ? null : c.sha)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setOpen(open === c.sha ? null : c.sha)
                          }
                        }}
                      >
                        <td className="mono">{c.short_sha}</td>
                        <td className="cell-ellipsis" title={subject(c.message)}>{subject(c.message)}</td>
                        <td>{c.author_name}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>{fmtDateTime(c.authored_at)}</td>
                        <td className="num">{fmtInt(c.files_changed)}</td>
                        <td className="num">
                          {fmtPlus(c.additions)} {fmtMinus(c.deletions)}
                        </td>
                      </tr>
                      {open === c.sha && <CommitDetailRow repoId={id} sha={c.sha} />}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            <Pager offset={offset} limit={LIMIT} total={d.total} onChange={(o) => { setOffset(o); setOpen(null) }} />
          </>
        )}
      </QueryBoundary>
    </section>
  )
}
