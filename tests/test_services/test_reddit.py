from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.reddit.analyzer import SentimentAnalyzer


class TestSentimentAnalyzer:
    def setup_method(self):
        self.analyzer = SentimentAnalyzer()

    def test_extract_tickers(self):
        text = "AAPL is looking great! Also buying MSFT and GOOGL calls."
        tickers = self.analyzer.extract_tickers(text)
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert "GOOGL" in tickers

    def test_extract_tickers_no_tickers(self):
        tickers = self.analyzer.extract_tickers("This is a normal sentence without tickers.")
        assert tickers == []

    def test_extract_tickers_excludes_common_words(self):
        tickers = self.analyzer.extract_tickers("I think THE market is going up")
        assert "THE" not in tickers
        assert "I" not in tickers

    def test_compute_sentiment_positive(self):
        score, label, conf = self.analyzer.compute_sentiment("Bullish on this stock! Moon rocket!")
        assert score > 0
        assert label == "positive"

    def test_compute_sentiment_negative(self):
        score, label, conf = self.analyzer.compute_sentiment("Bearish crash dump sell everything!")
        assert score < 0
        assert label == "negative"

    def test_compute_sentiment_neutral(self):
        score, label, conf = self.analyzer.compute_sentiment("The market is trading sideways today")
        assert label == "neutral"

    def test_compute_sentiment_empty(self):
        score, label, conf = self.analyzer.compute_sentiment("")
        assert score == 0.0
        assert label == "neutral"

    def test_extract_keywords(self):
        keywords = self.analyzer.extract_keywords("bullish on technology sector growth")
        assert "bullish" in keywords
        assert "technology" in keywords

    def test_analyze_post(self):
        post = {
            "id": "test123",
            "title": "AAPL earnings beat",
            "text": "Great earnings beat! Bullish on apple stock",
            "score": 100,
            "num_comments": 20,
            "subreddit": "wallstreetbets",
            "created_utc": datetime.now(timezone.utc),
        }
        result = self.analyzer.analyze_post(post)
        assert result.post_id == "test123"
        assert "AAPL" in result.tickers_mentioned
        assert result.sentiment_score > -2.0

    def test_aggregate_empty(self):
        agg = self.analyzer.aggregate([], query="test")
        assert agg.volume == 0
        assert agg.overall_score == 0.0

    def test_aggregate_multiple(self):
        from app.models.sentiment import SentimentData
        posts = [
            SentimentData(
                source="reddit", platform="reddit", post_id="1", subreddit="test",
                title="Bullish", text="Great!", score=10, num_comments=5,
                created_utc=datetime.now(timezone.utc),
                sentiment_score=0.8, sentiment_label="positive", confidence=0.9,
                tickers_mentioned=["AAPL"], keywords=["bullish"],
            ),
            SentimentData(
                source="reddit", platform="reddit", post_id="2", subreddit="test",
                title="Bearish", text="Terrible!", score=-5, num_comments=2,
                created_utc=datetime.now(timezone.utc),
                sentiment_score=-0.6, sentiment_label="negative", confidence=0.7,
                tickers_mentioned=["MSFT"], keywords=["bearish"],
            ),
        ]
        agg = self.analyzer.aggregate(posts, query="tech")
        assert agg.volume == 2
        assert agg.overall_score == 0.1
