from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.logging_config import get_logger
from app.models.sentiment import SentimentAggregate, SentimentData

logger = get_logger(__name__)

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")
CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})")

HYPE_KEYWORDS: Set[str] = {
    "moon", "rocket", "🚀", "mooning", "lambo", "tendies", "dd", "yolo",
    "diamond", "hands", "💎", "hodl", "hodling", "apes", "ape", "together",
    "strong", "gains", "pump", "squeeze", "short squeeze", "calls", "moon shot",
    "megabullish", "super bullish", "life changing", "generational wealth",
    "to the moon", "fly", "soaring", "blast off", "launch",
}

FEAR_KEYWORDS: Set[str] = {
    "crash", "dumping", "dump", "panicking", "panic", "fear", "fud",
    "paper hands", "sell off", "selloff", "liquidation", "margin call",
    "bagholder", "bag", "rekt", "wiped out", "bloodbath", "capitulation",
    "bearish", "over", "dead", "dying", "collapse", "crisis", "plunge",
    "freefall", "tanking", "tanked", "nosedive", "meltdown", "disaster",
}

BULLISH_KEYWORDS: Set[str] = {
    "bullish", "buy", "buying", "long", "overweight", "outperform",
    "positive", "growth", "profit", "beat", "surge", "rally", "breakout",
    "upside", "strong", "momentum", "accumulate", "value", "undervalued",
    "catalyst", "upgrade", "target", "price target", "guidance up",
}

BEARISH_KEYWORDS: Set[str] = {
    "bearish", "sell", "selling", "short", "underweight", "underperform",
    "negative", "decline", "drop", "fall", "weak", "miss", "downgrade",
    "overvalued", "risk", "volatile", "uncertainty", "guidance down",
    "recession", "inflation", "slowdown", "downturn", "warning",
}

STOP_TICKERS: Set[str] = {
    "A", "I", "THE", "FOR", "AND", "NOT", "ARE", "ALL", "BUT", "ITS",
    "HAS", "HAD", "HOW", "WHY", "WHO", "YOU", "WAS", "WERE", "CAN", "WILL",
    "JUST", "THAT", "THIS", "WITH", "FROM", "YOUR", "HAVE", "BEEN", "BEING",
    "ALSO", "VERY", "MUCH", "MANY", "SOME", "ANY", "EACH", "EVER", "NEVER",
    "NOW", "THEN", "THAN", "WHAT", "WHEN", "WHERE", "WHICH", "WHOSE",
    "ONE", "TWO", "NEW", "OLD", "GET", "USE", "SAY", "SHE", "HE", "HER",
    "HIM", "HIS", "SAID", "GOT", "MAY", "LET", "PUT", "SET", "RUN", "DID",
    "WAY", "LONG", "DAY", "YEAR", "WEEK", "MONTH", "END", "NEXT", "LAST",
    "FIRST", "BACK", "GOOD", "BIG", "EVEN", "STILL", "ALREADY", "ALWAYS",
    "OFTEN", "SURE", "REAL", "SAME", "ANOTHER", "BOTH", "EITHER", "NEITHER",
    "WHETHER", "THOUGH", "ALTHOUGH", "UNLESS", "BECAUSE", "SINCE", "WHILE",
    "DURING", "BEFORE", "AFTER", "ABOVE", "BELOW", "BETWEEN", "THROUGH",
    "WITHIN", "WITHOUT", "PER", "VIA", "UP", "DOWN", "OFF", "OVER", "OUT",
    "IN", "ON", "AT", "BY", "TO", "FOR", "OF", "IS", "BE", "ELSE", "MORE",
    "DO", "DUE", "LESS", "WELL", "HERE", "THERE", "ELSE", "EACH", "FEW",
    "MOST", "SUCH", "ONLY", "OWN", "SAME", "SO", "THAN", "TOO", "VERY",
    "WAS", "WERE", "HAS", "HAD", "HASN'T", "HADN'T", "DOES", "DID", "DONE",
}

