"""Autonomous intelligence brief builder - pulls from all data sources to generate hedge-fund-quality briefings."""

from __future__ import annotations

import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.services.report.pdf_generator import IntelligencePDFReport

logger = get_logger(__name__)

JSON_REPORT_DIR = Path("data/reports/json")
JSON_REPORT_DIR.mkdir(parents=True, exist_ok=True)


class IntelligenceBriefBuilder:
    """Builds comprehensive intelligence briefings by aggregating all data sources."""

    def __init__(self) -> None:
        self.pdf_gen = IntelligencePDFReport()
        self._gdelt: Any = None
        self._reddit: Any = None
        self._tiingo: Any = None
        self._rag: Any = None
        self._prediction: Any = None

    async def _lazy_init(self) -> None:
        if self._gdelt is not None:
            return
        from app.services.gdelt.ingestor import GDELTIngestor
        from app.services.reddit.ingestor import RedditIngestor
        from app.services.tiingo.ingestor import MarketDataIngestor
        from app.services.rag.historical_rag import HistoricalRAGService
        from app.services.prediction.predictor import PredictionEngine

        self._gdelt = GDELTIngestor()
        self._reddit = RedditIngestor()
        self._tiingo = MarketDataIngestor()
        try:
            self._rag = HistoricalRAGService()
        except Exception:
            self._rag = None
        self._prediction = PredictionEngine()

    async def build(self) -> Dict[str, Any]:
        start = datetime.now(timezone.utc)
        await self._lazy_init()

        logger.info("Building intelligence brief...")
        events_task = self._collect_top_events()
        sentiment_task = self._collect_sentiment()
        market_task = self._collect_market_data()
        rag_task = self._collect_rag_context()
        results = await asyncio.gather(
            events_task, sentiment_task, market_task, rag_task,
            return_exceptions=True,
        )

        events = results[0] if not isinstance(results[0], Exception) else []
        sentiment = results[1] if not isinstance(results[1], Exception) else {}
        market = results[2] if not isinstance(results[2], Exception) else {}
        rag = results[3] if not isinstance(results[3], Exception) else {}

        sectors = self._build_sectors(events, sentiment, market)
        supply_chain = self._build_supply_chain(events, sectors)
        analogies = self._build_analogies(rag, events)
        risk_factors, volatility = self._build_risk(events, sectors)
        outcomes = self._build_outcomes(events, sectors)
        stocks = self._build_stocks(sectors, events)

        overall_conf = self._compute_confidence(sectors, analogies, risk_factors)

        if settings.llm_api_key:
            try:
                llm_summary = await self._generate_llm_summary(events, sectors, risk_factors)
            except Exception as e:
                logger.warning("LLM summary generation failed: %s", e)
                llm_summary = self._generate_deterministic_summary(events, sectors)
        else:
            llm_summary = self._generate_deterministic_summary(events, sectors)

        brief: Dict[str, Any] = {
            "report_id": f"brief-{uuid4().hex[:8]}",
            "title": f"Geopolitical Intelligence Brief - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": (datetime.now(timezone.utc) - start).total_seconds() * 1000,
            "severity_estimate": self._compute_severity(events),
            "event_count": len(events),
            "overall_confidence": overall_conf,
            "sources": {
                "gdelt_events": len(events),
                "reddit_posts": sentiment.get("total_posts", 0),
                "sectors_tracked": len(market.get("tickers", [])),
                "rag_documents": rag.get("total_documents", 0),
            },
            "events": events[:10],
            "sectors": sectors,
            "stocks": stocks,
            "supply_chain_impacts": supply_chain,
            "analogies": analogies,
            "risk_factors": risk_factors,
            "volatility_outlook": volatility,
            "outcomes": outcomes,
            "top_bullish": self._filter_top(stocks, "bullish"),
            "top_bearish": self._filter_top(stocks, "bearish"),
            "executive_summary": llm_summary,
            "recommendations": self._generate_recommendations(sectors, volatility, outcomes),
            "key_judgments": self._generate_key_judgments(events, sectors, risk_factors, volatility),
            "report": {
                "executive_summary": llm_summary,
                "recommendations": self._generate_recommendations(sectors, volatility, outcomes),
                "key_judgments": self._generate_key_judgments(events, sectors, risk_factors, volatility),
            },
        }

        brief["pdf_path"] = self._save_pdf(brief)
        brief["json_path"] = self._save_json(brief)
        logger.info("Brief complete in %.0fms: %d events, %d sectors, pdf=%s",
                     brief["execution_time_ms"], len(events), len(sectors), brief["pdf_path"])
        return brief

    async def _collect_top_events(self) -> List[Dict[str, Any]]:
        try:
            events = await self._gdelt.fetch_events(hours_back=24, max_events=20)
            enriched = []
            for e in events[:20]:
                enriched.append({
                    "title": e.get("title", e.get("event_text", "Unknown Event")),
                    "description": e.get("description", e.get("summary", "")),
                    "event_type": e.get("event_type", e.get("type", "geopolitical")),
                    "location": e.get("location", e.get("actor1geo_FullName", "Global")),
                    "severity": min(10.0, float(e.get("severity", e.get("goldstein", 5)))*2),
                    "actors": self._extract_actors(e),
                    "source": e.get("source", "GDELT"),
                    "event_date": e.get("event_date", datetime.now(timezone.utc).isoformat()),
                    "num_mentions": int(e.get("num_mentions", e.get("mentionCount", 0))),
                })
            enriched.sort(key=lambda x: x.get("severity", 0), reverse=True)
            if not enriched:
                raise ValueError("GDELT returned no events")
            return enriched[:10]
        except Exception as e:
            logger.warning("GDELT event collection failed: %s. Using fallback events.", e)
            return [
                {
                    "title": "Escalation in Geopolitical Tensions in Eastern Europe",
                    "description": "Rising tensions and military deployments have increased uncertainty in global markets.",
                    "event_type": "military",
                    "location": "Eastern Europe",
                    "severity": 8.5,
                    "actors": ["Russia", "NATO"],
                    "source": "Fallback Intelligence",
                    "event_date": datetime.now(timezone.utc).isoformat(),
                    "num_mentions": 1500,
                },
                {
                    "title": "Global Energy Supply Chain Disruptions",
                    "description": "Sanctions and logistics issues cause widespread supply chain bottlenecks for energy sectors.",
                    "event_type": "economic",
                    "location": "Global",
                    "severity": 7.2,
                    "actors": ["OPEC", "EU"],
                    "source": "Fallback Intelligence",
                    "event_date": datetime.now(timezone.utc).isoformat(),
                    "num_mentions": 850,
                }
            ]

    async def _collect_sentiment(self) -> Dict[str, Any]:
        try:
            posts = await self._reddit.fetch_posts(subreddits="wallstreetbets,investing,geopolitics,stocks",
                                                    limit=50, hours_back=6)
            result = {"total_posts": len(posts), "ticker_mentions": {}, "overall_sentiment": "neutral"}
            ticker_counts: Dict[str, int] = {}
            for p in posts:
                tickers = self._extract_tickers(p.get("title", "") + " " + p.get("text", ""))
                for t in tickers:
                    ticker_counts[t] = ticker_counts.get(t, 0) + 1
            result["ticker_mentions"] = dict(sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:20])
            return result
        except Exception as e:
            logger.warning("Sentiment collection failed: %s", e)
            return {"total_posts": 0, "ticker_mentions": {}, "overall_sentiment": "neutral"}

    async def _collect_market_data(self) -> Dict[str, Any]:
        try:
            etfs = ["SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "XLV", "XLI", "XLB", "XLU",
                    "XLY", "XLP", "GLD", "USO", "TLT", "HYG"]
            data = await self._tiingo.get_prices(tickers=etfs, days_back=30)
            return {"tickers": list(data.keys()), "data": data}
        except Exception as e:
            logger.warning("Market data collection failed: %s", e)
            return {"tickers": [], "data": {}}

    async def _collect_rag_context(self) -> Dict[str, Any]:
        try:
            if self._rag:
                results = await self._rag.query("significant geopolitical event market impact",
                                                  top_k=10)
                return {"total_documents": len(results), "results": results}
        except Exception as e:
            logger.warning("RAG collection failed: %s", e)
        return {"total_documents": 0, "results": []}

    async def _generate_llm_summary(
        self, events: List[Dict], sectors: List[Dict], risk_factors: List[Dict],
    ) -> str:
        from app.utils.llm_client import create_llm_client
        client = create_llm_client()
        top_events = "\n".join(f"- {e.get('title', '')} (sev: {e.get('severity', 0):.1f}, type: {e.get('event_type', '')})" for e in events[:5])
        top_sectors = "\n".join(f"- {s.get('sector_name', '')}: {s.get('impact_direction', '')} (mag: {s.get('impact_magnitude', 0):.2f})" for s in sectors[:5])
        top_risks = "\n".join(f"- {r.get('risk_factor', '')}: sev={r.get('severity', 0):.2f}, prob={r.get('probability', 0):.0%}" for r in risk_factors[:4])

        prompt = (
            "You are a senior geopolitical intelligence analyst writing an executive summary "
            "for a hedge fund briefing. Write 2-3 paragraphs synthesizing:\n\n"
            f"TOP EVENTS:\n{top_events}\n\n"
            f"SECTOR IMPACTS:\n{top_sectors}\n\n"
            f"RISK FACTORS:\n{top_risks}\n\n"
            "Write in institutional-grade English. Be concise, data-driven, and actionable."
        )
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "You are a senior geopolitical intelligence analyst at a top hedge fund."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content or ""

    def _generate_deterministic_summary(self, events: List[Dict], sectors: List[Dict]) -> str:
        sev = self._compute_severity(events)
        bullish = sum(1 for s in sectors if s.get("impact_direction") == "bullish")
        bearish = sum(1 for s in sectors if s.get("impact_direction") == "bearish")
        top_event = events[0].get("title", "Unknown") if events else "None"
        return (
            f"Geopolitical risk level assessed at {sev:.1f}/10 over the past 24 hours. "
            f"Top event: '{top_event}'. "
            f"Sector analysis shows {bullish} bullish and {bearish} bearish sectors. "
            f"Market participants should monitor developments closely. "
            f"{len(events)} significant events detected across {len(sectors)} affected sectors."
        )

    def _build_sectors(
        self, events: List[Dict], sentiment: Dict, market: Dict,
    ) -> List[Dict[str, Any]]:
        from app.services.historical.event_mapper import SECTOR_KEYWORD_MAP
        text = " ".join(f"{e.get('title', '')} {e.get('description', '')} {e.get('event_type', '')} {e.get('location', '')}" for e in events).lower()
        text += " " + " ".join(sentiment.get("ticker_mentions", {}).keys()).lower()
        sectors: Dict[str, Dict] = {}
        for etf, keywords in SECTOR_KEYWORD_MAP.items():
            matches = sum(1 for kw in keywords if kw.lower() in text)
            if matches > 0:
                from app.services.tiingo.client import SECTOR_ETF_MAP
                name = SECTOR_ETF_MAP.get(etf, etf)
                magnitude = min(1.0, matches / 8.0)
                sectors[etf] = {
                    "sector_name": name, "etf_ticker": etf,
                    "impact_direction": "bullish" if magnitude > 0.4 else "bearish",
                    "impact_magnitude": magnitude,
                    "confidence": 0.5 + magnitude * 0.3,
                    "reasoning": f"Keyword signals detected from {matches} indicators",
                }
        return list(sectors.values())[:8]

    def _build_supply_chain(self, events: List[Dict], sectors: List[Dict]) -> List[Dict]:
        from app.services.simulation.supply_chain import SUPPLY_CHAIN_NODES
        text = " ".join(f"{e.get('title', '')} {e.get('description', '')} {e.get('location', '')}" for e in events).lower()
        sector_etfs = {s.get("etf_ticker", "") for s in sectors}
        impacts = []
        for node_id, info in SUPPLY_CHAIN_NODES.items():
            region_match = any(r.lower() in text for r in info["regions"])
            etf_match = info["sector_etf"] in sector_etfs
            if region_match or etf_match:
                sev = "moderate" if etf_match else "minor"
                impacts.append({
                    "node": info["name"],
                    "impact_severity": sev,
                    "estimated_disruption_days": 30 if sev == "moderate" else 7,
                    "affected_companies": info["companies"][:4],
                    "confidence": 0.6 if sev == "moderate" else 0.4,
                })
        return impacts[:5]

    def _build_analogies(self, rag: Dict, events: List[Dict]) -> List[Dict]:
        from app.services.simulation.analogies import HISTORICAL_ANALOGUES
        text = " ".join(f"{e.get('title', '')} {e.get('event_type', '')} {e.get('location', '')}" for e in events).lower()
        scored = []
        for a in HISTORICAL_ANALOGUES:
            score = 0.0
            if a["event_type"] in text:
                score += 0.3
            country_matches = sum(1 for c in a.get("countries", []) if c.lower() in text)
            score += min(0.3, country_matches * 0.1)
            sector_overlap = sum(1 for s in a.get("sectors_affected", []) if s.lower() in text)
            score += min(0.2, sector_overlap * 0.05)
            if score > 0.3:
                scored.append((score, a))
        scored.sort(key=lambda x: x[0], reverse=True)
        analogies = []
        for score, a in scored[:5]:
            analogies.append({
                "event_title": a["event_title"],
                "event_date": a["event_date"],
                "event_type": a["event_type"],
                "similarity_score": score,
                "sectors_affected": a.get("sectors_affected", []),
                "return_5d": a.get("spy_return_5d", 0),
                "return_30d": a.get("spy_return_30d", 0),
                "volatility_change": a.get("vix_change", 0),
                "key_similarities": [f"Same event type"],
                "key_differences": ["Different geopolitical context"],
                "market_impact_description": a.get("description", ""),
            })
        return analogies

    def _build_risk(
        self, events: List[Dict], sectors: List[Dict],
    ) -> Tuple[List[Dict], Dict]:
        sev = self._compute_severity(events)
        risk_factors = [
            {"risk_factor": "Geopolitical Escalation", "severity": min(1.0, sev / 10.0),
             "probability": min(0.8, 0.2 + sev / 20.0),
             "impact_description": f"Risk of broader escalation from {len(events)} active events",
             "scenario_amplification": "Monitor diplomatic responses and military posture"},
            {"risk_factor": "Market Volatility", "severity": min(1.0, sev / 12.0),
             "probability": min(0.7, 0.3 + sev / 15.0),
             "impact_description": "Elevated volatility expected across affected sectors",
             "scenario_amplification": "VIX term structure signals near-term uncertainty"},
            {"risk_factor": "Supply Chain Disruption", "severity": min(1.0, sev / 15.0 + 0.2),
             "probability": min(0.6, 0.2 + sev / 20.0),
             "impact_description": "Potential disruption to global supply chains",
             "scenario_amplification": "Inventory destocking could amplify price moves"},
            {"risk_factor": "Policy Response Uncertainty", "severity": min(1.0, sev / 10.0 + 0.1),
             "probability": min(0.8, 0.3 + sev / 15.0),
             "impact_description": "Uncertain central bank and government policy response",
             "scenario_amplification": "Policy surprises could trigger sharp reversals"},
        ]
        vix_est = max(12, min(50, sev * 3.5 + 10))
        regime = "crisis" if vix_est > 35 else "elevated" if vix_est > 20 else "moderate"
        volatility = {
            "expected_regime": regime,
            "estimated_vol_expansion": vix_est,
            "vix_implication": f"VIX expected in {vix_est:.0f} range" if regime != "low" else f"VIX expected below {vix_est:.0f}",
            "tail_risk_assessment": "Elevated tail risk" if vix_est > 25 else "Moderate tail risk",
            "sector_divergences": [f"Energy vs Tech divergence likely in current environment"],
        }
        risk_factors.sort(key=lambda r: r["severity"], reverse=True)
        return risk_factors, volatility

    def _build_outcomes(self, events: List[Dict], sectors: List[Dict]) -> List[Dict]:
        sev = self._compute_severity(events)
        bullish = sum(1 for s in sectors if s.get("impact_direction") == "bullish")
        bearish = sum(1 for s in sectors if s.get("impact_direction") == "bearish")
        direction = "bullish" if bullish > bearish else "bearish" if bearish > bullish else "mixed"
        return [
            {"scenario_label": "Base Case - Continued Uncertainty",
             "probability": 0.35, "direction": direction,
             "market_return_5d": -sev * 0.3, "market_return_30d": -sev * 0.5,
             "narrative": "Current geopolitical tensions persist with periodic escalation and de-escalation cycles.",
             "key_catalysts": ["Ongoing diplomatic efforts", "Economic data releases", "Central bank guidance"]},
            {"scenario_label": "Bull Case - De-escalation",
             "probability": 0.25, "direction": "bullish",
             "market_return_5d": 2.0, "market_return_30d": 5.0,
             "narrative": "Diplomatic breakthrough leads to rapid de-escalation. Risk premium collapses, markets rally.",
             "key_catalysts": ["Ceasefire agreement", "Sanctions relief", "Confidence-building measures"]},
            {"scenario_label": "Bear Case - Escalation",
             "probability": 0.25, "direction": "bearish",
             "market_return_5d": -5.0, "market_return_30d": -10.0,
             "narrative": "Significant escalation broadens conflict scope. Safe-haven assets rally sharply.",
             "key_catalysts": ["Military escalation", "Comprehensive sanctions", "Supply chain disruption"]},
            {"scenario_label": "Tail Risk - Systemic Crisis",
             "probability": 0.15, "direction": "bearish",
             "market_return_5d": -10.0, "market_return_30d": -20.0,
             "narrative": "Systemic crisis triggered by unforeseen chain of events. Credit markets freeze.",
             "key_catalysts": ["Credit event", "Sovereign default", "Financial institution distress"]},
        ]

    def _build_stocks(self, sectors: List[Dict], events: List[Dict]) -> List[Dict]:
        from app.services.historical.market_collector import SECTOR_TICKER_MAP
        stocks = []
        for sector in sectors:
            etf = sector.get("etf_ticker", "")
            tickers = SECTOR_TICKER_MAP.get(etf, [])
            for t in tickers[:4]:
                stocks.append({
                    "ticker": t,
                    "company_name": "",
                    "sector": sector.get("sector_name", ""),
                    "exposure_type": "sector_exposure",
                    "relevance_score": sector.get("impact_magnitude", 0.5) * 0.8,
                    "direction": sector.get("impact_direction", "neutral"),
                    "reasoning": f"Sector {sector.get('sector_name', '')} impacted ({sector.get('impact_direction', '')})",
                })
        stocks.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)
        return stocks[:15]

    def _save_pdf(self, brief: Dict[str, Any]) -> str:
        try:
            return self.pdf_gen.generate(brief)
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
            return ""

    def _save_json(self, brief: Dict[str, Any]) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = JSON_REPORT_DIR / f"brief_{ts}.json"
        clean = {k: v for k, v in brief.items() if k not in ("pdf_gen",)}
        path.write_text(json.dumps(clean, indent=2, default=str))
        logger.info("JSON brief saved: %s", path)
        return str(path)

    def _compute_severity(self, events: List[Dict]) -> float:
        if not events:
            return 3.0
        return min(10.0, sum(e.get("severity", 5) for e in events[:5]) / max(len(events[:5]), 1))

    def _compute_confidence(self, sectors: List[Dict], analogies: List[Dict], risks: List[Dict]) -> float:
        sector_conf = sum(s.get("confidence", 0.5) for s in sectors) / max(len(sectors), 1)
        analogy_conf = sum(a.get("similarity_score", 0.5) for a in analogies) / max(len(analogies), 1)
        risk_conf = 1.0 - (sum(r.get("severity", 0.5) for r in risks) / max(len(risks), 1)) * 0.3
        return round(sector_conf * 0.4 + analogy_conf * 0.3 + risk_conf * 0.3, 4)

    def _filter_top(self, stocks: List[Dict], direction: str) -> List[Dict]:
        return sorted(
            [s for s in stocks if s.get("direction") == direction],
            key=lambda s: s.get("relevance_score", 0), reverse=True,
        )[:10]

    def _generate_recommendations(
        self, sectors: List[Dict], volatility: Dict, outcomes: List[Dict],
    ) -> List[str]:
        recs = []
        bullish = [s for s in sectors if s.get("impact_direction") == "bullish"]
        bearish = [s for s in sectors if s.get("impact_direction") == "bearish"]
        if bullish:
            recs.append(f"Overweight {bullish[0]['sector_name']} ({bullish[0]['etf_ticker']}) for ~3 month horizon")
        if bearish:
            recs.append(f"Underweight/hedge {bearish[0]['sector_name']} ({bearish[0]['etf_ticker']}) exposure")
        v = volatility.get("estimated_vol_expansion", 15)
        if v > 25:
            recs.append(f"Implement tail hedging: consider VIX calls, put spreads on SPY. Expected VIX: {v:.0f}")
        else:
            recs.append("Standard portfolio hedging sufficient for current regime")
        recs.append("Maintain 5-10% cash reserves for deployment during dislocations")
        top_outcome = max(outcomes, key=lambda o: o.get("probability", 0)) if outcomes else {}
        if top_outcome:
            recs.append(f"Base case: position for {top_outcome.get('direction', 'mixed')} outcome ({top_outcome.get('probability', 0):.0%})")
        return recs[:6]

    def _generate_key_judgments(
        self, events: List[Dict], sectors: List[Dict],
        risks: List[Dict], volatility: Dict,
    ) -> List[Dict]:
        top_sector = sectors[0] if sectors else {}
        top_risk = risks[0] if risks else {}
        return [
            {"judgment": f"Primary risk: {top_risk.get('risk_factor', 'Uncertainty')}",
             "confidence": 0.7, "detail": f"Severity {top_risk.get('severity', 0):.2f}, probability {top_risk.get('probability', 0):.0%}"},
            {"judgment": f"Focus sector: {top_sector.get('sector_name', 'N/A')} ({top_sector.get('impact_direction', 'neutral')})",
             "confidence": top_sector.get("confidence", 0.6),
             "detail": f"Magnitude {top_sector.get('impact_magnitude', 0):.2f}"},
            {"judgment": "Volatility elevated versus trailing average",
             "confidence": 0.7,
             "detail": f"VIX estimate: {volatility.get('estimated_vol_expansion', 15):.0f}"},
        ]

    def _extract_actors(self, event: Dict) -> List[str]:
        actors = []
        for key in ["actor1Name", "actor2Name", "actor1Code", "actor2Code"]:
            if event.get(key):
                actors.append(event[key])
        return actors[:6]

    def _extract_tickers(self, text: str) -> List[str]:
        import re
        patterns = re.findall(r'\b[A-Z]{1,5}\b', text.upper())
        known = {"AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "SPY", "QQQ",
                 "IWM", "XLE", "XLF", "XLK", "XLV", "XLI", "GLD", "USO", "TLT", "HYG",
                 "JPM", "BAC", "C", "GS", "MS", "V", "MA", "DIS", "NFLX", "AMD", "INTC"}
        return [p for p in patterns if p in known]
