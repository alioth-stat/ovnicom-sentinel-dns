import { useState } from 'react'
import { getAlerts, getQoe } from '@/api'
import { Background } from '@/components/Background'
import { GlassPanel } from '@/components/GlassPanel'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { VisibilityPanel } from '@/components/VisibilityPanel'
import { usePolling } from '@/hooks/use-polling'
import { STRINGS, type Lang } from '@/lib/i18n'

const STATUS_VARIANT = { healthy: 'default', watch: 'secondary', degraded: 'destructive' } as const

// Rough severity split so a glance at the table tells kinds apart -- mirrors
// wazuh_sink.py's per-kind rule level (tunneling/beaconing > dga > typosquat).
const VERDICT_VARIANT: Record<string, 'destructive' | 'secondary' | 'outline'> = {
  dga: 'destructive',
  tunneling: 'destructive',
  beaconing: 'destructive',
  typosquat: 'secondary',
}

const LANG_STORAGE_KEY = 'sentinel-dns-lang'

function readStoredLang(): Lang {
  const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(LANG_STORAGE_KEY) : null
  return stored === 'en' ? 'en' : 'es'
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString()
}

function App() {
  const { data: alerts, error: alertsError } = usePolling(() => getAlerts(30), 3000)
  const { data: zones, error: zonesError } = usePolling(getQoe, 3000)
  const [visibilityOpen, setVisibilityOpen] = useState(false)
  const [lang, setLang] = useState<Lang>(readStoredLang)
  const t = STRINGS[lang]

  const toggleLang = () => {
    const next: Lang = lang === 'es' ? 'en' : 'es'
    setLang(next)
    try {
      localStorage.setItem(LANG_STORAGE_KEY, next)
    } catch {
      // private browsing or storage disabled -- toggle still works for this session
    }
  }

  return (
    <>
      <Background />
      <VisibilityPanel open={visibilityOpen} onClose={() => setVisibilityOpen(false)} lang={lang} />
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 md:p-10">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-primary">Sentinel-DNS</h1>
            <p className="text-sm text-muted-foreground">{t.subtitle}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={toggleLang}
              aria-label={lang === 'es' ? 'Switch to English' : 'Cambiar a español'}
              className="rounded-full border border-border px-3 py-2 text-sm font-medium text-primary transition-colors hover:bg-accent active:scale-[0.97]"
            >
              {lang === 'es' ? 'EN' : 'ES'}
            </button>
            <button
              type="button"
              onClick={() => setVisibilityOpen(true)}
              className="rounded-full border border-border px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-accent active:scale-[0.97]"
            >
              {t.transparencyButton}
            </button>
          </div>
        </header>

        {(alertsError || zonesError) && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t.backendError}</p>
        )}

        <div className="flex flex-col gap-6">
          <GlassPanel className="max-w-none">
            <h2 className="mb-4 text-lg font-medium text-primary">{t.alertsTitle}</h2>
            <div className="max-h-96 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.alertsColumns.time}</TableHead>
                    <TableHead>{t.alertsColumns.zone}</TableHead>
                    <TableHead>{t.alertsColumns.domain}</TableHead>
                    <TableHead>{t.alertsColumns.verdict}</TableHead>
                    <TableHead>{t.alertsColumns.reason}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alerts === null && (
                    <TableRow>
                      <TableCell colSpan={5}>{t.loading}</TableCell>
                    </TableRow>
                  )}
                  {alerts?.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-muted-foreground">
                        {t.noAlertsYet}
                      </TableCell>
                    </TableRow>
                  )}
                  {alerts?.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="align-top">{formatTime(a.created_at)}</TableCell>
                      <TableCell className="align-top">{a.client_zone}</TableCell>
                      <TableCell className="max-w-64 truncate align-top" title={a.qname}>{a.qname}</TableCell>
                      <TableCell className="align-top whitespace-nowrap">
                        <Badge variant={VERDICT_VARIANT[a.verdict] ?? 'outline'}>{a.verdict}</Badge>
                        <span className="ml-1 text-xs text-muted-foreground">{Math.round(a.confidence * 100)}%</span>
                      </TableCell>
                      <TableCell className="max-w-72 min-w-48 align-top" title={a.reasoning}>
                        <p className="line-clamp-2 whitespace-normal text-muted-foreground">{a.reasoning}</p>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </GlassPanel>

          <GlassPanel className="max-w-none">
            <h2 className="mb-4 text-lg font-medium text-primary">{t.qoeTitle}</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.qoeColumns.zone}</TableHead>
                  <TableHead>{t.qoeColumns.status}</TableHead>
                  <TableHead>{t.qoeColumns.score}</TableHead>
                  <TableHead>{t.qoeColumns.latency}</TableHead>
                  <TableHead>{t.qoeColumns.nxdomain}</TableHead>
                  <TableHead>{t.qoeColumns.qps}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(zones === null || zones.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6}>{zones === null ? t.loading : t.waitingForData}</TableCell>
                  </TableRow>
                )}
                {zones?.map((z) => (
                  <TableRow key={z.zone}>
                    <TableCell className="font-medium">{z.zone}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[z.status]}>{z.status}</Badge>
                    </TableCell>
                    <TableCell>{z.score.toFixed(2)}</TableCell>
                    <TableCell>{z.avg_latency_ms.toFixed(0)} ms</TableCell>
                    <TableCell>{(z.nxdomain_rate * 100).toFixed(1)}%</TableCell>
                    <TableCell>{z.qps.toFixed(1)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </GlassPanel>
        </div>
      </div>
    </>
  )
}

export default App
