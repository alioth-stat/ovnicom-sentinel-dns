"""Background task: generator -> detectors -> QVAC judge -> db + Wazuh sink.

Runs continuously on the FastAPI app's own event loop (started from a
lifespan hook, not a route) -- this is the "additional consumer of the DNS
stream" the brief asks for. The one blocking step (the QVAC call) is
dispatched to a thread via run_in_executor so it never stalls the loop that
also serves /api/alerts and /api/qoe.
"""
import asyncio
from collections import defaultdict, deque

import db
import detectors
import generator
import qoe
import qvac_judge
import wazuh_sink

TICK_SECONDS = 1.5
BATCH_SIZE = 25
_ZONE_WINDOW = 200  # events kept per zone for rolling QoE stats

_zone_events: dict[str, deque] = defaultdict(lambda: deque(maxlen=_ZONE_WINDOW))


def _update_zone_stats(conn, zone: str) -> None:
    events = _zone_events[zone]
    if len(events) < 2:
        return
    latencies = [e.latency_ms for e in events]
    nxdomain_rate = sum(1 for e in events if e.rcode == "NXDOMAIN") / len(events)
    span_s = max(events[-1].ts - events[0].ts, 1.0)
    avg_latency = sum(latencies) / len(latencies)
    qps = len(events) / span_s
    score, status = qoe.compute_qoe(avg_latency, nxdomain_rate, qps)
    db.upsert_qoe(conn, zone, round(avg_latency, 1), round(nxdomain_rate, 3), round(qps, 2), score, status)


async def run_forever(conn) -> None:
    loop = asyncio.get_running_loop()
    while True:
        for event in generator.next_batch(BATCH_SIZE):
            _zone_events[event.client_zone].append(event)

            candidate = detectors.classify_candidate(event)
            if candidate is not None:
                verdict = await loop.run_in_executor(None, qvac_judge.classify, event.qname, candidate)
                if verdict["verdict"] != "benign":
                    db.insert_alert(conn, event, candidate, verdict)
                    wazuh_sink.append_alert(event, candidate, verdict)

        for zone in generator.ZONES:
            _update_zone_stats(conn, zone)

        await asyncio.sleep(TICK_SECONDS)
