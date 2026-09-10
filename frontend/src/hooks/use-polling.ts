import { useEffect, useState } from 'react'

export interface PollResult<T> {
  data: T | null
  error: boolean
}

// Polling, not SSE/WebSocket: the "must run over a live stream" requirement
// is a backend property (the pipeline never touches a static file) --
// polling this cheaply is the simplest correct transport for a dashboard.
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number): PollResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    const tick = () => {
      fetcher().then(
        (result) => {
          if (!cancelled) {
            setData(result)
            setError(false)
          }
        },
        () => {
          if (!cancelled) setError(true)
        },
      )
    }
    tick()
    const id = setInterval(tick, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs])

  return { data, error }
}
