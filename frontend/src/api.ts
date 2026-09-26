// OWNER: Ojas. Every backend call and every image/static URL goes through this file.
import type { AnalysisResult, CaseSummary, Health, Review, Sample } from './types'
import mock from './mock.json'
import mockMetrics from './mock-metrics.json'

export const MOCK = import.meta.env.VITE_MOCK === '1'

function readBase(): string {
  try {
    return localStorage.getItem('unmask_api') || import.meta.env.VITE_API_BASE || ''
  } catch {
    return import.meta.env.VITE_API_BASE || ''
  }
}

export let BASE = readBase().replace(/\/$/, '')

export function setBase(url: string | null) {
  try {
    if (url) localStorage.setItem('unmask_api', url)
    else localStorage.removeItem('unmask_api')
  } catch { /* ignore */ }
  BASE = readBase().replace(/\/$/, '')
}

/** Prefix a root-relative path ("/static/..." or "/api/...") with the backend base. */
export function apiUrl(path?: string): string {
  if (!path) return ''
  if (/^(https?:|data:|blob:)/.test(path) || path.startsWith('/mock/')) return path
  return BASE + path
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(apiUrl(path), init)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

const mockResult = mock as AnalysisResult

export const api = {
  health: () => j<Health>('/api/health'),
  analyze: (file: File) => {
    if (MOCK) return Promise.resolve(mockResult)
    const fd = new FormData()
    fd.append('file', file)
    return j<AnalysisResult>('/api/analyze', { method: 'POST', body: fd })
  },
  samples: () => (MOCK ? Promise.resolve([] as Sample[]) : j<Sample[]>('/api/samples')),
  cases: () => (MOCK ? Promise.resolve([mockResult as CaseSummary]) : j<CaseSummary[]>('/api/cases')),
  getCase: (id: string) => (MOCK ? Promise.resolve(mockResult) : j<AnalysisResult>(`/api/cases/${id}`)),
  review: (id: string, decision: Review['decision'], note: string) =>
    MOCK
      ? Promise.resolve({ ...mockResult, review: { decision, note, at: new Date().toISOString() } })
      : j<AnalysisResult>(`/api/cases/${id}/review`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, note }),
        }),
  metrics: () => (MOCK ? Promise.resolve(mockMetrics) : j<typeof mockMetrics>('/api/metrics')),
  reportUrl: (id: string) => apiUrl(`/api/cases/${id}/report`),
}
