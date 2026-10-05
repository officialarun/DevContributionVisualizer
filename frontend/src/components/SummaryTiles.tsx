import type { Summary } from '../api/client'
import { fmtDate, fmtInt } from '../lib/format'

export function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}

export function SummaryTiles({ s }: { s: Summary }) {
  return (
    <div className="tiles">
      <Tile label="Commits" value={fmtInt(s.commits)} sub={s.first_commit_at ? `${fmtDate(s.first_commit_at)} – ${fmtDate(s.last_commit_at)}` : undefined} />
      <Tile label="Developers" value={fmtInt(s.developers)} />
      <Tile label="Files modified" value={fmtInt(s.files_modified)} />
      <Tile label="Lines added" value={fmtInt(s.additions)} />
      <Tile label="Lines deleted" value={fmtInt(s.deletions)} />
    </div>
  )
}
