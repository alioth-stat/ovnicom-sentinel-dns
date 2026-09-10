"""Cheap rule-based heuristics that flag DNS-event candidates worth a QVAC opinion.

Runs on every event inline (no model, no I/O) -- the point is to filter a
firehose down to the handful of candidates actually worth an LLM call.
"""
import math
import re
from collections import defaultdict

from rapidfuzz import fuzz

from generator import DnsEvent, _BRANDS

_ENTROPY_THRESHOLD = 3.6  # bits/char; real words sit ~2.8-3.3, random labels ~4+
_TYPOSQUAT_SIMILARITY = 82  # rapidfuzz ratio 0-100; close-but-not-exact match to a known brand
_TUNNELING_LABEL_LEN = 32  # dnstap-observed tunneling payloads use long subdomain labels
_BEACON_WINDOW_S = 3600
_BEACON_MIN_HITS = 4
_BEACON_INTERVAL_TOLERANCE = 0.15  # +/- 15% jitter still counts as "fixed interval"

# ponytail: per-process in-memory history, capped by simple eviction -- a real
# deployment would key this off the Kafka consumer group's own windowing
# instead of reinventing one, but a hackathon single-process demo doesn't have that.
_query_history: dict[tuple[str, str], list[float]] = defaultdict(list)
_MAX_TRACKED_PAIRS = 5000


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = defaultdict(int)
    for ch in s:
        freq[ch] += 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def _apex_label(qname: str) -> str:
    return qname.split(".")[0]


def score_dga(qname: str) -> float:
    label = _apex_label(qname)
    if len(label) < 8:
        return 0.0
    entropy = _shannon_entropy(label)
    digit_ratio = sum(ch.isdigit() for ch in label) / len(label)
    vowel_ratio = sum(ch in "aeiou" for ch in label) / len(label)
    score = 0.0
    if entropy >= _ENTROPY_THRESHOLD:
        score += 0.6
    if vowel_ratio < 0.2:  # real words have vowels; random strings often don't
        score += 0.25
    if digit_ratio > 0.3:
        score += 0.15
    return min(score, 1.0)


def score_typosquat(qname: str) -> tuple[float, str | None]:
    best_score, best_brand = 0.0, None
    for brand in _BRANDS:
        if qname == brand:
            continue  # exact match is the real brand, not a squat
        similarity = fuzz.ratio(qname, brand)
        if similarity > best_score:
            best_score, best_brand = similarity, brand
    if best_score >= _TYPOSQUAT_SIMILARITY:
        return best_score / 100, best_brand
    return 0.0, None


def score_tunneling(qname: str) -> float:
    label = _apex_label(qname)
    if len(label) < _TUNNELING_LABEL_LEN:
        return 0.0
    entropy = _shannon_entropy(label)
    has_hex_charset = bool(re.fullmatch(r"[0-9a-f]+", label))
    score = 0.5
    if entropy >= _ENTROPY_THRESHOLD:
        score += 0.3
    if has_hex_charset:
        score += 0.2
    return min(score, 1.0)


def score_beaconing(event: DnsEvent) -> float:
    key = (event.client_id, event.qname)
    history = _query_history[key]
    history.append(event.ts)
    history[:] = [t for t in history if event.ts - t <= _BEACON_WINDOW_S]

    if len(_query_history) > _MAX_TRACKED_PAIRS:
        _query_history.clear()  # ponytail: drop everything rather than LRU-evict; demo-scale only

    if len(history) < _BEACON_MIN_HITS:
        return 0.0

    intervals = [b - a for a, b in zip(history, history[1:])]
    mean_interval = sum(intervals) / len(intervals)
    if mean_interval <= 0:
        return 0.0
    deviation = max(abs(i - mean_interval) / mean_interval for i in intervals)
    return 1.0 if deviation <= _BEACON_INTERVAL_TOLERANCE else 0.0


_CANDIDATE_THRESHOLD = 0.5


def classify_candidate(event: DnsEvent) -> dict | None:
    """Return heuristic signals if event is worth escalating to QVAC, else None."""
    dga = score_dga(event.qname)
    typo_score, typo_brand = score_typosquat(event.qname)
    tunneling = score_tunneling(event.qname)
    beaconing = score_beaconing(event)

    signals = {"dga": dga, "typosquat": typo_score, "tunneling": tunneling, "beaconing": beaconing}
    top_kind = max(signals, key=signals.get)
    top_score = signals[top_kind]
    if top_score < _CANDIDATE_THRESHOLD:
        return None

    return {
        "kind": top_kind,
        "heuristic_score": round(top_score, 2),
        "typosquat_target": typo_brand if top_kind == "typosquat" else None,
        "signals": {k: round(v, 2) for k, v in signals.items()},
    }
