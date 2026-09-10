export interface Alert {
  id: number
  client_zone: string
  client_id: string
  qname: string
  heuristic_kind: string
  heuristic_score: number
  verdict: string
  confidence: number
  reasoning: string
  created_at: string
}

export interface ZoneQoe {
  zone: string
  avg_latency_ms: number
  nxdomain_rate: number
  qps: number
  score: number
  status: 'healthy' | 'watch' | 'degraded'
  updated_at: string
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export function getAlerts(limit = 50): Promise<Alert[]> {
  return fetch(`/api/alerts?limit=${limit}`).then(unwrap<Alert[]>)
}

export function getQoe(): Promise<ZoneQoe[]> {
  return fetch('/api/qoe').then(unwrap<ZoneQoe[]>)
}
