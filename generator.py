"""DNS telemetry stream -- stands in for BIND9+dnstap/Vector/Kafka.

Yields one DnsEvent at a time, forever. Two traffic sources, blended:
- Benign backbone: if a real BIND9 capture is present under `data/dns_logs/`
  (Ovnicom's provided synthetic-but-realistic dataset -- see README), replay
  its actual qnames/client IPs; otherwise fall back to a small synthetic
  domain list. Either way this is legitimate per the brief ("el equipo genera
  o utiliza un dataset que imite patrones reales").
- Adversarial minority: always synthetic (DGA/typosquat/tunneling/beaconing),
  since a benign capture has none of these by construction.
Per-zone latency and NXDOMAIN rate are always synthetic -- the real capture
has no response/latency data, only the query line.
"""
import hashlib
import os
import random
import string
import time
from dataclasses import dataclass, field
from pathlib import Path

import bind_log

ZONES = ["pty-01", "pty-02", "bog-01", "gua-01", "sal-01"]

# ponytail: fixed baseline per zone instead of a learned/config-driven model
# -- five zones for a hackathon demo don't need calibration infrastructure.
_ZONE_BASELINE = {
    "pty-01": {"latency_ms": 12, "nxdomain_rate": 0.02},
    "pty-02": {"latency_ms": 18, "nxdomain_rate": 0.03},
    "bog-01": {"latency_ms": 35, "nxdomain_rate": 0.04},
    "gua-01": {"latency_ms": 60, "nxdomain_rate": 0.06},
    "sal-01": {"latency_ms": 90, "nxdomain_rate": 0.12},  # simulates a saturated/degraded zone
}

_NORMAL_DOMAINS = [
    "google.com", "microsoft.com", "office365.com", "salesforce.com", "zoom.us",
    "aws.amazon.com", "github.com", "slack.com", "bancogeneral.com", "wikipedia.org",
]

_BRANDS = ["bancogeneral.com", "bancolombia.com", "bancoagricola.com", "banrural.com.gt"]

_TLDS = [".com", ".net", ".info", ".biz", ".top"]

_REAL_LOG_DIR = Path(os.environ.get("SENTINEL_DNS_LOG_DIR", "data/dns_logs"))
_real_stream = bind_log.stream_real_events(_REAL_LOG_DIR) if _REAL_LOG_DIR.is_dir() else None


def _zone_for_ip(ip: str) -> str:
    # stdlib hashlib, not the builtin hash() -- hash() is salted per-process
    # (PYTHONHASHSEED), which would reassign every client to a new zone on
    # every restart instead of giving each client a stable "home" POP.
    digest = hashlib.md5(ip.encode()).digest()
    return ZONES[digest[0] % len(ZONES)]


@dataclass
class DnsEvent:
    ts: float
    client_zone: str
    client_id: str
    qname: str
    qtype: str
    rcode: str
    latency_ms: float
    true_label: str = field(default="benign", repr=False)  # test/demo-accuracy only; pipeline never reads this


def _random_label(length: int, alphabet: str = string.ascii_lowercase + string.digits) -> str:
    return "".join(random.choices(alphabet, k=length))


def _dga_domain() -> str:
    return _random_label(random.randint(10, 18)) + random.choice(_TLDS)


def _typosquat_domain() -> str:
    brand = random.choice(_BRANDS)
    name, tld = brand.rsplit(".", 1)
    # only mutate real label chars -- name can itself contain a "." for a
    # compound-TLD brand like "banrural.com.gt" (name="banrural.com" here),
    # and mutating that embedded dot would produce a malformed domain.
    indices = [k for k, ch in enumerate(name) if ch != "."]
    i = random.choice(indices)
    op = random.choice(["swap", "drop", "dup"])
    if op == "drop" and len(name) > 3:
        mutated = name[:i] + name[i + 1:]
    elif op == "dup":
        mutated = name[:i] + name[i] + name[i:]
    else:
        j = random.choice(indices)
        chars = list(name)
        chars[i], chars[j] = chars[j], chars[i]
        mutated = "".join(chars)
    return f"{mutated}.{tld}"


