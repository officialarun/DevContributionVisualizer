import { useEffect, useRef } from 'react'
import { Link, NavLink, Outlet, useLocation, useMatch } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAnalyze, useRepository } from '../../api/hooks'
import { ApiError } from '../../api/client'
import type { Repository } from '../../api/client'
import { FilterBar } from '../filters/FilterBar'
import { ErrorState, Skeleton } from '../states/QueryBoundary'
import { useRepoId } from '../../hooks/useRepoId'
import { fmtDateTime, fmtInt } from '../../lib/format'

function Progress({ repo }: { repo: Repository }) {
  const pct = repo.commits_total ? Math.round((repo.commits_processed / repo.commits_total) * 100) : 0
  return (
    <div>
      <strong>Analyzing history…</strong>{' '}
      <span className="muted">
        {fmtInt(repo.commits_processed)} / {fmtInt(repo.commits_total)} commits
      </span>
      <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function RepoLayout() {
  const id = useRepoId()
  const repoQ = useRepository(id)
  const analyze = useAnalyze(id)
  const qc = useQueryClient()
  const { search } = useLocation()
  const onDeveloperPage = !!useMatch('/r/:id/developers/:dev')

  // When an analysis finishes, every cached number is stale.
  const prev = useRef<string | undefined>(undefined)
  const status = repoQ.data?.status
  useEffect(() => {
    if (prev.current === 'running' && status && status !== 'running') qc.invalidateQueries({ queryKey: ['r', id] })
    prev.current = status
  }, [status, id, qc])

  if (repoQ.isPending) return <Skeleton height={120} />
  if (repoQ.isError) {
    const notFound = repoQ.error instanceof ApiError && repoQ.error.status === 404
    return (
      <div className="card">
        <ErrorState error={notFound ? new Error('This repository does not exist.') : repoQ.error} onRetry={() => repoQ.refetch()} />
        <p className="state">
          <Link to="/">Back to repositories</Link>
        </p>
      </div>
    )
  }

  const repo = repoQ.data
  const hasData = !!repo.last_analyzed_sha
  const running = repo.status === 'running' || repo.status === 'pending'

  if (!hasData) {
    return (
      <div className="card">
        <h1>{repo.name}</h1>
        <p className="muted mono">{repo.path}</p>
        {running ? (
          <Progress repo={repo} />
        ) : (
          <>
            <ErrorState error={new Error(repo.error ?? 'The analysis did not complete.')} />
            <div className="state">
              <button className="btn primary" onClick={() => analyze.mutate()} disabled={analyze.isPending}>
                Re-analyze
              </button>
            </div>
          </>
        )}
      </div>
    )
  }

  const tab = (to: string, label: string, end = false) => (
    <NavLink to={{ pathname: `/r/${id}${to}`, search }} end={end}>
      {label}
    </NavLink>
  )

  return (
    <div className="stack">
      <div className="page-head">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <div>
            <h1>{repo.name}</h1>
            <p className="muted mono">{repo.path}</p>
          </div>
          <div className="row">
            <span className="muted">
              Analyzed {repo.last_analyzed_at ? fmtDateTime(repo.last_analyzed_at) : '—'} @{' '}
              <span className="mono">{repo.last_analyzed_sha?.slice(0, 7)}</span>
            </span>
            <button className="btn" onClick={() => analyze.mutate()} disabled={running || analyze.isPending}>
              {running ? 'Updating…' : 'Update analysis'}
            </button>
          </div>
        </div>
      </div>
      {running && (
        <div className="banner">
          <Progress repo={repo} />
          Numbers shown may be incomplete until this finishes.
        </div>
      )}
      {repo.status === 'failed' && (
        <div className="banner" role="alert">
          The last update failed: {repo.error}
        </div>
      )}
      {repo.is_shallow && (
        <div className="banner">
          This is a shallow clone: history before the clone depth is missing, so totals are incomplete.
        </div>
      )}
      <nav className="nav" aria-label="Sections">
        {tab('', 'Dashboard', true)}
        {tab('/developers', 'Developers')}
        {tab('/files', 'Files')}
        {tab('/commits', 'Commits')}
      </nav>
      <FilterBar hideDeveloper={onDeveloperPage} />
      <Outlet />
    </div>
  )
}
