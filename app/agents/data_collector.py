import httpx
import yfinance as yf
from datetime import datetime, timezone
from app.config import settings
from app.agents.state import AgentState
from app.events.redis_client import publish_event

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
DATA_COLLECTOR_STREAM = "data_collector_events"


def fetch_market_data(symbol: str) -> dict:
    """Pull a market snapshot for a given symbol using yfinance."""
    ticker = yf.Ticker(symbol)
    info = ticker.info
    history = ticker.history(period="5d", interval="1d")

    return {
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "volume": info.get("volume"),
        "market_cap": info.get("marketCap"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "recent_closes": history["Close"].tolist() if not history.empty else [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_news_data(symbol: str, limit: int = 10) -> list[dict]:
    """Pull recent news headlines for a symbol from Alpha Vantage News & Sentiment."""
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "apikey": settings.alpha_vantage_api_key,
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    if "feed" not in data:
        print(f"[DataCollector] News fetch issue: {data}")
        return []

    articles = data["feed"][:limit]  # enforce the cap ourselves - AV doesn't reliably honor it

    return [
        {
            "title": article.get("title"),
            "url": article.get("url"),
            "source": article.get("source"),
            "summary": article.get("summary"),
            "time_published": article.get("time_published"),
        }
        for article in articles
    ]


async def data_collector_node(state: AgentState) -> dict:
    """LangGraph node: Data Collector Agent."""
    symbol = state["symbol"]
    request_id = state["request_id"]

    market_data = fetch_market_data(symbol)
    news_data = await fetch_news_data(symbol)

    await publish_event(DATA_COLLECTOR_STREAM, {
        "request_id": request_id,
        "symbol": symbol,
        "status": "completed",
        "articles_count": len(news_data),
        "published_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "raw_market_data": market_data,
        "raw_news_data": news_data,
        "agent_log": [
            f"[DataCollector] Fetched market data for {symbol} at {market_data['fetched_at']}",
            f"[DataCollector] Fetched {len(news_data)} news articles for {symbol}",
            f"[DataCollector] Published completion event to Redis Stream '{DATA_COLLECTOR_STREAM}'",
        ],
    }