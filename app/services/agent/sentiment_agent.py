from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.models.sentiment import SentimentAggregate, SentimentData
from app.services.agent.base import BaseAgent
from app.services.reddit.analyzer import SentimentAnalyzer
from app.services.reddit.client import RedditClient


class SentimentAnalystAgent(BaseAgent):
    """Analyzes social media sentiment for financial signals."""

    def __init__(
        self,
        reddit_client: Optional[RedditClient] = None,
        analyzer: Optional[SentimentAnalyzer] = None,
    ) -> None:
        super().__init__(
            agent_id="sentiment-agent",
            name="Sentiment Analyst",
        )
        self.reddit = reddit_client or RedditClient()
        self.analyzer = analyzer or SentimentAnalyzer()

    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = input_data.get("query", "")
        ticker = input_data.get("ticker", "")
        subreddits = input_data.get("subreddits", None)
        limit = input_data.get("limit", 100)

        if ticker:
            query = ticker

        raw_posts = await self.reddit.fetch_multiple_subreddits(
            subreddits=subreddits,
            limit=limit,
        )

        analyzed: List[SentimentData] = [
            self.analyzer.analyze_post(p) for p in raw_posts
        ]
        aggregate = self.analyzer.aggregate(analyzed, query=query or ticker)

        signal = self._generate_signal(aggregate)
        analysis_prompt = (
            f"Social sentiment analysis for '{query or ticker}':\n"
            f"Overall score: {aggregate.overall_score}\n"
            f"Confidence: {aggregate.confidence}\n"
            f"Distribution: {aggregate.distribution}\n"
            f"Volume: {aggregate.volume}\n"
            f"Top keywords: {', '.join(aggregate.top_keywords[:10])}\n\n"
            f"Signal: {signal}\n\n"
            f"Provide a concise assessment of market sentiment and "
            f"whether this represents a trading opportunity."
        )

        llm_output = await self._call_llm(
            system_prompt="You are a sentiment analyst for quantitative trading.",
            user_prompt=analysis_prompt,
        )

        self._add_to_memory("user", str(input_data))
        self._add_to_memory("assistant", llm_output)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "query": query or ticker,
            "overall_score": aggregate.overall_score,
            "confidence": aggregate.confidence,
            "distribution": aggregate.distribution,
            "volume": aggregate.volume,
            "top_keywords": aggregate.top_keywords[:20],
            "signal": signal,
            "analysis": llm_output,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_signal(self, agg: SentimentAggregate) -> str:
        if agg.overall_score > 0.3 and agg.confidence > 0.5:
            return "bullish"
        elif agg.overall_score < -0.3 and agg.confidence > 0.5:
            return "bearish"
        elif abs(agg.overall_score) <= 0.3 and agg.volume > 50:
            return "neutral_high_volume"
        return "neutral"
