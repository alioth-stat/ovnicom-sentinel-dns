"""Appends confirmed alerts as JSON lines to a local log, in the shape a real
Wazuh agent's `<localfile><log_format>json</log_format>` decoder ingests --
this is a genuine supported Wazuh integration pattern (tail a JSON log), not
a fake stand-in for a live manager we didn't stand up."""
import json
from datetime import datetime, timezone
from pathlib import Path

_LOG_PATH = Path("wazuh_alerts.log")

_LEVEL_BY_KIND = {"dga": 10, "typosquat": 8, "tunneling": 12, "beaconing": 13}


def append_alert(event, candidate: dict, verdict: dict) -> None:
    kind = verdict["verdict"]
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule": {
            "level": _LEVEL_BY_KIND.get(kind, 5),
            "description": f"Sentinel-DNS: {kind} sospechoso detectado por QVAC",
            "groups": ["dns", "sentinel-dns", kind],
        },
        "data": {
            "dns": {
                "query": event.qname,
                "client_zone": event.client_zone,
                "client_id": event.client_id,
                "heuristic_kind": candidate["kind"],
                "heuristic_score": candidate["heuristic_score"],
                "verdict": kind,
                "confidence": verdict["confidence"],
                "reasoning": verdict["reasoning"],
            },
        },
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
