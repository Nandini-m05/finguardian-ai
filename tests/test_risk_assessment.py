import pytest
from app.agents.risk_assessment import compute_risk_score


def test_calm_case_low_score_no_factors():
    indicators = {"volatility": 0.5, "price_change_pct": 0.2}
    score, factors = compute_risk_score(indicators, sentiment_score=0.3)

    assert score < 20
    assert factors == ["No significant risk signals detected"]


def test_weighted_scoring_matches_manual_calculation():
    # volatility_points = min(2.0*10, 40) = 20
    # sentiment_points  = min(0.5*30, 30) = 15 (negative sentiment only)
    # momentum_points   = min(5.0*5, 20)  = 20 (capped)
    indicators = {"volatility": 2.0, "price_change_pct": 5.0}
    score, factors = compute_risk_score(indicators, sentiment_score=-0.5)

    assert score == pytest.approx(55.0)
    assert len(factors) == 3


def test_positive_sentiment_never_adds_risk():
    indicators = {"volatility": 1.0, "price_change_pct": 0.0}
    score, _ = compute_risk_score(indicators, sentiment_score=0.9)
    assert score == pytest.approx(10.0)  # only volatility contributes


def test_score_never_exceeds_the_combined_component_caps():
    # Individual caps are 40 + 30 + 20 = 90 - the score can never reach
    # 100 through normal inputs, even at extreme values.
    indicators = {"volatility": 999, "price_change_pct": 999}
    score, _ = compute_risk_score(indicators, sentiment_score=-999)
    assert score == pytest.approx(90.0)
