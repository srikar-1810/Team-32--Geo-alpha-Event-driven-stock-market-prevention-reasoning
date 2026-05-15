from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.services.historical.models import HistoricalMarketImpact, ImpactDirection
from app.services.historical.orchestrator import HistoricalOrchestrator
from app.services.rag.historical_rag import HistoricalRAGService
from app.services.reddit.analyzer import SentimentAnalyzer
from app.services.reddit.client import RedditClient
from app.services.tiingo.client import TiingoClient, SECTOR_ETF_MAP
from app.services.yahoo.client import YahooFinanceClient

logger = get_logger(__name__)


class SignalAggregator:
    """Aggregates all signals used in predictions."""

    def __init__(self) -> None:
        self.tiingo = TiingoClient()
        self.yahoo = YahooFinanceClient()
        self.rag = HistoricalRAGService()
        self.reddit = RedditClient()
        self.analyzer = SentimentAnalyzer()
        self.orchestrator = HistoricalOrchestrator()

    async def compute_all_signals(
        self,
        query: str,
        target_tickers: Optional[List[str]] = None,
        target_sectors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute all signal sources for a given query/tickers/sectors."""
        geo_signal = await self._compute_geopolitical_signal(query)
        social_signal = await self._compute_social_signal(query, target_tickers)
        historical_signal = await self._compute_historical_signal(query)
        momentum_signals = await self._compute_momentum_signals(target_tickers, target_sectors)
        volatility_signals = await self._compute_volatility_signals(target_tickers, target_sectors)

        return {
            "geopolitical": geo_signal,
            "social": social_signal,
            "historical": historical_signal,
            "momentum": momentum_signals,
            "volatility": volatility_signals,
            "metadata": {
                "computed_at": datetime.now(timezone.utc).isoformat(),
                "query": query,
                "tickers": target_tickers or [],
                "sectors": target_sectors or [],
            },
        }

    async def _compute_geopolitical_signal(self, query: str) -> Dict[str, Any]:
        """Extract signal strength from news intelligence."""
        from app.services.gdelt.client import GDELTClient
        from app.services.gdelt.parser import GDELTParser

        client = GDELTClient()
        parser = GDELTParser()

        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=3)
            articles = await client.fetch_article_list(query, start, end, max_records=20)
            events = [parser.parse_article(a) for a in articles if parser.parse_article(a)]

            if not events:
                return {"signal_strength": 0.0, "direction": "neutral", "event_count": 0, "avg_severity": 0.0, "high_signal_events": 0}

            severities = [e.severity for e in events]
            tones = []
            for e in events:
                raw = e.gdelt_raw or {}
                tone = raw.get("tone", {}) if isinstance(raw, dict) else {}
                tones.append(tone.get("tone_score", tone.get("normalized", 0) if isinstance(tone, dict) else 0))

            avg_severity = sum(severities) / len(severities) if severities else 0
            avg_tone = sum(tones) / len(tones) if tones else 0

            high_signal = sum(1 for e in events if parser.compute_signal_strength(e)["is_high_signal"])
            total_mentions = sum(e.mentions for e in events)

            signal = min(1.0, (avg_severity / 10.0) * 0.5 + (high_signal / max(len(events), 1)) * 0.3 + min(1.0, total_mentions / 500.0) * 0.2)

            if avg_tone < -3:
                direction = "bearish"
            elif avg_tone > 3:
                direction = "bullish"
            else:
                direction = "neutral"

            sectors_hit: set = set()
            for e in events:
                sectors_hit.update(e.affected_sectors)

            return {
                "signal_strength": round(signal, 4),
                "direction": direction,
                "event_count": len(events),
                "avg_severity": round(avg_severity, 2),
                "avg_tone": round(avg_tone, 2),
                "high_signal_events": high_signal,
                "total_mentions": total_mentions,
                "sectors_mentioned": list(sectors_hit),
            }
        except Exception as e:
            logger.warning("Geopolitical signal failed: %s", e)
            return {"signal_strength": 0.0, "direction": "neutral", "event_count": 0, "avg_severity": 0.0}
        finally:
            await client.close()

    async def _compute_social_signal(self, query: str, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extract signal from social media sentiment."""
        try:
            search_terms = [query]
            if tickers:
                search_terms.extend(tickers[:5])

            all_posts = []
            for term in search_terms[:3]:
                posts = await self.reddit.fetch_multiple_subreddits(subreddits=None, limit=30)
                all_posts.extend(posts)

            if not all_posts:
                return {"signal_strength": 0.0, "direction": "neutral", "post_count": 0, "avg_score": 0.0, "confidence": 0.0}

            analyzed = [self.analyzer.analyze_post(p) for p in all_posts]
            aggregate = self.analyzer.aggregate(analyzed, query=query)

            score = aggregate.overall_score
            conf = aggregate.confidence
            vol = aggregate.volume

            signal_str = aggregate.get("signal", "") if hasattr(aggregate, "signal") else ""
            if not signal_str:
                if score > 0.15 and conf > 0.3:
                    signal_str = "bullish"
                elif score < -0.15 and conf > 0.3:
                    signal_str = "bearish"
                else:
                    signal_str = "neutral"

            strength = min(1.0, abs(score) * 0.5 + conf * 0.3 + min(1.0, vol / 200.0) * 0.2)

            return {
                "signal_strength": round(strength, 4),
                "direction": signal_str,
                "post_count": len(analyzed),
                "avg_score": round(score, 4),
                "confidence": round(conf, 4),
                "volume": vol,
                "distribution": aggregate.distribution if hasattr(aggregate, "distribution") else {},
                "top_keywords": aggregate.top_keywords[:10] if hasattr(aggregate, "top_keywords") else [],
            }
        except Exception as e:
            logger.warning("Social signal failed: %s", e)
            return {"signal_strength": 0.0, "direction": "neutral", "post_count": 0}

    async def _compute_historical_signal(self, query: str) -> Dict[str, Any]:
        """Extract signal from historical analogues."""
        try:
            results = await self.rag.retrieve_similar(query_text=query, top_k=15)
            if not results:
                return {"signal_strength": 0.0, "direction": "neutral", "analogue_count": 0, "avg_similarity": 0.0}

            similarities = [r["similarity"] for r in results]
            avg_sim = sum(similarities) / len(similarities) if similarities else 0

            bullish_count = sum(
                1 for r in results
                if r.get("metadata", {}).get("sectors", "")
            )
            market_reactions = self.rag.extract_market_reactions(results)
            avg_5d = market_reactions.get("avg_market_return_5d", 0)
            avg_30d = market_reactions.get("avg_market_return_30d", 0)

            signal = min(1.0, avg_sim * 0.5 + (bullish_count / max(len(results), 1)) * 0.3 + min(1.0, abs(avg_5d) / 15.0) * 0.2)

            if avg_5d > 2:
                direction = "bullish"
            elif avg_5d < -2:
                direction = "bearish"
            else:
                direction = "neutral"

            return {
                "signal_strength": round(signal, 4),
                "direction": direction,
                "analogue_count": len(results),
                "avg_similarity": round(avg_sim, 4),
                "avg_historical_return_5d": round(avg_5d, 2),
                "avg_historical_return_30d": round(avg_30d, 2),
                "market_reactions": market_reactions,
            }
        except Exception as e:
            logger.warning("Historical signal failed: %s", e)
            return {"signal_strength": 0.0, "direction": "neutral", "analogue_count": 0}

    async def _compute_momentum_signals(
        self, tickers: Optional[List[str]] = None, sectors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extract momentum signals from market data."""
        signals: Dict[str, Any] = {"tickers": {}, "sectors": {}, "overall_market": {}}
        try:
            if tickers:
                for t in tickers:
                    try:
                        mom = await self.yahoo.compute_technical_indicators(t, days=100)
                        if isinstance(mom, dict) and "error" not in mom:
                            signals["tickers"][t] = {
                                "momentum_10d": mom.get("momentum_10d_pct", 0),
                                "momentum_20d": mom.get("momentum_20d_pct", 0),
                                "rsi_14": mom.get("rsi_14", 50),
                                "sma_20_distance": mom.get("distance_from_20d_high_pct", 0),
                                "trend": mom.get("trend", "neutral"),
                            }
                    except Exception:
                        continue

            macro_tickers = ["SPY", "QQQ", "IWM"]
            for t in macro_tickers:
                try:
                    mom = await self.yahoo.compute_technical_indicators(t, days=100)
                    if isinstance(mom, dict) and "error" not in mom:
                        signals["overall_market"][t] = {
                            "momentum_10d": mom.get("momentum_10d_pct", 0),
                            "momentum_20d": mom.get("momentum_20d_pct", 0),
                            "rsi_14": mom.get("rsi_14", 50),
                            "current_price": mom.get("current_price", 0),
                        }
                except Exception:
                    continue

            if sectors:
                sector_to_etf = {v: k for k, v in SECTOR_ETF_MAP.items()}
                for sector in sectors:
                    etf = sector_to_etf.get(sector, "")
                    if etf:
                        try:
                            mom = await self.tiingo.compute_momentum(etf)
                            if isinstance(mom, dict) and "error" not in mom:
                                signals["sectors"][sector] = {
                                    "momentum_5d": mom.get("momentum_5d_pct", 0),
                                    "momentum_10d": mom.get("momentum_10d_pct", 0),
                                    "momentum_20d": mom.get("momentum_20d_pct", 0),
                                    "rsi_14": mom.get("rsi_14", 50),
                                }
                        except Exception:
                            continue

        except Exception as e:
            logger.warning("Momentum signals failed: %s", e)

        return signals

    async def _compute_volatility_signals(
        self, tickers: Optional[List[str]] = None, sectors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extract volatility regime signals."""
        signals: Dict[str, Any] = {"overall": {}, "tickers": {}, "sectors": {}, "warning_level": "normal", "vix_level": 0}
        try:
            vix_data = await self.yahoo.get_market_data_points("VIX", date.today() - timedelta(days=30), date.today())
            if vix_data:
                vix_close = vix_data[-1].close_price
                vix_changes = [(vix_data[i].close_price - vix_data[i-1].close_price) / vix_data[i-1].close_price
                               for i in range(1, len(vix_data)) if vix_data[i-1].close_price > 0]
                vix_trend = statistics.mean(vix_changes[-5:]) if len(vix_changes) >= 5 else 0

                if vix_close > 30:
                    warning = "high"
                elif vix_close > 20:
                    warning = "elevated"
                elif vix_close > 12:
                    warning = "normal"
                else:
                    warning = "low"

                signals["overall"] = {
                    "vix_close": round(vix_close, 2),
                    "vix_trend_5d": round(vix_trend * 100, 2) if vix_trend else 0,
                    "vix_volatility": round(statistics.stdev(vix_changes[-10:]) * 100, 4) if len(vix_changes) >= 10 else 0,
                }
                signals["warning_level"] = warning
                signals["vix_level"] = round(vix_close, 2)

            if tickers:
                for t in tickers:
                    try:
                        vol = await self.tiingo.compute_volatility(t)
                        if isinstance(vol, dict) and "error" not in vol:
                            signals["tickers"][t] = {
                                "annualized_volatility": vol.get("annualized_volatility", 0),
                                "daily_volatility": vol.get("daily_volatility", 0),
                            }
                    except Exception:
                        continue

        except Exception as e:
            logger.warning("Volatility signals failed: %s", e)

        return signals

    async def close(self) -> None:
        await self.tiingo.close()
        await self.yahoo.close()
        await self.reddit.close()
        await self.rag.close()
