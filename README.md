# Sentinel-DNS — Reto Ovnicom

Prototipo para el reto **"Sentinel-DNS: inteligencia local sobre telemetría DNS"** de
Ovnicom, en el **Decentralized AI Hackathon** (ISD Summit, Panamá). Un agente que se conecta
como **consumidor adicional** de un stream de telemetría DNS (sin tocar el pipeline de
producción) y produce, con toda la inferencia corriendo **on-device vía QVAC**:

1. **Seguridad**: clasificación en tiempo real de dominios sospechosos (DGA, typosquatting,
   tunneling DNS, beaconing hacia C2) → alerta a Wazuh.
2. **Experiencia de cliente**: un score de calidad de experiencia (QoE) por zona/POP, a
   partir de latencia, tasa de NXDOMAIN y saturación.

## Declaración de reuso (requerida por las reglas del hackathon)

Este proyecto reutiliza base de la **submission previa del mismo equipo en este mismo
hackathon**, [`Challenges/Phillips/`](../Phillips) ("Inteligencia de Base Instalada de
Clientes", reto Philips). Específicamente:

- `qvac_client.py` — copiado tal cual, sin cambios. Wrapper genérico sobre el SDK de QVAC
  (conexión única, loop de asyncio + lock compartidos para todo el proceso, carga perezosa
  de modelos).
- La forma de `api.py` (FastAPI delgado, rutas `def` planas, sin lógica propia, CORS abierto
  a `localhost:5173`) y de `db.py` (sqlite plano, sin ORM).
- La forma de `confidence.py` → se convirtió en `qoe.py` (score ponderado → estado por
  balde). La forma de `extract.py` → se convirtió en `qvac_judge.py` (salida JSON forzada
  por schema + reintento corto ante salida malformada).
- Frontend: `Background.tsx`, `GlassPanel.tsx` y sus dependencias (`lib/utils.ts`,
  `hooks/use-prefers-reduced-motion.ts`, `index.css`, `main.tsx`, `vite.config.ts`,
  configuración de TypeScript, `package.json`), además de los primitivos genéricos de
  shadcn `ui/badge.tsx` y `ui/table.tsx`. **No** se reutilizó `StepShell.tsx` (el asistente
  de pasos deslizantes de Philips) — esta app es un dashboard en vivo, no un flujo de
  varios pasos.

Más detalle sobre el origen de esta base en
[`../Phillips/context/README.md`](../Phillips/context/README.md). El repositorio es
independiente (historia de git propia), por decisión explícita del equipo, aunque comparte
código base con la submission de Philips.

## Cómo funciona

1. **Captura**: el agente se conecta como consumidor adicional del stream de telemetría DNS.
   Si `data/dns_logs/` tiene el dataset real provisto por Ovnicom, reproduce esas consultas;
   si no, sintetiza tráfico benigno. En ambos casos nunca toca el pipeline de producción, que
   no existe en este prototipo.
2. **Heurísticos**: reglas baratas (entropía del nombre de dominio, distancia difusa a
   marcas conocidas, intervalos de repetición fijos) deciden qué dominios ameritan gastar
   una llamada al modelo.
3. **Veredicto QVAC**: solo los candidatos ya filtrados llegan a un modelo pequeño
   (Qwen3-1.7B-Instruct) cargado vía QVAC, que confirma, descarta o reclasifica la sospecha
   con un nivel de confianza y una explicación en español.
4. **Alerta**: todo veredicto distinto de "benigno" se guarda en sqlite y se escribe como
   línea JSON en `wazuh_alerts.log`, en el formato que un agente Wazuh real consume
   directamente.
5. **QoE**: en paralelo, cada zona acumula una ventana móvil de eventos y calcula un score
   (latencia + tasa de NXDOMAIN + saturación) mediante una fórmula fija, sin usar ningún
   modelo.
6. **Panel**: un dashboard React muestra ambas salidas en vivo, con un panel de
   Transparencia y glosario, y un selector de idioma para la interfaz.

## Requisito técnico cumplido

Toda la clasificación (`qvac_judge.classify`) corre localmente a través de `tetherto.qvac_sdk`
(`qvac_client.py`), sin ninguna llamada a un endpoint de inferencia en la nube. El código no
importa ningún cliente HTTP (`requests`/`urllib`/`httpx`) ni abre sockets salientes. La única
cadena de red en todo el backend es la configuración de CORS hacia `http://localhost:5173`.
El SDK de QVAC habla con el worker local vía IPC, nunca hacia afuera.

## Qué es real y qué es simulado

Ovnicom opera BIND9+dnstap → Vector → Kafka → ClickHouse → Grafana, con Wazuh como SIEM.
Nada de esa infraestructura se instaló para este prototipo; en su lugar:

| Componente real de Ovnicom | Cómo se representa aquí |
|---|---|
| BIND9 + dnstap (captura de queries) | `bind_log.py` parsea líneas reales de `named.log` (formato `queries: info: client ...`) cuando hay un dataset en `data/dns_logs/`; si no, `generator.py` sintetiza tráfico benigno. En ambos casos, tráfico adversarial (DGA/typosquat/tunneling/beaconing) siempre se sintetiza y se mezcla encima, tal como pide el reto ("los datos de entrada son sintéticos... dominios DGA de listas públicas, tráfico normal simulado"). |
| Vector / Kafka (bus de eventos) | `pipeline.run_forever()`, una tarea de fondo en el mismo proceso FastAPI que lee del generador en batches, actuando como el "consumidor adicional" que el reto exige. |
| ClickHouse (almacenamiento) | `db.py`, sqlite local (`alerts`, `qoe_snapshots`). |
| Grafana (visualización) | El dashboard React (`frontend/`), con polling cada 3s sobre `/api/alerts` y `/api/qoe`. |
| Wazuh (SIEM) | No se levantó un manager de Wazuh real. `wazuh_sink.py` escribe cada alerta confirmada como una línea JSON en `wazuh_alerts.log`, en el formato que un agente Wazuh real con `<localfile><log_format>json</log_format>` consume directamente: un patrón de integración soportado de verdad, no un stand-in inventado. |

El dataset real (`data/dns_logs/`, provisto por Ovnicom vía un enlace privado de SharePoint
referenciado en el brief del reto) **no está incluido en este repositorio**: son 721MB de
logs de BIND9 reales/realistas, sin redistribuir libremente, y están en `.gitignore`. Sin
ese directorio poblado, el proyecto corre en modo 100% sintético, lo cual está
explícitamente permitido por las reglas del reto.

## Interfaz

Un dashboard React de una sola pantalla (Vite + TypeScript + Tailwind + shadcn/ui) que
consume el backend FastAPI por polling cada 3 segundos. Dos paneles con efecto de vidrio
(`GlassSurface`, componente de React Bits) muestran las alertas de seguridad y la
experiencia de red por zona, sobre un fondo animado de olas degradadas (`GradientWaves`,
también de React Bits, renderizado en WebGL vía `ogl`). Toda la interfaz alterna entre
español e inglés con un botón ES/EN; el contenido que genera el modelo (dominio, veredicto,
motivo) siempre queda en español, ya que así fue instruido.

![Alertas de seguridad clasificadas en vivo](docs/screenshots/dashboard-alerts.jpg)

Cada alerta muestra hora, zona, dominio, veredicto con nivel de confianza, y el motivo que
dio QVAC en español.

![Experiencia de red por zona](docs/screenshots/dashboard-qoe.jpg)

El score de QoE por zona, con estados healthy / watch / degraded a simple vista.

![Panel de Transparencia y glosario](docs/screenshots/transparency-panel.jpg)

Un botón abre un panel lateral de **Transparencia y glosario** que explica, en lenguaje
simple, cómo funciona el sistema paso a paso y qué significa cada término técnico en
pantalla, pensado directamente para el criterio del jurado de que el score sea
"interpretable por un operador de red, no solo por quien lo programó".

## Instalación

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm install
```

La primera vez, si el worker de QVAC no se encuentra automáticamente:

```bash
.venv/bin/python -m tetherto.qvac_sdk install-worker
```

## Ejecutar

```bash
./run.sh
```

Levanta backend (`:8000`) y frontend (`:5173`) juntos, Ctrl+C detiene ambos. Abrir
`http://localhost:5173` (el dev server de Vite redirige `/api/*` al backend).

**Manual**, si prefieres controlarlo por separado:

```bash
.venv/bin/uvicorn api:app --port 8000 --reload   # terminal 1
cd frontend && npm run dev                       # terminal 2
```

La primera clasificación tarda más (carga en frío del modelo, ~50s en hardware modesto): la
tabla de alertas se ve vacía hasta entonces, esto es esperado.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Prueban la lógica pura de los heurísticos (DGA/typosquat/tunneling/beaconing), el
scheduler de beaconing, y los tres estados del score de QoE. No requieren cargar ningún
modelo, corren offline y en milisegundos.

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `qvac_client.py` | Conexión y carga de modelos vía QVAC SDK (reusado de Philips) |
| `bind_log.py` | Parser de líneas `named.log` de BIND9 + lector cíclico multi-archivo |
| `generator.py` | Stream de eventos: captura real (si existe) + ataques sintéticos mezclados |
| `detectors.py` | Heurísticos baratos (entropía, distancia difusa a marcas, intervalos fijos) que filtran candidatos antes de gastar una llamada a QVAC |
| `qvac_judge.py` | Veredicto estructurado de QVAC sobre los candidatos ya filtrados |
| `qoe.py` | Score de QoE por zona: 0.5×latencia + 0.3×NXDOMAIN + 0.2×saturación → estado |
| `db.py` | Almacenamiento sqlite (alertas + snapshots de QoE) |
| `wazuh_sink.py` | Alertas confirmadas como líneas JSON, formato ingerible por Wazuh |
| `pipeline.py` | Tarea de fondo: generador → detectores → QVAC → db + Wazuh |
| `api.py` | Backend FastAPI — 2 rutas GET, arranca el pipeline en el lifespan hook |
| `frontend/` | Dashboard React (Vite + TypeScript + Tailwind + shadcn/ui) |

## Limitaciones conocidas

- El modelo local usado para el veredicto final es pequeño (Qwen3-1.7B-Instruct); en
  pruebas en vivo, ocasionalmente reclasifica un candidato heurísticamente típico de
  `typosquat` como `dga` (ambos comparten señales de entropía/estructura a nivel de
  heurístico). El veredicto sigue siendo válido y schema-correcto. Es una imprecisión de
  subcategoría del modelo pequeño, no un fallo de detección: el dominio sospechoso igual
  genera una alerta.
- El heurístico de DGA (`detectors.score_dga`) puntúa por entropía del nombre, lo que
  también puede disparar en subdominios reales de infraestructura con nombres largos y
  técnicos (confirmado en pruebas con el dataset real: por ejemplo
  `api19-normal-c-alisg.tiktokv.com` y `cloud-meraki-asn.amp.cisco.com` recibieron un
  veredicto `dga` de baja confianza). QVAC no siempre corrige este falso positivo del
  heurístico. Es una limitación conocida de los detectores basados en entropía, no
  específica de esta implementación, y un ajuste de umbral no la elimina sin también
  perder detecciones reales.
- Con el tráfico sintético a este ritmo de demo, el componente de saturación del score de
  QoE rara vez domina el resultado frente a latencia/NXDOMAIN: está calibrado para
  responder si el tráfico de una zona supera su capacidad configurada, pero no está
  garantizado que eso ocurra dentro de una demo corta.

## Guión de demo (para el video)

1. Mostrar el dashboard justo después de `./run.sh`, con la tabla de alertas vacía
   (~50s de carga en frío del modelo) — deja claro que corre sobre un stream en vivo, no un
   archivo estático.
2. Desconectar la red de la máquina en cámara antes de que aparezca la primera alerta, como
   prueba visible de que ninguna consulta sale del edificio.
3. Esperar a que aparezca al menos una alerta de cada tipo (dga, typosquat, tunneling,
   beaconing) con su motivo en español.
4. Mostrar la tabla de QoE con las 5 zonas, señalando la zona en estado degraded.
5. Abrir el panel de Transparencia y glosario: el "Cómo funciona" paso a paso y una
   definición del glosario.
6. `tail -f wazuh_alerts.log` en una terminal, mostrando una línea JSON real.
7. Mencionar explícitamente la declaración de reuso de la base de Philips.

## Fuera de alcance (deliberado)

- Kafka/ClickHouse/Grafana/Wazuh manager reales — sustituidos por sqlite, polling HTTP y un
  log JSON, respectivamente (ver tabla arriba). Levantarlos no cambia la arquitectura del
  agente, que ya está diseñado para leer de un bus de eventos sin modificarlo.
- Motor de reglas configurable/aprendido para los heurísticos — cinco zonas fijas y umbrales
  fijos son suficientes para una demo de hackathon.
