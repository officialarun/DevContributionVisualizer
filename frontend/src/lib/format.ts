const int = new Intl.NumberFormat('en-US')
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

export const fmtInt = (n: number) => int.format(n)
export const fmtCompact = (n: number) => compact.format(n)
export const fmtPct = (part: number, whole: number) =>
  whole === 0 ? '—' : `${((part / whole) * 100).toFixed(part / whole < 0.1 ? 1 : 0)}%`

/** Dates are shown in UTC to match the server's bucketing. */
export const fmtDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }) : '—'

export const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
  }) + ' UTC'

/** 'YYYY-MM-DD' bucket label -> UTC Date */
export const parseDay = (s: string) => {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

export const subject = (message: string) => message.split('\n', 1)[0]

/** Signed line counts; zero is shown plainly rather than as "+0" / "−0". */
export const fmtPlus = (n: number) => (n === 0 ? '0' : `+${int.format(n)}`)
export const fmtMinus = (n: number) => (n === 0 ? '0' : `−${int.format(n)}`)
