import numpy as np
from app.agents.state import AgentState


def compute_technical_indicators(market_data: dict) -> dict:
    """Compute basic technical indicators from the Data Collector's market snapshot.

    Intentionally lightweight v1 - working with the 5-day close history we
    already have. Deeper indicators (RSI, MACD, Bollinger Bands) need a
    longer price history and will come as a pass 2, later.
    """
    closes = market_data.get("recent_closes", [])
    closes = [c for c in closes if c is not None and c == c]  # drop NaNs (NaN != NaN is always True)

    current_price = market_data.get("current_price")
    previous_close = market_data.get("previous_close")

    price_change_pct = None
    if current_price is not None and previous_close:
        price_change_pct = round((current_price - previous_close) / previous_close * 100, 2)

    five_day_high = round(max(closes), 2) if closes else None
    five_day_low = round(min(closes), 2) if closes else None
    five_day_range_pct = None
    if five_day_high is not None and five_day_low:
        five_day_range_pct = round((five_day_high - five_day_low) / five_day_low * 100, 2)

    volatility = round(float(np.std(closes, ddof=1)), 2) if len(closes) >= 2 else None

    momentum = "flat"
    if len(closes) >= 2:
        if closes[-1] > closes[0]:
            momentum = "up"
        elif closes[-1] < closes[0]:
            momentum = "down"

    return {
        "price_change_pct": price_change_pct,
        "five_day_high": five_day_high,
        "five_day_low": five_day_low,
        "five_day_range_pct": five_day_range_pct,
        "volatility": volatility,
        "momentum": momentum,
    }

def build_market_summary(symbol: str, indicators: dict) -> str:
    change = indicators["price_change_pct"] or 0
    direction = "up" if change >= 0 else "down"
    return (
        f"{symbol} is {direction} {abs(change)}% from the previous close, "
        f"with {indicators['momentum']} momentum over the last 5 trading days "
        f"(range: {indicators['five_day_low']}-{indicators['five_day_high']})."
    )


def market_analysis_node(state: AgentState) -> dict:
    """LangGraph node: Market Analysis Agent."""
    symbol = state["symbol"]
    market_data = state.get("raw_market_data")

    if not market_data:
        return {
            "agent_log": [f"[MarketAnalysis] Skipped - no raw_market_data found for {symbol}"],
        }

    indicators = compute_technical_indicators(market_data)
    summary = build_market_summary(symbol, indicators)

    return {
        "technical_indicators": indicators,
        "market_summary": summary,
        "agent_log": [f"[MarketAnalysis] Computed indicators for {symbol}: {summary}"],
    }