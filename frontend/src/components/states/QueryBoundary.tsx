import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { useFilters } from '../../hooks/useFilters'

export function Skeleton({ height = 160 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} aria-busy="true" aria-label="Loading" />
}

export function EmptyState({ message, showClear = true }: { message: string; showClear?: boolean }) {
  const { active, clear } = useFilters()
  return (
    <div className="state">
      <strong>{message}</strong>
      {showClear && active && (
        <button className="btn" onClick={clear}>
          Clear filters
        </button>
      )}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="state error" role="alert">
      <strong>Something went wrong</strong>
      <div style={{ marginBottom: 8 }}>{error.message}</div>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

interface Props<T> {
  query: UseQueryResult<T>
  children: (data: T) => ReactNode
  isEmpty?: (data: T) => boolean
  emptyMessage?: string
  height?: number
}

/** One place for loading / error / empty handling. */
export function QueryBoundary<T>({ query, children, isEmpty, emptyMessage = 'No data for these filters', height }: Props<T>) {
  if (query.isPending) return <Skeleton height={height} />
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  if (isEmpty?.(query.data)) return <EmptyState message={emptyMessage} />
  return <div style={{ opacity: query.isPlaceholderData ? 0.6 : 1, transition: 'opacity .15s' }}>{children(query.data)}</div>
}
