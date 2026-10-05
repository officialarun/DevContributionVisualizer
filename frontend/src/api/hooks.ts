import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { ApiFilters, FileSort, Granularity } from './client'

const keep = { placeholderData: keepPreviousData }

export const useRepositories = () =>
  useQuery({
    queryKey: ['repositories'],
    queryFn: api.listRepositories,
    refetchInterval: (q) => (q.state.data?.some((r) => r.status === 'running') ? 1500 : false),
  })

export const useRepository = (id: number) =>
  useQuery({
    queryKey: ['repository', id],
    queryFn: () => api.getRepository(id),
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 1000 : false),
  })

export const useSummary = (id: number, f: ApiFilters) =>
  useQuery({ queryKey: ['r', id, 'summary', f], queryFn: () => api.summary(id, f), ...keep })

export const useDevelopers = (id: number, f: ApiFilters) =>
  useQuery({ queryKey: ['r', id, 'developers', f], queryFn: () => api.developers(id, f), ...keep })

export const useDeveloper = (id: number, devId: number, f: ApiFilters) =>
  useQuery({ queryKey: ['r', id, 'developer', devId, f], queryFn: () => api.developer(id, devId, f), ...keep })

export const useActivity = (id: number, f: ApiFilters, g: Granularity) =>
  useQuery({ queryKey: ['r', id, 'activity', f, g], queryFn: () => api.activity(id, f, g), ...keep })

export const useFiles = (
  id: number,
  f: ApiFilters,
  o: { q?: string; sort?: FileSort; limit?: number; offset?: number },
) => useQuery({ queryKey: ['r', id, 'files', f, o], queryFn: () => api.files(id, f, o), ...keep })

export const useCommits = (id: number, f: ApiFilters, o: { q?: string; limit?: number; offset?: number }) =>
  useQuery({ queryKey: ['r', id, 'commits', f, o], queryFn: () => api.commits(id, f, o), ...keep })

export const useCommit = (id: number, sha: string | null) =>
  useQuery({ queryKey: ['r', id, 'commit', sha], queryFn: () => api.commit(id, sha!), enabled: !!sha })

export function useAddRepository() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.addRepository,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['repositories'] }),
  })
}

export function useAnalyze(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.analyze(id),
    onSuccess: (repo) => {
      qc.setQueryData(['repository', id], repo)
      qc.invalidateQueries({ queryKey: ['repositories'] })
    },
  })
}
