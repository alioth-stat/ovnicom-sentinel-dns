import qoe


def test_healthy_zone_scores_high():
    score, status = qoe.compute_qoe(avg_latency_ms=10, nxdomain_rate=0.01, qps=5)
    assert status == "healthy"
    assert score >= 0.85


def test_degraded_zone_scores_low():
    score, status = qoe.compute_qoe(avg_latency_ms=200, nxdomain_rate=0.2, qps=200)
    assert status == "degraded"
    assert score < 0.6


def test_saturation_alone_can_tip_a_zone_into_watch():
    healthy_score, _ = qoe.compute_qoe(avg_latency_ms=10, nxdomain_rate=0.01, qps=5)
    saturated_score, status = qoe.compute_qoe(avg_latency_ms=10, nxdomain_rate=0.01, qps=150)
    assert saturated_score < healthy_score
    assert status in ("watch", "degraded")
