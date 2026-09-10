import { getAlerts, getQoe } from '@/api'
import { Background } from '@/components/Background'
import { GlassPanel } from '@/components/GlassPanel'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { usePolling } from '@/hooks/use-polling'

const STATUS_VARIANT = { healthy: 'default', watch: 'secondary', degraded: 'destructive' } as const

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString()
}

function App() {
  const alerts = usePolling(() => getAlerts(30), 3000)
  const zones = usePolling(getQoe, 3000)

  return (
    <>
      <Background step={0} />
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6 md:p-10">
        <header>
          <h1 className="text-2xl font-semibold text-slate-900">Sentinel-DNS</h1>
          <p className="text-sm text-slate-600">
            Clasificación de amenazas DNS y experiencia de red por zona -- inferencia local vía QVAC.
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          <GlassPanel className="max-w-none">
            <h2 className="mb-4 text-lg font-medium text-slate-900">Alertas de seguridad</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Hora</TableHead>
                  <TableHead>Zona</TableHead>
                  <TableHead>Dominio</TableHead>
                  <TableHead>Veredicto</TableHead>
                  <TableHead>Motivo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts === null && (
                  <TableRow>
                    <TableCell colSpan={5}>Cargando…</TableCell>
                  </TableRow>
                )}
                {alerts?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-slate-500">
                      Sin alertas todavía -- el pipeline sigue observando el stream.
                    </TableCell>
                  </TableRow>
                )}
                {alerts?.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{formatTime(a.created_at)}</TableCell>
                    <TableCell>{a.client_zone}</TableCell>
                    <TableCell className="max-w-48 truncate" title={a.qname}>{a.qname}</TableCell>
                    <TableCell>
                      <Badge variant="destructive">{a.verdict}</Badge>
                    </TableCell>
                    <TableCell className="max-w-72 truncate whitespace-normal text-slate-600" title={a.reasoning}>
                      {a.reasoning}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </GlassPanel>

          <GlassPanel className="max-w-none">
            <h2 className="mb-4 text-lg font-medium text-slate-900">Experiencia de red por zona</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Zona</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Puntaje</TableHead>
                  <TableHead>Latencia</TableHead>
                  <TableHead>NXDOMAIN</TableHead>
                  <TableHead>QPS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(zones === null || zones.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6}>{zones === null ? 'Cargando…' : 'Esperando datos suficientes…'}</TableCell>
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
