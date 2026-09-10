export type Lang = 'es' | 'en'

interface Strings {
  subtitle: string
  transparencyButton: string
  backendError: string
  alertsTitle: string
  alertsColumns: { time: string; zone: string; domain: string; verdict: string; reason: string }
  loading: string
  noAlertsYet: string
  qoeTitle: string
  qoeColumns: { zone: string; status: string; score: string; latency: string; nxdomain: string; qps: string }
  waitingForData: string
  panel: {
    title: string
    close: string
    howItWorksHeading: string
    steps: string[]
    dataNote: string
    glossaryHeading: string
  }
}

export const STRINGS: Record<Lang, Strings> = {
  es: {
    subtitle: 'Clasificación de amenazas DNS y experiencia de red por zona, con inferencia local vía QVAC.',
    transparencyButton: 'Transparencia y glosario',
    backendError: 'No se pudo conectar con el backend. Verifica que esté corriendo en el puerto 8000.',
    alertsTitle: 'Alertas de seguridad',
    alertsColumns: { time: 'Hora', zone: 'Zona', domain: 'Dominio', verdict: 'Veredicto', reason: 'Motivo' },
    loading: 'Cargando…',
    noAlertsYet: 'Sin alertas todavía. El pipeline sigue observando el stream.',
    qoeTitle: 'Experiencia de red por zona',
    qoeColumns: { zone: 'Zona', status: 'Estado', score: 'Puntaje', latency: 'Latencia', nxdomain: 'NXDOMAIN', qps: 'QPS' },
    waitingForData: 'Esperando datos suficientes…',
    panel: {
      title: 'Transparencia del sistema',
      close: 'Cerrar',
      howItWorksHeading: 'Cómo funciona',
      steps: [
        '1. Heurísticos, sin IA. Reglas rápidas (entropía del nombre de dominio, distancia a marcas conocidas, intervalos de repetición fijos) deciden qué dominios son candidatos sospechosos, antes de gastar una llamada al modelo.',
        '2. Modelo QVAC local. Solo los candidatos filtrados llegan a un modelo de lenguaje pequeño (Qwen3-1.7B-Instruct) que corre en esta misma máquina, vía QVAC. Recibe únicamente el dominio consultado y las señales heurísticas, nunca historial de navegación ni datos identificables del cliente más allá de su zona, y devuelve un veredicto, un nivel de confianza y una explicación.',
        '3. Cero llamadas a la nube. Todo el paso anterior ocurre sin conexión a internet. Se puede desconectar la red de esta máquina y el sistema sigue clasificando exactamente igual.',
        '4. Score de experiencia (QoE). No usa IA: es una fórmula fija (ver "QoE" abajo) sobre latencia, tasa de NXDOMAIN y saturación, calculada por zona.',
        '5. Qué se guarda. Solo las alertas confirmadas (no el tráfico benigno) y los snapshots de QoE, en una base de datos local en este equipo. Las alertas también se escriben a un archivo de log en el formato que un SIEM real (Wazuh) puede leer directamente.',
      ],
      dataNote:
        'Nota: el contenido que genera el modelo (dominio consultado, veredicto y motivo) siempre aparece en español, sin importar este idioma de interfaz. Así fue instruido el modelo.',
      glossaryHeading: 'Glosario de términos',
    },
  },
  en: {
    subtitle: 'Real-time DNS threat classification and per-zone network experience, with inference running locally via QVAC.',
    transparencyButton: 'Transparency & glossary',
    backendError: "Couldn't connect to the backend. Check that it's running on port 8000.",
    alertsTitle: 'Security alerts',
    alertsColumns: { time: 'Time', zone: 'Zone', domain: 'Domain', verdict: 'Verdict', reason: 'Reason' },
    loading: 'Loading…',
    noAlertsYet: 'No alerts yet. The pipeline is still watching the stream.',
    qoeTitle: 'Network experience by zone',
    qoeColumns: { zone: 'Zone', status: 'Status', score: 'Score', latency: 'Latency', nxdomain: 'NXDOMAIN', qps: 'QPS' },
    waitingForData: 'Waiting for enough data…',
    panel: {
      title: 'System transparency',
      close: 'Close',
      howItWorksHeading: 'How it works',
      steps: [
        '1. Rule-based checks, no AI. Fast checks (domain-name entropy, distance to known brand names, fixed repeat intervals) decide which domains are worth escalating, before spending a call on the model.',
        '2. Local QVAC model. Only the filtered candidates reach a small language model (Qwen3-1.7B-Instruct) running on this same machine, via QVAC. It receives only the queried domain and the pre-computed signals, never browsing history or client-identifying data beyond its zone, and returns a verdict, a confidence level, and an explanation.',
        '3. Zero cloud calls. All of the above happens with no internet connection. You can disconnect this machine from the network and the system keeps classifying exactly the same.',
        '4. Experience score (QoE). No AI here: it is a fixed formula (see "QoE" below) over latency, NXDOMAIN rate, and saturation, computed per zone.',
        '5. What gets stored. Only confirmed alerts, not benign traffic, plus QoE snapshots, in a local database on this machine. Alerts are also written to a log file in a format a real SIEM (Wazuh) can read directly.',
      ],
      dataNote:
        "Note: content generated by the model (queried domain, verdict, and reasoning) always appears in Spanish, regardless of this interface language. That's how the model was prompted.",
      glossaryHeading: 'Glossary',
    },
  },
}
