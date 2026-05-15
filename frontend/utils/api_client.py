from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from frontend.config import settings


class ApiClient:
    """Async HTTP client for the GeoMarketGPT API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        # Re-initialize client if it's closed or the event loop changed/closed
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if settings.MOCK_MODE:
            return self._get_mock_data(method, path, **kwargs)
        
        try:
            client = await self._get_client()
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except (RuntimeError, httpx.RequestError) as e:
            # Handle cases where the event loop is closed or other request errors
            if "Event loop is closed" in str(e) or isinstance(e, RuntimeError):
                self._client = None
                client = await self._get_client()
                response = await client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
            raise e

    def _get_mock_data(self, method: str, path: str, **kwargs) -> Any:
        """Return hardcoded sample data for all dashboard pages in demo mode."""
        now = "2024-05-14T15:00:00Z"
        
        # 1. Health
        if "/health" in path:
            return {"status": "ok", "version": settings.APP_VERSION, "services": {"db": "mock", "redis": "mock", "chroma": "mock"}}
        
        # 2. Geopolitical Events
        if "/geopol/events" in path:
            return {
                "items": [
                    {"id": "evt_1", "title": "Energy Pipeline Disruption in North Sea", "severity": 0.92, "location": "Norway/UK", "event_type": "crisis", "event_date": now, "description": "A major subsea pipeline has experienced a pressure drop. Investigations are ongoing into possible sabotage or technical failure.", "source": "GDELT", "affected_sectors": ["energy", "utilities"]},
                    {"id": "evt_2", "title": "New Trade Sanctions Announced", "severity": 0.75, "location": "Washington D.C.", "event_type": "sanctions", "event_date": now, "description": "The US Treasury has announced a new round of sanctions targeting semiconductor technology exports.", "source": "Reuters", "affected_sectors": ["technology", "finance"]},
                    {"id": "evt_3", "title": "Election Results in Key Emerging Market", "severity": 0.65, "location": "South Africa", "event_type": "election", "event_date": now, "description": "Preliminary results suggest a coalition government will be required, introducing policy uncertainty.", "source": "BBC", "affected_sectors": ["finance", "commodities"]},
                    {"id": "evt_4", "title": "Global Summit on AI Regulation", "severity": 0.45, "location": "Geneva", "event_type": "diplomacy", "event_date": now, "description": "World leaders meet to discuss a unified framework for AI safety and cross-border data flows.", "source": "UN", "affected_sectors": ["technology"]}
                ],
                "total": 4,
                "page": 1,
                "page_size": 20
            }
        
        # 3. Geopolitical Summary
        if "/geopol/summary" in path:
            return {
                "total_events": 124,
                "active_conflicts": 12,
                "high_severity_count": 8,
                "last_updated": now,
                "top_regions": ["Europe", "Middle East", "Southeast Asia"],
                "trending_topics": ["Pipeline Sabotage", "Trade War", "Lithium Supply"],
                "top_sectors_affected": ["Energy", "Technology", "Financials", "Materials"]
            }

        # 4. Sentiment Analysis
        if "sentiment" in path.lower():
            if "trends" in path.lower():
                return {
                    "ticker": kwargs.get("params", {}).get("ticker", "SPY"),
                    "data_points": [
                        {"timestamp": "2024-05-14T08:00:00Z", "score": 0.45, "volume": 120},
                        {"timestamp": "2024-05-14T10:00:00Z", "score": 0.32, "volume": 250},
                        {"timestamp": "2024-05-14T12:00:00Z", "score": 0.15, "volume": 480},
                        {"timestamp": "2024-05-14T14:00:00Z", "score": 0.55, "volume": 190}
                    ],
                    "trend_direction": "bullish",
                    "volatility": 0.12,
                    "period_hours": 24
                }
            # Default to analysis if only 'sentiment' is matched
            return {
                "ticker": kwargs.get("params", {}).get("query", "SPY"),
                "overall_score": 0.65,
                "sentiment": "bullish",
                "confidence": 0.88,
                "volume": 1250,
                "analyzed_at": now,
                "distribution": {"positive": 0.65, "neutral": 0.25, "negative": 0.10},
                "top_keywords": ["bullish", "earnings", "growth", "breakout", "demand"],
                "key_drivers": ["strong earnings", "sector rotation"]
            }

        # 5. Market Data
        if "market" in path.lower():
            if "impact" in path.lower():
                return {
                    "overall_impact_score": 0.725,
                    "confidence": 0.88,
                    "generated_at": now,
                    "affected_sectors": [
                        {"sector": "Energy", "impact_score": 0.95, "direction": "bullish"},
                        {"sector": "Technology", "impact_score": -0.62, "direction": "bearish"},
                        {"sector": "Financials", "impact_score": -0.15, "direction": "bearish"},
                        {"sector": "Defense", "impact_score": 0.44, "direction": "bullish"}
                    ]
                }
            return [
                {"date": "2024-05-10", "open": 510.2, "high": 515.5, "low": 508.3, "close": 512.4, "volume": 45000000},
                {"date": "2024-05-11", "open": 512.4, "high": 513.8, "low": 505.2, "close": 506.1, "volume": 52000000},
                {"date": "2024-05-12", "open": 506.1, "high": 511.4, "low": 504.1, "close": 509.7, "volume": 41000000},
                {"date": "2024-05-13", "open": 509.7, "high": 522.1, "low": 508.4, "close": 518.2, "volume": 61000000},
                {"date": "2024-05-14", "open": 518.2, "high": 525.0, "low": 515.2, "close": 521.8, "volume": 58000000}
            ]

        # 7. Agents & Workflow
        if "/agents" in path or "/workflow" in path:
            if method == "GET" and path.endswith("/agents"):
                return [
                    {"id": "news_agent", "name": "News Intelligence", "status": "healthy", "agent_type": "geopolitical", "model": "gpt-4-turbo"},
                    {"id": "sentiment_agent", "name": "Social Sentiment", "status": "healthy", "agent_type": "sentiment", "model": "gpt-4-turbo"},
                    {"id": "market_agent", "name": "Market Strategist", "status": "healthy", "agent_type": "market", "model": "gpt-4-turbo"},
                    {"id": "risk_agent", "name": "Risk Analyst", "status": "healthy", "agent_type": "risk", "model": "gpt-4-turbo"}
                ]
            
            return {
                "status": "completed",
                "workflow_id": "wf_12345",
                "results": {"executive_summary": "Overall market risk is increasing due to supply chain threats."},
                "items": [
                    {"id": "news_agent", "name": "News Intelligence", "status": "healthy"},
                    {"id": "sentiment_agent", "name": "Social Sentiment", "status": "healthy"},
                    {"id": "market_agent", "name": "Market Strategist", "status": "healthy"},
                    {"id": "risk_agent", "name": "Risk Analyst", "status": "healthy"}
                ]
            }

        # 8. RAG Explorer
        if "rag" in path.lower():
            return {
                "answer": "Based on the knowledge base, the North Sea pipeline disruption has historically correlated with a 5-8% spike in Brent Crude within 48 hours. Major integrated energy companies often see a positive alpha during these periods.",
                "total_results": 2,
                "processing_time_ms": 450.5,
                "results": [
                    {"content": "Historical analogue: The 2022 Nord Stream leak led to a 15% spike in European natural gas prices.", "score": 0.89, "metadata": {"event_date": "2022-09-26", "source": "Historical Database"}},
                    {"content": "Trade sanctions on semiconductor exports frequently lead to short-term volatility in tech ETFs.", "score": 0.76, "metadata": {"topic": "Trade Policy"}}
                ]
            }

        # 9. Reports & Briefings
        if "/reports" in path:
            latest_brief = {
                "report_id": "brief_20240514_001",
                "generated_at": now,
                "overall_confidence": 0.88,
                "executive_summary": "The geopolitical landscape is dominated by energy supply risks and trade tensions. We expect increased volatility in tech and energy sectors over the next 15 days.",
                "sectors": [
                    {"sector_name": "Energy", "etf_ticker": "XLE", "impact_direction": "bullish", "impact_magnitude": 0.92, "confidence": 0.90, "reasoning": "Supply disruptions in North Sea."},
                    {"sector_name": "Technology", "etf_ticker": "XLK", "impact_direction": "bearish", "impact_magnitude": 0.65, "confidence": 0.82, "reasoning": "New trade sanctions on chips."}
                ],
                "top_bullish": [
                    {"ticker": "XOM", "company": "Exxon Mobil", "relevance": 0.95, "sector": "Energy", "reasoning": "Direct beneficiary of higher crude prices and supply constraints."},
                    {"ticker": "LMT", "company": "Lockheed Martin", "relevance": 0.78, "sector": "Defense", "reasoning": "Increased regional tensions drive long-term contract expectations."}
                ],
                "top_bearish": [
                    {"ticker": "NVDA", "company": "NVIDIA", "relevance": 0.88, "sector": "Technology", "reasoning": "Exposure to export restrictions in key emerging markets."},
                    {"ticker": "TSLA", "company": "Tesla", "relevance": 0.72, "sector": "Consumer Cyclical", "reasoning": "Supply chain bottlenecks for critical materials."}
                ],
                "key_judgments": [
                    {"judgment": "Energy prices will remain elevated for 30+ days.", "confidence": 0.85, "detail": "Subsea repair timelines are estimated at 4-6 weeks."},
                    {"judgment": "Tech sector volatility will spike in Q3.", "confidence": 0.72, "detail": "Regulatory uncertainty is increasing across G7 nations."}
                ],
                "analogies": [
                    {"event_title": "2022 Nord Stream Leak", "similarity_score": 0.89, "return_5d": 12.5, "return_30d": 8.2, "volatility_change": 4.5, "event_date": "2022-09-26"},
                    {"event_title": "2019 Abqaiq–Khurais Attack", "similarity_score": 0.76, "return_5d": 15.2, "return_30d": -2.1, "volatility_change": 6.8, "event_date": "2019-09-14"}
                ],
                "outcomes": [
                    {"scenario_label": "Prolonged Energy Crisis", "probability": 0.55, "direction": "bearish", "narrative": "Escalation of supply chain sabotage leads to global energy rationing.", "market_return_5d": -4.2, "market_return_30d": -12.5},
                    {"scenario_label": "Diplomatic Resolution", "probability": 0.25, "direction": "bullish", "narrative": "De-escalation through international mediation stabilizes prices.", "market_return_5d": 3.1, "market_return_30d": 6.8},
                    {"scenario_label": "Limited Containment", "probability": 0.20, "direction": "mixed", "narrative": "Regional impact is managed but global sentiment remains cautious.", "market_return_5d": -0.5, "market_return_30d": 1.2}
                ],
                "volatility_outlook": {
                    "estimated_vol_expansion": 22.4,
                    "expected_regime": "high_volatility"
                }
            }

            if "/brief/latest" in path:
                return latest_brief
            
            if "/brief/list" in path:
                return {
                    "items": [latest_brief, {**latest_brief, "report_id": "brief_20240514_000", "generated_at": "2024-05-14T14:00:00Z"}],
                    "total": 2
                }
            
            return {
                "items": [
                    {"id": "rep_1", "report_id": "rep_1", "title": "Weekly Geopolitical Risk Report", "format": "pdf", "status": "completed", "created_at": now, "author": "GeoGPT AI"},
                    {"id": "rep_2", "report_id": "rep_2", "title": "Energy Sector Outlook Q3", "format": "json", "status": "completed", "created_at": now, "author": "GeoGPT AI"}
                ],
                "total": 2
            }

        # 10. Simulation
        if "/simulation/run" in path:
            json_data = kwargs.get("json", {})
            query_val = json_data.get("query", "") if isinstance(json_data, dict) else ""
            q = query_val.lower()
            
            # Scenario A: Taiwan / Semiconductor
            if "taiwan" in q or "china" in q or "semiconductor" in q:
                return {
                    "execution_time_ms": 1560,
                    "overall_confidence": 0.75,
                    "parsed_scenario": {
                        "event_type": "Supply Chain Disruption",
                        "severity_estimate": 9.2,
                        "economic_scope": "Global",
                        "estimated_timeline": "long_term",
                        "countries": ["Taiwan", "China", "USA", "Japan"],
                        "actors": ["TSMC", "CCP", "US State Dept"],
                        "uncertainty_factors": ["Fabrication plant safety", "Blockade duration"]
                    },
                    "sectors": [
                        {"sector_name": "Technology", "etf_ticker": "XLK", "impact_direction": "bearish", "impact_magnitude": 0.98, "reasoning": "Taiwan produces 60% of world semiconductors and 90% of advanced chips."},
                        {"sector_name": "Defense", "etf_ticker": "ITA", "impact_direction": "bullish", "impact_magnitude": 0.85, "reasoning": "Increased procurement for regional security and naval presence."},
                        {"sector_name": "Automotive", "etf_ticker": "CARZ", "impact_direction": "bearish", "impact_magnitude": 0.65, "reasoning": "Immediate halt to smart-vehicle production due to chip shortage."}
                    ],
                    "top_bullish": [
                        {"ticker": "INTC", "company": "Intel", "relevance": 0.88, "sector": "Technology", "reasoning": "On-shoring play; beneficiary of US-based fabrication incentives."},
                        {"ticker": "RTX", "company": "Raytheon", "relevance": 0.82, "sector": "Defense", "reasoning": "High demand for missile defense systems in the Pacific."}
                    ],
                    "top_bearish": [
                        {"ticker": "AAPL", "company": "Apple", "relevance": 0.95, "sector": "Technology", "reasoning": "Extreme vulnerability in supply chain and manufacturing assembly."},
                        {"ticker": "TSM", "company": "TSMC", "relevance": 1.0, "sector": "Technology", "reasoning": "Direct physical risk to assets and production capacity."}
                    ],
                    "supply_chain_impacts": [
                        {
                            "node": "Hsinchu Science Park",
                            "impact_severity": "critical",
                            "description": "Heart of global advanced logic chip production at risk of total shutdown.",
                            "affected_companies": ["NVIDIA", "Apple", "AMD"],
                            "estimated_disruption_days": 180,
                            "confidence": 0.95
                        }
                    ],
                    "analogies": [
                        {
                            "event_title": "2011 Tohoku Earthquake",
                            "event_date": "2011-03-11",
                            "similarity_score": 0.65,
                            "key_similarities": ["Localized tech supply cluster hit", "Global ripple effects"],
                            "key_differences": ["Geopolitical intent vs Natural disaster", "Scale of advanced node dependency"],
                            "return_5d": -5.2,
                            "return_30d": -2.8,
                            "volatility_change": 8.4
                        }
                    ],
                    "outcomes": [
                        {
                            "scenario_label": "Extended Tech Dark Age",
                            "probability": 0.40,
                            "direction": "bearish",
                            "market_return_5d": -12.5,
                            "market_return_30d": -18.0,
                            "narrative": "Global GDP contracts as high-end manufacturing stalls indefinitely.",
                            "key_catalysts": ["Port blockade", "Power grid sabotage"]
                        }
                    ],
                    "risk_factors": [
                        {"risk_factor": "Manufacturing Paralysis", "severity": 0.95, "probability": 0.70, "impact_description": "Electronics and automotive assembly lines freeze globally."}
                    ],
                    "volatility_outlook": {
                        "expected_regime": "extreme_volatility",
                        "estimated_vol_expansion": 35.0,
                        "tail_risk_assessment": "Systemic risk to the Nasdaq-100"
                    },
                    "report": {
                        "title": "Simulation: Pacific Semiconductor Crisis",
                        "executive_summary": "This scenario represents a 'black swan' event for the global technology sector. The concentration of advanced chip manufacturing in the Taiwan Strait creates a single point of failure for the modern economy.",
                        "key_judgments": [
                            {"judgment": "Tech earnings will fall 40% year-over-year.", "confidence": 0.88, "detail": "Inventory buffers only last 3-5 weeks for major OEMs."},
                            {"judgment": "US domestic fabrication will take 5 years to scale.", "confidence": 0.92, "detail": "CHIPS Act projects are still in early construction phases."}
                        ],
                        "recommendations": [
                            "Rotate heavily into old-economy/commodities.",
                            "Avoid consumer electronics and high-growth SaaS.",
                            "Buy long-dated VIX calls."
                        ],
                        "confidence_assessment": "Moderate (uncertainty on escalation depth)",
                        "disclaimers": ["Assumes no immediate US-China kinetic resolution."]
                    }
                }

            # Scenario B: US Debt / Economy
            if "debt" in q or "default" in q or "treasury" in q or "usa" in q:
                return {
                    "execution_time_ms": 1100,
                    "overall_confidence": 0.90,
                    "parsed_scenario": {
                        "event_type": "Financial Crisis",
                        "severity_estimate": 7.8,
                        "economic_scope": "Global / Macro",
                        "estimated_timeline": "short_term",
                        "countries": ["USA", "Global"],
                        "actors": ["US Treasury", "Federal Reserve", "Ratings Agencies"],
                        "uncertainty_factors": ["Technical default duration", "Social security impact"]
                    },
                    "sectors": [
                        {"sector_name": "Financials", "etf_ticker": "XLF", "impact_direction": "bearish", "impact_magnitude": 0.88, "reasoning": "Counterparty risk and collateral instability in repo markets."},
                        {"sector_name": "Gold / Precious Metals", "etf_ticker": "GLD", "impact_direction": "bullish", "impact_magnitude": 0.92, "reasoning": "Safe haven rotation as dollar credibility is questioned."},
                        {"sector_name": "Real Estate", "etf_ticker": "XLRE", "impact_direction": "bearish", "impact_magnitude": 0.55, "reasoning": "Spiking mortgage rates due to Treasury yield volatility."}
                    ],
                    "top_bullish": [
                        {"ticker": "GLD", "company": "SPDR Gold Trust", "relevance": 0.98, "sector": "Commodities", "reasoning": "Primary alternative to fiat currency during credit events."},
                        {"ticker": "BITO", "company": "Bitcoin Strategy ETF", "relevance": 0.70, "sector": "Crypto", "reasoning": "Digital gold narrative attracts speculative safe-haven flow."}
                    ],
                    "top_bearish": [
                        {"ticker": "JPM", "company": "JPMorgan Chase", "relevance": 0.85, "sector": "Financials", "reasoning": "Extreme exposure to Treasury collateral and payment systems."},
                        {"ticker": "SPY", "company": "S&P 500", "relevance": 0.90, "sector": "Macro", "reasoning": "Broad market re-pricing of risk-free rate."}
                    ],
                    "supply_chain_impacts": [
                        {
                            "node": "Federal Payment Systems",
                            "impact_severity": "critical",
                            "description": "Suspension of social security, military pay, and vendor contracts.",
                            "affected_companies": ["Lockheed Martin", "General Dynamics", "Humana"],
                            "estimated_disruption_days": 14,
                            "confidence": 0.85
                        }
                    ],
                    "analogies": [
                        {
                            "event_title": "2011 US Debt Ceiling Crisis",
                            "event_date": "2011-08-05",
                            "similarity_score": 0.95,
                            "key_similarities": ["Political brinkmanship", "S&P Downgrade"],
                            "key_differences": ["Higher interest rate environment today", "Polarized Congress"],
                            "return_5d": -6.5,
                            "return_30d": -4.2,
                            "volatility_change": 15.0
                        }
                    ],
                    "outcomes": [
                        {
                            "scenario_label": "Technical Default & Rebound",
                            "probability": 0.70,
                            "direction": "mixed",
                            "market_return_5d": -8.0,
                            "market_return_30d": 5.2,
                            "narrative": "Markets panic for 48-72 hours until a last-minute deal is struck.",
                            "key_catalysts": ["Fed emergency liquidity", "Legislative compromise"]
                        }
                    ],
                    "risk_factors": [
                        {"risk_factor": "Collateral Collapse", "severity": 0.88, "probability": 0.40, "impact_description": "Repos and derivatives face margin calls as Treasury value fluctuates."}
                    ],
                    "volatility_outlook": {
                        "expected_regime": "high_volatility",
                        "estimated_vol_expansion": 25.0,
                        "tail_risk_assessment": "Systemic threat to US dollar reserve status"
                    },
                    "report": {
                        "title": "Simulation: US Sovereign Credit Event",
                        "executive_summary": "A failure to raise the debt ceiling or a technical default would trigger a seismic shift in global finance. US Treasuries, the world's 'risk-free' asset, would face immediate liquidity premiums.",
                        "key_judgments": [
                            {"judgment": "US Dollar will weaken 5-10% against hard currencies.", "confidence": 0.75, "detail": "Flight to CHF, JPY, and Gold will be rapid."},
                            {"judgment": "Short-term Treasury yields will spike above 10%.", "confidence": 0.95, "detail": "Liquidity in bill markets will evaporate instantly."}
                        ],
                        "recommendations": [
                            "Move to ultra-short duration or cash-like instruments.",
                            "Overweight Gold and defensive commodities.",
                            "Short regional banks and leverage-heavy financials."
                        ],
                        "confidence_assessment": "High (well-understood historical mechanics)",
                        "disclaimers": ["Assumes no immediate Fed monetization of defaulted debt."]
                    }
                }

            # Scenario C: Russia / Ukraine / Europe
            if "russia" in q or "ukraine" in q or "energy" in q or "europe" in q:
                return {
                    "execution_time_ms": 1300,
                    "overall_confidence": 0.85,
                    "parsed_scenario": {
                        "event_type": "Energy War / Escalation",
                        "severity_estimate": 8.8,
                        "economic_scope": "Regional (Europe) / Energy",
                        "estimated_timeline": "short_term",
                        "countries": ["Russia", "Ukraine", "Germany", "Poland"],
                        "actors": ["Gazprom", "EU Commission", "NATO"],
                        "uncertainty_factors": ["Winter weather severity", "Infrastructure sabotage"]
                    },
                    "sectors": [
                        {"sector_name": "Energy (Gas)", "etf_ticker": "UNG", "impact_direction": "bullish", "impact_magnitude": 0.98, "reasoning": "Total cut-off of remaining pipeline flows to Europe."},
                        {"sector_name": "Industrials (EU)", "etf_ticker": "EWG", "impact_direction": "bearish", "impact_magnitude": 0.82, "reasoning": "Energy rationing leads to industrial production halts in Germany."},
                        {"sector_name": "Wheat / Agriculture", "etf_ticker": "WEAT", "impact_direction": "bullish", "impact_magnitude": 0.60, "reasoning": "Black Sea shipping lane closure impacts grain exports."}
                    ],
                    "top_bullish": [
                        {"ticker": "EQNR", "company": "Equinor", "relevance": 0.95, "sector": "Energy", "reasoning": "Primary alternative gas supplier to the European continent."},
                        {"ticker": "CHRY", "company": "Cheniere Energy", "relevance": 0.88, "sector": "Energy", "reasoning": "US LNG exporter benefiting from European demand shift."}
                    ],
                    "top_bearish": [
                        {"ticker": "BASFY", "company": "BASF", "relevance": 0.92, "sector": "Chemicals", "reasoning": "High energy-intensity production vulnerable to gas prices."},
                        {"ticker": "VWAGY", "company": "Volkswagen", "relevance": 0.75, "sector": "Auto", "reasoning": "Supply chain and energy cost pressure in home markets."}
                    ],
                    "supply_chain_impacts": [
                        {
                            "node": "Druzhba Pipeline",
                            "impact_severity": "critical",
                            "description": "Critical oil pipeline to Central Europe sabotaged or shut down.",
                            "affected_companies": ["PKN Orlen", "MOL Group"],
                            "estimated_disruption_days": 90,
                            "confidence": 0.88
                        }
                    ],
                    "analogies": [
                        {
                            "event_title": "2022 Nord Stream Sabotage",
                            "event_date": "2022-09-26",
                            "similarity_score": 0.90,
                            "key_similarities": ["Energy infrastructure targeting", "Irreversible escalation"],
                            "key_differences": ["Existing LNG storage levels", "Diversified supply routes"],
                            "return_5d": +8.5,
                            "return_30d": +4.2,
                            "volatility_change": 10.0
                        }
                    ],
                    "outcomes": [
                        {
                            "scenario_label": "Winter Energy Crisis",
                            "probability": 0.50,
                            "direction": "bearish",
                            "market_return_5d": -5.2,
                            "market_return_30d": -12.4,
                            "narrative": "EU undergoes mandatory energy rationing; industrial recession follows.",
                            "key_catalysts": ["Severe cold snap", "Further pipeline damage"]
                        }
                    ],
                    "risk_factors": [
                        {"risk_factor": "Social Unrest", "severity": 0.70, "probability": 0.55, "impact_description": "Protests against soaring utility costs in major EU cities."}
                    ],
                    "volatility_outlook": {
                        "expected_regime": "high_volatility",
                        "estimated_vol_expansion": 18.0,
                        "tail_risk_assessment": "EUR/USD parity threat"
                    },
                    "report": {
                        "title": "Simulation: Eurasian Energy Decoupling",
                        "executive_summary": "This scenario models the final stage of energy decoupling between Russia and Europe. The resulting price shock will force a structural shift in European industrial strategy.",
                        "key_judgments": [
                            {"judgment": "EU Gas prices will stabilize at 3x historical averages.", "confidence": 0.82, "detail": "Reliance on expensive spot-market LNG becomes the new normal."},
                            {"judgment": "Defense spending in EU will double by 2030.", "confidence": 0.90, "detail": "Eastern flank security becomes the top budgetary priority."}
                        ],
                        "recommendations": [
                            "Long US and Norwegian energy producers.",
                            "Avoid energy-intensive European industrials.",
                            "Hedge Euro currency exposure."
                        ],
                        "confidence_assessment": "High",
                        "disclaimers": ["Assumes no nuclear escalation."]
                    }
                }

            # Scenario D: Retail / Fashion / Consumer
            if "fashion" in q or "zara" in q or "tata" in q or "retail" in q:
                return {
                    "execution_time_ms": 980,
                    "overall_confidence": 0.88,
                    "parsed_scenario": {
                        "event_type": "Market Competition",
                        "severity_estimate": 4.5,
                        "economic_scope": "Sector-Specific",
                        "estimated_timeline": "medium_term",
                        "countries": ["India", "Spain", "Global"],
                        "actors": ["Tata Group", "Inditex (Zara)", "Reliance"],
                        "uncertainty_factors": ["Logistics speed", "Brand loyalty shift"]
                    },
                    "sectors": [
                        {"sector_name": "Consumer Discretionary", "etf_ticker": "XLY", "impact_direction": "bullish", "impact_magnitude": 0.45, "reasoning": "Increased competition and innovation in fast fashion."},
                        {"sector_name": "Retail", "etf_ticker": "XRT", "impact_direction": "mixed", "impact_magnitude": 0.30, "reasoning": "Market share battle between incumbents and new entrants."},
                        {"sector_name": "Textiles (India)", "etf_ticker": "INDY", "impact_direction": "bullish", "impact_magnitude": 0.65, "reasoning": "Local manufacturing boost for the new brand."}
                    ],
                    "top_bullish": [
                        {"ticker": "TATAELXSI", "company": "Tata Elxsi", "relevance": 0.75, "sector": "Technology/Design", "reasoning": "Potential design and tech partner for the new retail venture."},
                        {"ticker": "RELANCE", "company": "Reliance Industries", "relevance": 0.60, "sector": "Retail", "reasoning": "Broader sector growth and investment in retail infrastructure."}
                    ],
                    "top_bearish": [
                        {"ticker": "ITX", "company": "Inditex (Zara)", "relevance": 0.92, "sector": "Retail", "reasoning": "Direct threat to market dominance and margin compression."},
                        {"ticker": "HNNMY", "company": "H&M", "relevance": 0.68, "sector": "Retail", "reasoning": "Secondary impact from increased price competition."}
                    ],
                    "supply_chain_impacts": [
                        {
                            "node": "South Asian Textile Hubs",
                            "impact_severity": "moderate",
                            "description": "Shift in factory orders from European brands to the new domestic player.",
                            "affected_companies": ["Trent Ltd", "Aditya Birla Fashion"],
                            "estimated_disruption_days": 10,
                            "confidence": 0.82
                        }
                    ],
                    "analogies": [
                        {
                            "event_title": "Launch of Reliance Trends",
                            "event_date": "2006-11-01",
                            "similarity_score": 0.82,
                            "key_similarities": ["Domestic giant entering retail", "Organized retail disruption"],
                            "key_differences": ["Digital commerce scale today", "Speed of global fashion cycles"],
                            "return_5d": 2.4,
                            "return_30d": 5.8,
                            "volatility_change": -1.2
                        }
                    ],
                    "outcomes": [
                        {
                            "scenario_label": "Successful Market Disruption",
                            "probability": 0.65,
                            "direction": "bullish",
                            "market_return_5d": 1.2,
                            "market_return_30d": 4.5,
                            "narrative": "The new brand captures significant market share in emerging markets.",
                            "key_catalysts": ["Pricing strategy", "Supply chain velocity"]
                        }
                    ],
                    "risk_factors": [
                        {"risk_factor": "Brand Saturation", "severity": 0.40, "probability": 0.30, "impact_description": "Over-saturation of fast fashion leads to diminishing returns."}
                    ],
                    "volatility_outlook": {
                        "expected_regime": "normal",
                        "estimated_vol_expansion": 5.2,
                        "tail_risk_assessment": "Low systemic risk"
                    },
                    "report": {
                        "title": f"Analysis: {query_val[:40]}...",
                        "executive_summary": f"The entry of a major player like Tata into the extremely fast fashion space would significantly disrupt the current retail hierarchy. This move leverages India's manufacturing base to challenge incumbents like Zara.",
                        "key_judgments": [
                            {"judgment": "Inditex margins will compress by 200bps.", "confidence": 0.78, "detail": "Competition in mid-tier pricing will be intense."},
                            {"judgment": "Logistics will be the primary battleground.", "confidence": 0.92, "detail": "Zara's 'just-in-time' model is the benchmark to beat."}
                        ],
                        "recommendations": [
                            "Monitor Trent Ltd (Tata Retail) for early performance signals.",
                            "Avoid direct exposure to European fast-fashion incumbents.",
                            "Watch for logistics and textile infrastructure investment plays."
                        ],
                        "confidence_assessment": "High",
                        "disclaimers": ["Assumes successful execution of the supply chain model."]
                    }
                }

            # Default Case: Dynamic Fallback
            return {
                "execution_time_ms": 1240,
                "overall_confidence": 0.82,
                "parsed_scenario": {
                    "event_type": "Generic Geopolitical Event",
                    "severity_estimate": 6.5,
                    "economic_scope": "Broad Market",
                    "estimated_timeline": "medium_term",
                    "countries": ["USA", "Global"],
                    "actors": ["Market Participants", "Institutional Investors"],
                    "uncertainty_factors": ["Macro sentiment", "Policy response"]
                },
                "sectors": [
                    {"sector_name": "Financials", "etf_ticker": "XLF", "impact_direction": "mixed", "impact_magnitude": 0.45, "reasoning": "Uncertainty creates volatility in payment and trading volumes."},
                    {"sector_name": "Consumer", "etf_ticker": "XLY", "impact_direction": "bearish", "impact_magnitude": 0.35, "reasoning": "Sentiment shift impacts discretionary spending."}
                ],
                "top_bullish": [],
                "top_bearish": [],
                "supply_chain_impacts": [],
                "analogies": [],
                "outcomes": [
                    {
                        "scenario_label": "Status Quo Maintenance",
                        "probability": 0.70,
                        "direction": "neutral",
                        "market_return_5d": -0.2,
                        "market_return_30d": 1.5,
                        "narrative": "The event is absorbed by the market without major structural changes.",
                        "key_catalysts": ["Central bank policy", "Economic data releases"]
                    }
                ],
                "risk_factors": [
                    {"risk_factor": "Policy Uncertainty", "severity": 0.55, "probability": 0.60, "impact_description": "Delayed regulatory or governmental response."}
                ],
                "volatility_outlook": {
                    "expected_regime": "normal",
                    "estimated_vol_expansion": 8.5,
                    "tail_risk_assessment": "Moderate volatility spike expected"
                },
                "report": {
                    "title": f"Custom Analysis: {query_val[:50]}",
                    "executive_summary": f"Our model has analyzed the scenario: '{query_val}'. We project a moderate impact on market sentiment with sectoral shifts favoring defensive positions.",
                    "key_judgments": [
                        {"judgment": "Short-term volatility will increase by 15%.", "confidence": 0.85, "detail": "Options markets are currently under-pricing this specific risk."},
                        {"judgment": "Safe-haven flows will accelerate.", "confidence": 0.72, "detail": "Gold and Treasury demand shows early signs of correlation with this scenario."}
                    ],
                    "recommendations": [
                        "Maintain a balanced portfolio with increased cash reserves.",
                        "Monitor VIX levels for hedging opportunities.",
                        "Await further clarity on geopolitical escalations."
                    ],
                    "confidence_assessment": "Moderate",
                    "disclaimers": ["Preliminary analysis based on historical correlations."]
                }
            }

        return {"status": "success", "message": "Mock data generated for " + path, "items": []}

    async def health_check(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/health")

    async def get_geopol_events(self, **params) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/geopol/events", params=params)

    async def get_geopol_summary(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/v1/geopol/summary")

    async def analyze_sentiment(self, query: str, source: str = "reddit") -> Dict[str, Any]:
        return await self._request(
            "GET", "/api/v1/sentiment/analysis",
            params={"query": query, "source": source},
        )

    async def get_sentiment_trends(self, ticker: Optional[str] = None, sector: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        params = {"hours": hours}
        if ticker:
            params["ticker"] = ticker
        if sector:
            params["sector"] = sector
        return await self._request("GET", "/api/v1/sentiment/trends", params=params)

    async def get_market_data(self, ticker: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        return await self._request(
            "GET", f"/api/v1/markets/data/{ticker}",
            params={"start_date": start_date, "end_date": end_date},
        )

    async def assess_impact(self, event_id: str) -> Dict[str, Any]:
        return await self._request(
            "GET", "/api/v1/markets/impact",
            params={"event_id": event_id},
        )

    async def query_rag(self, query: str, collection: str = "geopol_events", top_k: int = 5) -> Dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/rag/query",
            json={"query": query, "collection": collection, "top_k": top_k},
        )

    async def list_agents(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/api/v1/agents")

    async def run_agent(self, agent_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request(
            "POST", f"/api/v1/agents/run/{agent_id}",
            json={"input_data": input_data},
        )

    async def orchestrate(self, agents: List[str], input_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/agents/orchestrate",
            json={"agents": agents, "input_data": input_data, "workflow_type": "sequential"},
        )

    async def generate_report(self, title: str, sections: Dict[str, str], format: str = "markdown") -> Dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/reports/generate",
            json={"title": title, "sections": list(sections.keys()), "format": format, "parameters": sections},
        )

    async def list_reports(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        return await self._request(
            "GET", "/api/v1/reports",
            params={"page": page, "page_size": page_size},
        )

    async def create_scenario(self, name: str, description: str, parameters: List[Dict] = None) -> Dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/simulation/scenarios",
            json={"name": name, "description": description, "parameters": parameters or []},
        )

    async def run_scenario(self, scenario_id: str) -> Dict[str, Any]:
        return await self._request(
            "POST", f"/api/v1/simulation/scenarios/{scenario_id}/run",
        )

    async def run_simulation(self, query: str) -> Dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/simulation/run",
            json={"query": query},
        )

    async def generate_prediction(
        self, query: str, tickers: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None, location: str = "",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"query": query}
        if tickers:
            payload["tickers"] = tickers
        if sectors:
            payload["sectors"] = sectors
        if location:
            payload["location"] = location
        return await self._request("POST", "/api/v1/prediction", json=payload)

    async def explain_prediction(self, ticker: str, query: str) -> Dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/prediction/explain",
            json={"query": query, "ticker": ticker},
        )

    async def run_workflow(self, query: str, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"query": query}
        if tickers:
            payload["tickers"] = tickers
        return await self._request("POST", "/api/v1/agents/workflow", json=payload)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


api_client = ApiClient()
