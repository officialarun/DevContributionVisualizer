import { useDevelopers } from '../../api/hooks'
import { useFilters } from '../../hooks/useFilters'
import { useRepoId } from '../../hooks/useRepoId'

export function FilterBar({ hideDeveloper = false }: { hideDeveloper?: boolean }) {
  const id = useRepoId()
  const F = useFilters()
  // The developer list ignores the developer filter so the select always shows everyone.
  const devs = useDevelopers(id, F.apiFilters({ ignoreDeveloper: true }))
  const names = new Map<string, number>()
  devs.data?.forEach((d) => names.set(d.name, (names.get(d.name) ?? 0) + 1))

  return (
    <div className="filters" role="search" aria-label="Filters">
      <label className="field">
        From (UTC)
        <input type="date" value={F.from} max={F.to || undefined} onChange={(e) => F.set({ from: e.target.value })} />
      </label>
      <label className="field">
        To (UTC)
        <input type="date" value={F.to} min={F.from || undefined} onChange={(e) => F.set({ to: e.target.value })} />
      </label>
      {!hideDeveloper && (
        <label className="field">
          Developer
          <select
            value={F.dev ?? ''}
            onChange={(e) => F.set({ dev: e.target.value ? Number(e.target.value) : null })}
            disabled={!devs.data}
          >
            <option value="">All developers</option>
            {devs.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {(names.get(d.name) ?? 0) > 1 ? `${d.name} <${d.email}>` : d.name}
              </option>
            ))}
          </select>
        </label>
      )}
      <button className="btn" onClick={F.clear} disabled={!F.active}>
        Clear filters
      </button>
    </div>
  )
}