STOP_WORDS: Set[str] = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can",
    "was", "were", "has", "had", "its", "how", "why", "who", "what",
    "when", "where", "this", "that", "with", "from", "have", "been",
    "being", "also", "very", "much", "many", "some", "any", "each",
    "every", "ever", "never", "now", "then", "than", "just", "like",
    "more", "most", "only", "over", "such", "than", "they", "their",
    "them", "these", "those", "about", "into", "could", "would",
    "should", "other", "which", "while", "after", "before", "between",
    "through", "during", "because", "under", "above", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "also",
    "well", "even", "still", "already", "always", "often", "sure",
    "really", "quite", "rather", "maybe", "perhaps", "probably",
}


class SentimentAnalyzer:
    """Advanced financial sentiment analyzer with hype/fear detection, ticker extraction, engagement scoring."""

    @staticmethod
    def extract_tickers(text: str) -> List[str]:
        words = text.split()
        tickers = set()

        for word in words:
            clean = word.strip("$¢£¥€.,!?;:'\"()[]{}<>")
            if TICKER_PATTERN.fullmatch(clean) and clean.isupper():
                if clean not in STOP_TICKERS:
                    tickers.add(clean)

        for match in CASHTAG_PATTERN.finditer(text):
            ticker = match.group(1)
            if ticker not in STOP_TICKERS:
                tickers.add(ticker)

        return sorted(tickers)

    @staticmethod
    def compute_sentiment(text: str) -> Tuple[float, str, float]:
        words = text.lower().split()
        bullish = sum(1 for w in words if w in BULLISH_KEYWORDS)
        bearish = sum(1 for w in words if w in BEARISH_KEYWORDS)
        total_signal = bullish + bearish

        if total_signal == 0:
            return 0.0, "neutral", 0.0

        score = (bullish - bearish) / total_signal
        score = max(-1.0, min(1.0, score))
        confidence = min(1.0, total_signal / 15.0)

        if score > 0.25:
            label = "positive"
        elif score < -0.25:
            label = "negative"
        else:
            label = "neutral"

        return round(score, 4), label, round(confidence, 4)

    @staticmethod
    def compute_hype_score(text: str, score: int, num_comments: int, upvote_ratio: float) -> float:
        text_lower = text.lower()
        hype_hits = sum(1 for kw in HYPE_KEYWORDS if kw in text_lower)
        fear_hits = sum(1 for kw in FEAR_KEYWORDS if kw in text_lower)

        raw_hype = hype_hits - fear_hits

        engagement_factor = math.log2(max(2, score + num_comments + 1)) / 10.0
        ratio_factor = upvote_ratio if upvote_ratio > 0 else 0.5
        text_factor = min(1.0, abs(raw_hype) / 5.0)

        hype_score = (
            text_factor * 0.4 +
            engagement_factor * 0.35 +
            ratio_factor * 0.25
        )

        if raw_hype < 0:
            hype_score *= -1

        return round(max(-1.0, min(1.0, hype_score)), 4)

    @staticmethod
    def compute_fear_score(text: str, score: int, num_comments: int, upvote_ratio: float) -> float:
        text_lower = text.lower()
        fear_hits = sum(1 for kw in FEAR_KEYWORDS if kw in text_lower)
        panic_ratio = fear_hits / max(len(text_lower.split()), 1)

        engagement = math.log2(max(2, abs(score) + num_comments + 1)) / 8.0

        sentiment_score, _, _ = SentimentAnalyzer.compute_sentiment(text)

        fear_score = (
            panic_ratio * 0.35 +
            engagement * 0.35 +
            (abs(min(0, sentiment_score)) * 0.30)
        )

        return round(max(0.0, min(1.0, fear_score)), 4)

    @staticmethod
    def compute_engagement_score(score: int, num_comments: int, upvote_ratio: float) -> float:
        score_factor = math.log2(max(2, abs(score))) / 15.0
        comment_factor = math.log2(max(2, num_comments + 1)) / 10.0
        ratio_factor = upvote_ratio

        engagement = (
            score_factor * 0.35 +
            comment_factor * 0.30 +
            ratio_factor * 0.35
        )

        if score < 0:
            engagement *= 0.7

        return round(max(0.0, min(1.0, engagement)), 4)

    @staticmethod
    def compute_volatility(scores: List[float]) -> float:
        if len(scores) < 2:
            return 0.0
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return round(math.sqrt(variance), 4)

    @staticmethod
    def compute_mention_velocity(post_age_hours: float, num_comments: int) -> float:
        if post_age_hours <= 0:
            return 0.0
        return round(num_comments / post_age_hours, 4)

    @staticmethod
    def extract_financial_entities(text: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {
            "tickers": SentimentAnalyzer.extract_tickers(text),
            "crypto": [],
            "indices": [],
            "sectors": [],
        }

        text_lower = text.lower()

        crypto_map = {
            "bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH",
            "solana": "SOL", "sol": "SOL", "cardano": "ADA", "ada": "ADA",
            "ripple": "XRP", "xrp": "XRP", "dogecoin": "DOGE", "doge": "DOGE",
            "polkadot": "DOT", "dot": "DOT", "avalanche": "AVAX", "avax": "AVAX",
            "chainlink": "LINK", "link": "LINK", "polygon": "MATIC", "matic": "MATIC",
        }
        for name, sym in crypto_map.items():
            if name in text_lower:
                entities["crypto"].append(sym)

        index_map = {
            "s&p 500": "SPX", "s&p500": "SPX", "spx": "SPX",
            "nasdaq": "NDX", "ndx": "NDX", "dow jones": "DJI", "dji": "DJI",
            "vix": "VIX", "russell 2000": "RTY", "rty": "RTY",
        }
        for name, sym in index_map.items():
            if name in text_lower:
                entities["indices"].append(sym)

        sector_keywords = {
            "tech": "technology", "semiconductor": "technology", "software": "technology",
            "bank": "finance", "financial": "finance", "insurance": "finance",
            "oil": "energy", "gas": "energy", "energy": "energy",
            "health": "healthcare", "pharma": "healthcare", "biotech": "healthcare",
            "retail": "consumer", "consumer": "consumer", "e-commerce": "consumer",
            "industrial": "industrial", "manufacturing": "industrial",
        }
        for kw, sector in sector_keywords.items():
            if kw in text_lower:
                entities["sectors"].append(sector)

        entities["crypto"] = list(set(entities["crypto"]))
        entities["indices"] = list(set(entities["indices"]))
        entities["sectors"] = list(set(entities["sectors"]))
        return entities

    @staticmethod
    def extract_keywords(text: str, top_n: int = 15) -> List[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        words = [w for w in words if w not in STOP_WORDS and len(w) >= 3]
        counter = Counter(words)
        return [word for word, _ in counter.most_common(top_n)]

    @staticmethod
    def analyze_post(post: Dict[str, Any], current_time: Optional[datetime] = None) -> SentimentData:
        text = f"{post.get('title', '')} {post.get('text', '')}"
        created_utc = post.get("created_utc")
        if isinstance(created_utc, str):
            try:
                created_utc = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
            except ValueError:
                created_utc = datetime.now(timezone.utc)

        now = current_time or datetime.now(timezone.utc)
        post_age_hours = (now - created_utc).total_seconds() / 3600 if created_utc else 0

        score = post.get("score", 0)
        num_comments = post.get("num_comments", 0)
        upvote_ratio = post.get("upvote_ratio", 1.0)

        sentiment_score, sentiment_label, confidence = SentimentAnalyzer.compute_sentiment(text)
        hype_score = SentimentAnalyzer.compute_hype_score(text, score, num_comments, upvote_ratio)
        fear_score = SentimentAnalyzer.compute_fear_score(text, score, num_comments, upvote_ratio)
        engagement = SentimentAnalyzer.compute_engagement_score(score, num_comments, upvote_ratio)
        tickers = SentimentAnalyzer.extract_tickers(text)
        financial_entities = SentimentAnalyzer.extract_financial_entities(text)
        keywords = SentimentAnalyzer.extract_keywords(text)
        mention_velocity = SentimentAnalyzer.compute_mention_velocity(post_age_hours, num_comments)

        signal_type = "neutral"
        if hype_score > 0.4 and sentiment_score > 0:
            signal_type = "hype"
        elif fear_score > 0.4 or sentiment_score < -0.3:
            signal_type = "fear"
        elif engagement > 0.6 and sentiment_score > 0.2:
            signal_type = "strong_bullish"
        elif engagement > 0.6 and sentiment_score < -0.2:
            signal_type = "strong_bearish"

        return SentimentData(
            source="reddit",
            platform="reddit",
            post_id=post.get("id", ""),
            subreddit=post.get("subreddit", ""),
            title=post.get("title", ""),
            text=post.get("text", ""),
            score=score,
            num_comments=num_comments,
            created_utc=created_utc,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            confidence=confidence,
            tickers_mentioned=tickers,
            keywords=keywords,
            raw_data={
                "upvote_ratio": upvote_ratio,
                "hype_score": hype_score,
                "fear_score": fear_score,
                "engagement_score": engagement,
                "signal_type": signal_type,
                "mention_velocity": mention_velocity,
                "post_age_hours": round(post_age_hours, 2),
                "financial_entities": financial_entities,
                "url": post.get("url", ""),
            },
        )

    @staticmethod
    def compute_hype_fear_index(analyzed_posts: List[SentimentData]) -> Dict[str, Any]:
        if not analyzed_posts:
            return {"hype_index": 0.0, "fear_index": 0.0, "greed_fear_ratio": 0.5, "signal": "neutral"}

        hype_scores = []
        fear_scores = []
        engagement_scores = []
        sentiment_scores = []

        for post in analyzed_posts:
            raw = post.raw_data or {}
            hype_scores.append(raw.get("hype_score", 0))
            fear_scores.append(raw.get("fear_score", 0))
            engagement_scores.append(raw.get("engagement_score", 0))
            sentiment_scores.append(post.sentiment_score)

        avg_hype = sum(hype_scores) / len(hype_scores) if hype_scores else 0
        avg_fear = sum(fear_scores) / len(fear_scores) if fear_scores else 0
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0

        weighted_hype = avg_hype * (0.6 + 0.4 * avg_engagement)
        weighted_fear = avg_fear * (0.6 + 0.4 * avg_engagement)

        total = weighted_hype + weighted_fear
        greed_fear_ratio = weighted_hype / total if total > 0 else 0.5

        if greed_fear_ratio > 0.65:
            signal = "greed"
        elif greed_fear_ratio < 0.35:
            signal = "fear"
        else:
            signal = "neutral"

        return {
            "hype_index": round(weighted_hype, 4),
            "fear_index": round(weighted_fear, 4),
            "greed_fear_ratio": round(greed_fear_ratio, 4),
            "signal": signal,
            "engagement_weighted": round(avg_engagement, 4),
            "avg_sentiment": round(sum(sentiment_scores) / len(sentiment_scores), 4) if sentiment_scores else 0,
        }

    @staticmethod
    def aggregate(
        posts: List[SentimentData],
        query: str = "",
        source: str = "reddit",
    ) -> SentimentAggregate:
        if not posts:
            return SentimentAggregate(
                query=query,
                source=source,
                overall_score=0.0,
                confidence=0.0,
                volume=0,
                top_keywords=[],
                top_posts=[],
                period_start=None,
                period_end=None,
            )

        scores = [p.sentiment_score for p in posts if p.sentiment_score is not None]
        confs = [p.confidence for p in posts if p.confidence is not None]

        all_keywords = []
        for p in posts:
            all_keywords.extend(p.keywords)
        keyword_freq = Counter(all_keywords)
        top_keywords = [kw for kw, _ in keyword_freq.most_common(20)]

        distribution = {
            "positive": sum(1 for s in scores if s > 0.25) / len(scores) if scores else 0,
            "negative": sum(1 for s in scores if s < -0.25) / len(scores) if scores else 0,
            "neutral": sum(1 for s in scores if -0.25 <= s <= 0.25) / len(scores) if scores else 0,
        }

        timestamps = [p.created_utc for p in posts if p.created_utc]

        hype_fear = SentimentAnalyzer.compute_hype_fear_index(posts)
        volatility = SentimentAnalyzer.compute_volatility(scores)

        return SentimentAggregate(
            query=query,
            source=source,
            overall_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
            confidence=round(sum(confs) / len(confs), 4) if confs else 0.0,
            distribution=distribution,
            volume=len(posts),
            top_keywords=top_keywords,
            top_posts=[p.post_id for p in posts[:5]],
            period_start=min(timestamps) if timestamps else None,
            period_end=max(timestamps) if timestamps else None,
        )
