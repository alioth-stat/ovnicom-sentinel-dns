import type { Lang } from './i18n'

export interface GlossaryEntry {
  term: string
  definition: string
}

// Plain-language definitions for every technical term that shows up
// somewhere on the dashboard (table headers, verdicts, badges). Surfaced
// via VisibilityPanel so a non-technical viewer isn't left guessing.
export const GLOSSARY: Record<Lang, GlossaryEntry[]> = {
  es: [
    {
      term: 'DGA (Algoritmo de Generación de Dominios)',
      definition:
        'Malware que genera automáticamente miles de nombres de dominio con apariencia aleatoria, para que sea difícil bloquear su servidor de control. Se reconoce por nombres largos, sin sentido, con letras y números mezclados al azar.',
    },
    {
      term: 'Typosquatting',
      definition:
        'Un dominio que imita a una marca real cambiando una letra, por ejemplo "bancogenerall.com" en lugar de "bancogeneral.com", para engañar a quien lo escribe o hace clic.',
    },
    {
      term: 'Tunneling DNS',
      definition:
        'Esconder datos dentro de consultas DNS normales para sacar información de la red sin ser detectado. Se ve como subdominios inusualmente largos y aleatorios.',
    },
    {
      term: 'Beaconing',
      definition:
        'Un equipo infectado "reportándose" a un servidor de comando y control a intervalos regulares y predecibles, como un latido. La señal de detección es precisamente esa regularidad.',
    },
    {
      term: 'C2 (Comando y Control)',
      definition: 'El servidor que un atacante usa para controlar remotamente equipos infectados.',
    },
    {
      term: 'NXDOMAIN',
      definition:
        'La respuesta que da un servidor DNS cuando el dominio consultado no existe. Una tasa alta puede indicar malware probando dominios generados, o errores de configuración.',
    },
    {
      term: 'QPS',
      definition: 'Consultas por segundo ("queries per second"): cuánto tráfico DNS está manejando una zona en un momento dado.',
    },
    {
      term: 'Latencia',
      definition: 'Cuánto tiempo tarda el servidor DNS en responder una consulta. Más alta significa una experiencia más lenta para el usuario final.',
    },
    {
      term: 'Zona / POP',
      definition:
        'Un sitio o punto de presencia de la red (aquí, 5 zonas ficticias). Agrupa el tráfico por ubicación para poder comparar la salud de cada una.',
    },
    {
      term: 'Veredicto',
      definition: 'La clasificación final que da el modelo para un dominio sospechoso: benigno, dga, typosquat, tunneling o beaconing.',
    },
    {
      term: 'Confianza',
      definition:
        'Qué tan seguro está el modelo de su propio veredicto, de 0 a 100%. No mide qué tan peligroso es el dominio, sino cuánta certeza tiene el modelo en su respuesta.',
    },
    {
      term: 'QoE (Calidad de Experiencia)',
      definition:
        'Un puntaje de 0 a 1 por zona que combina latencia (50%), tasa de NXDOMAIN (30%) y saturación de tráfico (20%) en un solo número fácil de leer para un operador de red.',
    },
    {
      term: 'Saturación',
      definition: 'Qué tan cerca está una zona de superar la cantidad de tráfico DNS que puede manejar cómodamente.',
    },
    {
      term: 'Heurístico',
      definition:
        'Una regla simple y rápida (no un modelo de IA) que detecta patrones sospechosos, por ejemplo "¿tiene este nombre más letras al azar de lo normal?". Filtra candidatos antes de gastar una llamada al modelo, que es más lenta.',
    },
    {
      term: 'SIEM / Wazuh',
      definition:
        'Un sistema que centraliza y correlaciona alertas de seguridad de toda una organización. Wazuh es el SIEM real que usa Ovnicom; este prototipo le entrega alertas en un formato que puede leer directamente.',
    },
    {
      term: 'QVAC / on-device',
      definition:
        'El SDK que permite correr modelos de IA completos en esta misma máquina, sin enviar ningún dato a un servidor externo. Es el requisito no negociable de este proyecto: ninguna consulta DNS sale del edificio.',
    },
  ],
  en: [
    {
      term: 'DGA (Domain Generation Algorithm)',
      definition:
        "Malware that automatically generates thousands of random-looking domain names, making its control server hard to block. Recognizable by long, meaningless names with letters and digits mixed at random.",
    },
    {
      term: 'Typosquatting',
      definition:
        'A domain that mimics a real brand by changing one letter, for example "bancogenerall.com" instead of "bancogeneral.com", to trick whoever types or clicks it.',
    },
    {
      term: 'DNS tunneling',
      definition:
        'Hiding data inside normal DNS queries to smuggle information out of the network undetected. Shows up as unusually long, random-looking subdomains.',
    },
    {
      term: 'Beaconing',
      definition:
        'An infected device "checking in" with a command-and-control server at regular, predictable intervals, like a heartbeat. The detection signal is precisely that regularity.',
    },
    {
      term: 'C2 (Command and Control)',
      definition: 'The server an attacker uses to remotely control infected devices.',
    },
    {
      term: 'NXDOMAIN',
      definition:
        'The response a DNS server gives when the queried domain does not exist. A high rate can point to malware probing generated domains, or a misconfiguration.',
    },
    {
      term: 'QPS',
      definition: 'Queries per second: how much DNS traffic a zone is handling at a given moment.',
    },
    {
      term: 'Latency',
      definition: 'How long the DNS server takes to answer a query. Higher means a slower experience for the end user.',
    },
    {
      term: 'Zone / POP',
      definition: 'A site or point of presence in the network (here, 5 fictional zones). Groups traffic by location so the health of each one can be compared.',
    },
    {
      term: 'Verdict',
      definition: "The model's final classification for a suspicious domain: benign, dga, typosquat, tunneling, or beaconing.",
    },
    {
      term: 'Confidence',
      definition:
        'How sure the model is of its own verdict, from 0 to 100%. It does not measure how dangerous the domain is, only how certain the model is in its answer.',
    },
    {
      term: 'QoE (Quality of Experience)',
      definition:
        'A score from 0 to 1 per zone combining latency (50%), NXDOMAIN rate (30%), and traffic saturation (20%) into one number a network operator can read at a glance.',
    },
    {
      term: 'Saturation',
      definition: 'How close a zone is to exceeding the amount of DNS traffic it can comfortably handle.',
    },
    {
      term: 'Heuristic',
      definition:
        'A simple, fast rule, not an AI model, that flags a suspicious pattern, for example "does this name have more random letters than usual?". Filters candidates before spending a call on the slower model.',
    },
    {
      term: 'SIEM / Wazuh',
      definition:
        "A system that centralizes and correlates security alerts across an organization. Wazuh is the real SIEM Ovnicom uses; this prototype hands it alerts in a format it can read directly.",
    },
    {
      term: 'QVAC / on-device',
      definition:
        'The SDK that runs full AI models on this same machine, without sending any data to an external server. The non-negotiable requirement of this project: no DNS query leaves the building.',
    },
  ],
}
