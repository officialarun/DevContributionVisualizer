import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ApiFilters } from '../api/client'

export interface FilterState {
  from: string
  to: string
  dev: number | null
}

/** Global filters live in the URL query string, so every view is shareable. */
export function useFilters() {
  const [params, setParams] = useSearchParams()
  const from = params.get('from') ?? ''
  const to = params.get('to') ?? ''
  const dev = params.get('dev') ? Number(params.get('dev')) : null

  const set = useCallback(
    (patch: Partial<FilterState>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [k, v] of Object.entries(patch)) {
            if (v === null || v === '' || v === undefined) next.delete(k)
            else next.set(k, String(v))
          }
          return next
        },
        { replace: true },
      )
    },
    [setParams],
  )

  const clear = useCallback(() => set({ from: '', to: '', dev: null }), [set])

  /** Filters for the API. `pinnedDev` (developer page) overrides the URL's developer. */
  const apiFilters = useCallback(
    (opts: { developer?: number | null; ignoreDeveloper?: boolean } = {}): ApiFilters => {
      const f: ApiFilters = {}
      if (from) f.from = from
      if (to) f.to = to
      const d = opts.ignoreDeveloper ? null : (opts.developer ?? dev)
      if (d !== null) f.developer_id = d
      return f
    },
    [from, to, dev],
  )

  /** Query string carrying only the date range (used when linking to a developer's page). */
  const dateSearch = useMemo(() => {
    const sp = new URLSearchParams()
    if (from) sp.set('from', from)
    if (to) sp.set('to', to)
    const s = sp.toString()
    return s ? `?${s}` : ''
  }, [from, to])

  return useMemo(
    () => ({ from, to, dev, set, clear, apiFilters, dateSearch, active: !!(from || to || dev !== null) }),
    [from, to, dev, set, clear, apiFilters, dateSearch],
  )
}
