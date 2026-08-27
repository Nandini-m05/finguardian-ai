from transformers import pipeline
from app.agents.state import AgentState

# Loaded once at import time, not per-node-call - reused across every
# graph run in this process. This matters once this lives inside FastAPI:
# the ~1-2s load cost is paid once at startup, not on every request.
_finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")


def score_articles(articles: list[dict]) -> list[dict]:
    """Run FinBERT sentiment scoring on a batch of news articles."""
    if not articles:
        return []

    texts = [
        f"{article.get('title', '')}. {article.get('summary', '')}"
        for article in articles
    ]

    results = _finbert(texts, truncation=True)

    return [
        {
            **article,
            "sentiment_label": result["label"],
            "sentiment_confidence": round(result["score"], 3),
        }
        for article, result in zip(articles, results)
    ]


def aggregate_sentiment(scored_articles: list[dict]) -> tuple[float, str]:
    """Combine per-article FinBERT scores into one overall sentiment score (-1 to +1).

    Confidence matters here, not just label - a 0.95-confidence negative
    should pull the average down harder than a 0.55-confidence one.
    """
    if not scored_articles:
        return 0.0, "No news articles available to assess sentiment."

    signed_scores = []
    counts = {"positive": 0, "negative": 0, "neutral": 0}

    for article in scored_articles:
        label = article["sentiment_label"]
        confidence = article["sentiment_confidence"]
        counts[label] += 1
        if label == "positive":
            signed_scores.append(confidence)
        elif label == "negative":
            signed_scores.append(-confidence)
        else:
            signed_scores.append(0.0)

    overall_score = round(sum(signed_scores) / len(signed_scores), 3)
    tone = "positive" if overall_score > 0.15 else "negative" if overall_score < -0.15 else "mixed/neutral"

    summary = (
        f"Overall news sentiment is {tone} ({overall_score:+.2f}) across "
        f"{len(scored_articles)} articles - {counts['positive']} positive, "
        f"{counts['negative']} negative, {counts['neutral']} neutral."
    )

    return overall_score, summary


def news_intelligence_node(state: AgentState) -> dict:
    """LangGraph node: News Intelligence Agent."""
    symbol = state["symbol"]
    articles = state.get("raw_news_data") or []

    if not articles:
        return {
            "sentiment_score": 0.0,
            "sentiment_summary": "No news articles available to assess sentiment.",
            "agent_log": [f"[NewsIntelligence] Skipped - no raw_news_data found for {symbol}"],
        }

    scored_articles = score_articles(articles)
    overall_score, summary = aggregate_sentiment(scored_articles)

    return {
        "sentiment_score": overall_score,
        "sentiment_summary": summary,
        "agent_log": [f"[NewsIntelligence] Scored {len(scored_articles)} articles for {symbol}: {summary}"],
    }