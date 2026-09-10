import detectors
from generator import DnsEvent


def test_dga_flags_random_label_not_real_words():
    assert detectors.score_dga("xk7qz9mdpltrvw.com") > detectors.score_dga("googleanalytics.com")
    assert detectors.score_dga("short.com") == 0.0  # below length floor, not scored at all


def test_typosquat_flags_mutation_not_exact_brand():
    score, brand = detectors.score_typosquat("bancogeneral.com")
    assert score == 0.0  # the real brand itself is not a squat

    score, brand = detectors.score_typosquat("bancogenerall.com")  # one duplicated letter
    assert score > 0.0
    assert brand == "bancogeneral.com"

    score, _ = detectors.score_typosquat("wikipedia.org")
    assert score == 0.0  # unrelated domain, no brand nearby


def test_tunneling_flags_long_high_entropy_label():
    assert detectors.score_tunneling("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0.exfil.net") > 0.0
    assert detectors.score_tunneling("www.example.com") == 0.0


def test_beaconing_flags_fixed_interval_repeats():
    client, domain = "test-client-beacon", "c2-test.dynupdate.top"
    scores = []
    for i in range(6):
        event = DnsEvent(
            ts=1_000_000.0 + i * 60, client_zone="pty-01", client_id=client,
            qname=domain, qtype="A", rcode="NOERROR", latency_ms=10.0,
        )
        scores.append(detectors.score_beaconing(event))
    assert scores[-1] == 1.0  # enough regular-interval hits accumulated


def test_classify_candidate_returns_none_for_benign_traffic():
    event = DnsEvent(
        ts=1_000_000.0, client_zone="pty-01", client_id="host-1",
        qname="google.com", qtype="A", rcode="NOERROR", latency_ms=10.0,
    )
    assert detectors.classify_candidate(event) is None


def test_classify_candidate_flags_dga_traffic():
    event = DnsEvent(
        ts=1_000_000.0, client_zone="pty-01", client_id="host-2",
        qname="qxzjklmwprtfybn.top", qtype="A", rcode="NOERROR", latency_ms=10.0,
    )
    candidate = detectors.classify_candidate(event)
    assert candidate is not None
    assert candidate["kind"] == "dga"
