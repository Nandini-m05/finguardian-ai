import pytest
from app.agents.market_analysis import compute_technical_indicators


def test_basic_calculation():
    market_data = {
        "current_price": 110.0,
        "previous_close": 100.0,
        "recent_closes": [100.0, 102.0, 101.0, 105.0, 110.0],
    }
    result = compute_technical_indicators(market_data)

    assert result["price_change_pct"] == 10.0
    assert result["five_day_high"] == 110.0
    assert result["five_day_low"] == 100.0
    assert result["five_day_range_pct"] == 10.0
    assert result["volatility"] == pytest.approx(4.04, abs=0.01)
    assert result["momentum"] == "up"


def test_downward_momentum():
    market_data = {
        "current_price": 90.0,
        "previous_close": 100.0,
        "recent_closes": [110.0, 108.0, 105.0, 95.0, 90.0],
    }
    result = compute_technical_indicators(market_data)
    assert result["momentum"] == "down"
    assert result["price_change_pct"] == -10.0


def test_flat_momentum_on_single_price_point():
    market_data = {
        "current_price": 100.0,
        "previous_close": 100.0,
        "recent_closes": [100.0],
    }
    result = compute_technical_indicators(market_data)
    assert result["momentum"] == "flat"
    assert result["volatility"] is None  # needs >= 2 points


def test_nan_values_are_filtered_not_crashed_on():
    """Regression test: an earlier version crashed on gapped market data
    with 'float object has no attribute numerator' inside statistics.stdev.
    Fixed by filtering NaNs and switching to numpy."""
    market_data = {
        "current_price": 100.0,
        "previous_close": 95.0,
        "recent_closes": [100.0, float("nan"), 98.0, 102.0, 99.0],
    }
    result = compute_technical_indicators(market_data)
    assert result["volatility"] is not None
    assert result["five_day_high"] == 102.0


def test_missing_data_returns_none_gracefully():
    result = compute_technical_indicators({})
    assert result["price_change_pct"] is None
    assert result["volatility"] is None
    assert result["momentum"] == "flat"
