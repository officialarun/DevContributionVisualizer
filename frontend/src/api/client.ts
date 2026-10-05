import type { components } from './schema'

type S = components['schemas']
export type Repository = S['RepositoryOut']
export type Summary = S['Summary']
export type DeveloperStats = S['DeveloperStats']
export type Activity = S['Activity']
export type ActivityBucket = S['ActivityBucket']
export type FileList = S['FileList']
export type FileStats = S['FileStats']
export type CommitList = S['CommitList']
export type CommitOut = S['CommitOut']
export type CommitDetail = S['CommitDetail']

export type Granularity = 'auto' | 'day' | 'week' | 'month'
export type FileSort = 'commits' | 'additions' | 'deletions' | 'developers' | 'last_modified'

export interface ApiFilters {
  from?: string
  to?: string
  developer_id?: number
}

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') sp.set(k, String(v))
  const s = sp.toString()
  return s ? `?${s}` : ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the API server. Is the backend running?')
  }
  if (!res.ok) {
    let code = 'http_error'
    let message = res.statusText || `Request failed (${res.status})`
    try {
      const body = await res.json()
      code = body.error.code
      message = body.error.message
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code, message)
  }
  return res.json() as Promise<T>
}

const repo = (id: number) => `/repositories/${id}`

export const api = {
  listRepositories: () => request<Repository[]>('/repositories'),
  getRepository: (id: number) => request<Repository>(repo(id)),
  addRepository: (path: string) =>
    request<Repository>('/repositories', { method: 'POST', body: JSON.stringify({ path }) }),
  analyze: (id: number) => request<Repository>(`${repo(id)}/analyze`, { method: 'POST' }),
  summary: (id: number, f: ApiFilters) => request<Summary>(`${repo(id)}/summary${qs({ ...f })}`),
  developers: (id: number, f: ApiFilters) =>
    request<DeveloperStats[]>(`${repo(id)}/developers${qs({ ...f })}`),
  developer: (id: number, devId: number, f: ApiFilters) =>
    request<DeveloperStats>(`${repo(id)}/developers/${devId}${qs({ ...f })}`),
  activity: (id: number, f: ApiFilters, granularity: Granularity) =>
    request<Activity>(`${repo(id)}/activity${qs({ ...f, granularity })}`),
  files: (id: number, f: ApiFilters, o: { q?: string; sort?: FileSort; limit?: number; offset?: number }) =>
    request<FileList>(`${repo(id)}/files${qs({ ...f, ...o })}`),
  commits: (id: number, f: ApiFilters, o: { q?: string; limit?: number; offset?: number }) =>
    request<CommitList>(`${repo(id)}/commits${qs({ ...f, ...o })}`),
  commit: (id: number, sha: string) => request<CommitDetail>(`${repo(id)}/commits/${sha}`),
}
