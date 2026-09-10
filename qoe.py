"""Per-zone quality-of-experience score: 0.5 x latency + 0.3 x NXDOMAIN + 0.2 x saturation.
Same weighted-sum-then-bucket shape as Philips' confidence.py."""

_LATENCY_TARGET_MS = 30.0  # at/below this, latency component is a perfect 1.0
_LATENCY_CEILING_MS = 150.0  # at/above this, latency component bottoms out at 0.0
_NXDOMAIN_CEILING = 0.15  # rate at/above this bottoms the NXDOMAIN component out at 0.0
_CAPACITY_QPS = 4.0  # queries/sec a zone is provisioned for; above this, saturation degrades the score
# ponytail: sized to this demo's actual throughput (BATCH_SIZE/TICK_SECONDS
# spread over 5 zones, ~3-4 qps/zone) rather than a real POP's capacity, so
# the saturation term actually responds instead of pinning at 1.0 forever.


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _latency_component(avg_latency_ms: float) -> float:
    if avg_latency_ms <= _LATENCY_TARGET_MS:
        return 1.0
    span = _LATENCY_CEILING_MS - _LATENCY_TARGET_MS
    return _clamp01(1.0 - (avg_latency_ms - _LATENCY_TARGET_MS) / span)


def _nxdomain_component(nxdomain_rate: float) -> float:
    return _clamp01(1.0 - nxdomain_rate / _NXDOMAIN_CEILING)


def _saturation_component(qps: float) -> float:
    return _clamp01(1.0 - max(0.0, qps - _CAPACITY_QPS) / _CAPACITY_QPS)


def compute_qoe(avg_latency_ms: float, nxdomain_rate: float, qps: float) -> tuple[float, str]:
    latency = _latency_component(avg_latency_ms)
    nxdomain = _nxdomain_component(nxdomain_rate)
    saturation = _saturation_component(qps)
    score = round(0.5 * latency + 0.3 * nxdomain + 0.2 * saturation, 2)

    if score >= 0.85:
        status = "healthy"
    elif score >= 0.6:
        status = "watch"
    else:
        status = "degraded"

    return score, status
