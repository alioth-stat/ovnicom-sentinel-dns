"""QVAC structured classification of a heuristic-flagged domain. Same shape as
Philips' extract.py: JSON-schema-constrained decoding + a short retry loop."""
import json

import qvac_client

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["benign", "dga", "typosquat", "tunneling", "beaconing"]},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["verdict", "confidence", "reasoning"],
}

SYSTEM_PROMPT = """Eres un analista de seguridad DNS. Se te da un dominio consultado y señales \
heurísticas ya calculadas sobre él (posible generación algorítmica de dominios/DGA, \
typosquatting de una marca conocida, tunneling de datos vía subdominios, o beaconing hacia \
un servidor de comando y control). Tu trabajo es dar el veredicto final: confirma la \
sospecha, la descarta, o la reclasifica.

Responde ÚNICAMENTE con el objeto JSON: verdict (uno de benign, dga, typosquat, tunneling, \
beaconing), confidence (0 a 1), reasoning (una frase breve en español explicando por qué, \
para un operador de red sin contexto de ML).
"""

_FALLBACK = {"verdict": "benign", "confidence": 0.0, "reasoning": "No se pudo obtener un veredicto del modelo."}


def _format_candidate(qname: str, candidate: dict) -> str:
    return (
        f"Dominio: {qname}\n"
        f"Sospecha heurística principal: {candidate['kind']} (score {candidate['heuristic_score']})\n"
        f"Señales: {candidate['signals']}\n"
        + (f"Marca posiblemente imitada: {candidate['typosquat_target']}\n" if candidate.get("typosquat_target") else "")
    )


def classify(qname: str, candidate: dict) -> dict:
    text = _format_candidate(qname, candidate)
    # ponytail: same cold-load flakiness as extract.py -- retry once on
    # malformed JSON before falling back to a safe "benign, low confidence".
    for attempt in range(2):
        raw_text = qvac_client.extract_sync(text, JSON_SCHEMA, system_prompt=SYSTEM_PROMPT)
        try:
            raw = json.loads(raw_text)
            if raw and raw.get("verdict") and raw.get("reasoning"):
                raw["confidence"] = float(raw.get("confidence") or 0.0)
                return raw
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        print(f"qvac_judge: attempt {attempt + 1} did not return a usable verdict, got: {raw_text!r}")
    return dict(_FALLBACK)