def _tunneling_domain(client_id: str) -> str:
    # long high-entropy label under one apex, mimicking data smuggled in DNS labels
    return f"{_random_label(48, string.ascii_lowercase + string.digits + 'abcdef')}.exfil-{client_id[-4:]}.net"


def _beaconing_domain(client_id: str) -> str:
    # fixed C2 domain per client, queried at regular intervals by the caller
    return f"c2-{client_id[-4:]}.dynupdate.top"


# ponytail: beaconing is a *scheduled* pattern, not a random one-off like the
# other three attack kinds -- picking a random client+kind per event (like
# next_batch does for dga/typosquat/tunneling) never reproduces the fixed
# check-in interval detectors.score_beaconing looks for. One infected host
# per zone, checking in on a fixed clock, is the minimum that actually
# triggers the detector.
_BEACON_INTERVAL_S = 8.0  # well inside detectors._BEACON_WINDOW_S (3600s)
_BEACON_HOST = {zone: f"{zone}-beacon-host" for zone in ZONES}
_next_beacon_at: dict[str, float] = {zone: 0.0 for zone in ZONES}


def _due_beacon_events() -> list[DnsEvent]:
    now = time.time()
    events = []
    for zone in ZONES:
        if now >= _next_beacon_at[zone]:
            client_id = _BEACON_HOST[zone]
            events.append(_make_event(zone, client_id, _beaconing_domain(client_id), "A", "beaconing"))
            _next_beacon_at[zone] = now + _BEACON_INTERVAL_S
    return events


def _make_event(zone: str, client_id: str, qname: str, qtype: str, true_label: str) -> DnsEvent:
    baseline = _ZONE_BASELINE[zone]
    rcode = "NXDOMAIN" if random.random() < baseline["nxdomain_rate"] else "NOERROR"
    latency = max(1.0, random.gauss(baseline["latency_ms"], baseline["latency_ms"] * 0.25))
    return DnsEvent(
        ts=time.time(), client_zone=zone, client_id=client_id, qname=qname,
        qtype=qtype, rcode=rcode, latency_ms=round(latency, 1), true_label=true_label,
    )


def _synthetic_client_id(zone: str) -> str:
    return f"{zone}-host{random.randint(1, 40):03d}"


def _next_benign(zone: str, client_id: str) -> DnsEvent:
    if _real_stream is not None:
        record = next(_real_stream)
        zone = _zone_for_ip(record["client_ip"])
        return _make_event(zone, record["client_ip"], record["qname"], record["qtype"], "benign")
    return _make_event(zone, client_id, random.choice(_NORMAL_DOMAINS), "A", "benign")


def next_batch(n: int = 20, adversarial_rate: float = 0.08) -> list[DnsEvent]:
    """Return n events plus any due scheduled beacon check-ins. ~adversarial_rate
    of the n are synthetic dga/typosquat/tunneling traffic; beaconing is
    scheduled separately (see _due_beacon_events) since it's a fixed-interval
    pattern, not a random one-off. The rest are the benign backbone (real
    capture if present, else synthetic)."""
    events = _due_beacon_events()
    for _ in range(n):
        zone = random.choice(ZONES)
        client_id = _synthetic_client_id(zone)
        if random.random() < adversarial_rate:
            kind = random.choice(["dga", "typosquat", "tunneling"])
            if kind == "dga":
                events.append(_make_event(zone, client_id, _dga_domain(), "A", "dga"))
            elif kind == "typosquat":
                events.append(_make_event(zone, client_id, _typosquat_domain(), "A", "typosquat"))
            else:
                events.append(_make_event(zone, client_id, _tunneling_domain(client_id), "TXT", "tunneling"))
        else:
            events.append(_next_benign(zone, client_id))
    return events
