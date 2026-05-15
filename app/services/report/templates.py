from __future__ import annotations

REPORT_TEMPLATES: dict[str, dict[str, str]] = {
    "daily_brief": {
        "title": "GeoMarketGPT Daily Brief",
        "header": "# GeoMarketGPT Daily Geopolitical Brief\n\n",
        "sections": [
            "Executive Summary",
            "Top Geopolitical Events",
            "Market Impact Assessment",
            "Sentiment Overview",
            "Key Risks",
            "Recommendations",
        ],
    },
    "event_impact": {
        "title": "Event Impact Analysis",
        "header": "# Event Impact Analysis\n\n",
        "sections": [
            "Event Summary",
            "Affected Regions",
            "Affected Sectors",
            "Market Impact",
            "Historical Comparison",
            "Scenario Analysis",
            "Recommendations",
        ],
    },
    "portfolio_risk": {
        "title": "Portfolio Risk Assessment",
        "header": "# Portfolio Geopolitical Risk Assessment\n\n",
        "sections": [
            "Portfolio Overview",
            "Geopolitical Risk Exposure",
            "Sector-Level Risk",
            "Holding-Level Impact",
            "Mitigation Strategies",
            "Recommended Actions",
        ],
    },
    "weekly_analysis": {
        "title": "Weekly Geopolitical Market Analysis",
        "header": "# Weekly Geopolitical Market Analysis\n\n",
        "sections": [
            "Weekly Summary",
            "Event Timeline",
            "Sector Performance",
            "Sentiment Trends",
            "Forecast",
            "Portfolio Recommendations",
        ],
    },
}
