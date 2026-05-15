"""PDF generation for institutional-grade geopolitical intelligence briefings."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm, cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    ListFlowable, ListItem,
)
from reportlab.platypus.flowables import HRFlowable

from app.logging_config import get_logger
from app.services.report.chart_generator import ReportChartGenerator

logger = get_logger(__name__)

REPORT_DIR = Path("data/reports/pdf")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

PRIMARY = colors.HexColor("#1a5276")
SECONDARY = colors.HexColor("#2e86c1")
DARK_TEXT = colors.HexColor("#2c3e50")
LIGHT_BG = colors.HexColor("#f8f9fa")
BULLISH_GREEN = colors.HexColor("#2ecc71")
BEARISH_RED = colors.HexColor("#e74c3c")
NEUTRAL_GRAY = colors.HexColor("#95a5a6")
ACCENT_GOLD = colors.HexColor("#f39c12")


class IntelligencePDFReport:
    """Generates institutional-grade PDF intelligence briefings."""

    def __init__(self) -> None:
        self.charts = ReportChartGenerator()
        self._styles = self._build_styles()

    def _build_styles(self) -> Dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(
            "CoverTitle", parent=styles["Title"],
            fontSize=28, leading=34, textColor=colors.white,
            alignment=TA_CENTER, spaceAfter=12, fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            "CoverSubtitle", parent=styles["Normal"],
            fontSize=14, leading=18, textColor=colors.white,
            alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica",
        ))
        styles.add(ParagraphStyle(
            "SectionHeader", parent=styles["Heading1"],
            fontSize=16, leading=20, textColor=PRIMARY,
            spaceBefore=20, spaceAfter=12, fontName="Helvetica-Bold",
            borderWidth=0, borderPadding=0,
        ))
        styles.add(ParagraphStyle(
            "SubHeader", parent=styles["Heading2"],
            fontSize=12, leading=16, textColor=SECONDARY,
            spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            "BodyText2", parent=styles["Normal"],
            fontSize=9.5, leading=14, textColor=DARK_TEXT,
            spaceBefore=4, spaceAfter=6, fontName="Helvetica",
            alignment=TA_JUSTIFY,
        ))
        styles.add(ParagraphStyle(
            "BodyBold", parent=styles["Normal"],
            fontSize=9.5, leading=14, textColor=DARK_TEXT,
            spaceBefore=2, spaceAfter=2, fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            "SmallText", parent=styles["Normal"],
            fontSize=8, leading=10, textColor=NEUTRAL_GRAY,
            spaceBefore=2, spaceAfter=2, fontName="Helvetica",
        ))
        styles.add(ParagraphStyle(
            "DisclaimerText", parent=styles["Normal"],
            fontSize=7, leading=9, textColor=NEUTRAL_GRAY,
            spaceBefore=2, spaceAfter=2, fontName="Helvetica-Oblique",
        ))
        styles.add(ParagraphStyle(
            "MetricBig", parent=styles["Normal"],
            fontSize=18, leading=22, textColor=PRIMARY,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            "MetricLabel", parent=styles["Normal"],
            fontSize=8, leading=10, textColor=NEUTRAL_GRAY,
            alignment=TA_CENTER, fontName="Helvetica",
        ))
        styles.add(ParagraphStyle(
            "FooterStyle", parent=styles["Normal"],
            fontSize=7, leading=9, textColor=NEUTRAL_GRAY,
            alignment=TA_CENTER, fontName="Helvetica",
        ))
        return styles

    def generate(
        self,
        data: Dict[str, Any],
    ) -> str:
        report_id = f"brief-{uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc)
        filename = f"{report_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = REPORT_DIR / filename

        doc = BaseDocTemplate(
            str(filepath),
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.85 * inch,
            title=data.get("title", "Geopolitical Intelligence Brief"),
            author="GeoMarketGPT AI System",
            subject="Geopolitical Market Intelligence",
        )

        frame_normal = Frame(
            doc.leftMargin, doc.bottomMargin,
            doc.width, doc.height,
            id="normal",
        )
        frame_cover = Frame(0, 0, letter[0], letter[1], id="cover")

        def cover_bg(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(PRIMARY)
            canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#154360"))
            canvas.rect(0, letter[1] * 0.7, letter[0], letter[1] * 0.3, fill=1, stroke=0)
            canvas.restoreState()

        def normal_header_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(NEUTRAL_GRAY)
            canvas.drawString(doc.leftMargin, doc.height + doc.topMargin - 12,
                              "GeoMarketGPT | Geopolitical Intelligence Brief")
            canvas.drawRightString(doc.width + doc.leftMargin, doc.height + doc.topMargin - 12,
                                   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
            canvas.setStrokeColor(PRIMARY)
            canvas.setLineWidth(0.5)
            canvas.line(doc.leftMargin, doc.height + doc.topMargin - 14,
                        doc.width + doc.leftMargin, doc.height + doc.topMargin - 14)
            canvas.setFont("Helvetica", 7)
            canvas.drawString(doc.leftMargin, 0.5 * inch,
                              f"CONFIDENTIAL | Page {doc.page}")
            canvas.drawRightString(doc.width + doc.leftMargin, 0.5 * inch,
                                   "Generated by GeoMarketGPT AI")
            canvas.restoreState()

        doc.addPageTemplates([
            PageTemplate(id="cover", frames=frame_cover, onPage=cover_bg),
            PageTemplate(id="normal", frames=frame_normal, onPage=normal_header_footer),
        ])

        story: List = []
        self._build_cover(story, data, timestamp)
        story.append(NextPageTemplate("normal"))
        story.append(PageBreak())
        self._build_executive_summary(story, data)
        story.append(PageBreak())
        self._build_top_events(story, data)
        story.append(PageBreak())
        self._build_sector_analysis(story, data)
        story.append(PageBreak())
        self._build_stock_predictions(story, data)
        story.append(PageBreak())
        self._build_historical_analogies(story, data)
        story.append(PageBreak())
        self._build_risk_assessment(story, data)
        story.append(PageBreak())
        self._build_outcome_scenarios(story, data)
        story.append(Spacer(1, 0.5 * inch))
        self._build_disclaimers(story)

        doc.build(story)
        logger.info("PDF report generated: %s", filepath)
        return str(filepath)

    def _build_cover(self, story: List, data: Dict[str, Any], ts: datetime) -> None:
        story.append(Spacer(1, 2.5 * inch))
        story.append(Paragraph("GEOPOLITICAL", self._styles["CoverSubtitle"]))
        story.append(Paragraph("INTELLIGENCE BRIEF", self._styles["CoverTitle"]))
        story.append(Spacer(1, 0.3 * inch))
        story.append(HRFlowable(width="60%", thickness=1, color=ACCENT_GOLD,
                                 spaceAfter=12, spaceBefore=6, hAlign="CENTER"))
        story.append(Paragraph(ts.strftime("%B %d, %Y at %H:%M UTC"), self._styles["CoverSubtitle"]))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(f"Report: {data.get('report_id', 'auto')}", self._styles["CoverSubtitle"]))
        story.append(Spacer(1, 2 * inch))

        metrics = [
            ("Severity", f"{data.get('severity_estimate', 0):.1f}/10"),
            ("Events Tracked", str(data.get("event_count", 0))),
            ("Sectors Analyzed", str(len(data.get("sectors", [])))),
            ("Confidence", f"{data.get('overall_confidence', 0):.0%}"),
        ]
        t_data = [[Paragraph(m, self._styles["MetricBig"]),
                   Paragraph(v, self._styles["MetricBig"])] for m, v in metrics]
        t = Table(t_data, colWidths=[1.5 * inch, 1.5 * inch])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(data.get("title", "Market Intelligence Brief"), self._styles["CoverSubtitle"]))

    def _build_executive_summary(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("EXECUTIVE SUMMARY", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        report = data.get("report", {})
        summary = report.get("executive_summary", data.get("executive_summary", ""))
        story.append(Paragraph(summary, self._styles["BodyText2"]))

        if data.get("key_judgments"):
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph("Key Judgments", self._styles["SubHeader"]))
            for kj in data["key_judgments"]:
                j = kj.get("judgment", "")
                conf = kj.get("confidence", 0)
                detail = kj.get("detail", "")
                story.append(Paragraph(
                    f"<b>{j}</b> (Confidence: {conf:.0%})",
                    self._styles["BodyBold"],
                ))
                story.append(Paragraph(detail, self._styles["BodyText2"]))

        recommendations = report.get("recommendations", data.get("recommendations", []))
        if recommendations:
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph("Recommendations", self._styles["SubHeader"]))
            for r in recommendations[:6]:
                parts = r.split(":", 1)
                if len(parts) > 1:
                    story.append(Paragraph(f"<b>{parts[0]}:</b>{parts[1]}", self._styles["BodyText2"]))
                else:
                    story.append(Paragraph(r, self._styles["BodyText2"]))

    def _build_top_events(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("TOP GEOPOLITICAL EVENTS", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        events = data.get("events", data.get("top_events", []))
        if events:
            for i, evt in enumerate(events[:8]):
                title = evt.get("title", evt.get("event_title", f"Event {i+1}"))
                sev = evt.get("severity", evt.get("severity_estimate", 0))
                etype = evt.get("event_type", "geopolitical")
                loc = evt.get("location", "Unknown")
                desc = evt.get("description", evt.get("event_description", ""))
                actors = evt.get("actors", [])
                source = evt.get("source", "GDELT")

                emoji = "🔴" if sev >= 8 else "🟠" if sev >= 6 else "🟡" if sev >= 4 else "🟢"
                story.append(Paragraph(
                    f"{emoji} <b>{title}</b> &mdash; Severity: {sev:.1f}/10",
                    self._styles["SubHeader"],
                ))
                story.append(Paragraph(
                    f"<b>Type:</b> {etype} | <b>Location:</b> {loc} | <b>Source:</b> {source}",
                    self._styles["SmallText"],
                ))
                if desc:
                    story.append(Paragraph(desc[:250], self._styles["BodyText2"]))
                if actors:
                    story.append(Paragraph(
                        f"<b>Key Actors:</b> {', '.join(actors[:5])}",
                        self._styles["SmallText"],
                    ))
        else:
            story.append(Paragraph("No significant events detected in the current window.", self._styles["BodyText2"]))

        overview = data.get("scenario_context", "")
        if overview:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(overview[:400], self._styles["BodyText2"]))

    def _build_sector_analysis(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("SECTOR IMPACT ANALYSIS", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        sectors = data.get("sectors", [])
        if sectors:
            chart_path = self.charts.sector_impact_bar(sectors)
            if Path(chart_path).exists():
                story.append(Image(chart_path, width=6.5 * inch, height=3.2 * inch))
                story.append(Spacer(1, 0.15 * inch))

            t_data = [["Sector", "ETF", "Direction", "Magnitude", "Confidence", "Reasoning"]]
            for s in sectors[:7]:
                t_data.append([
                    s.get("sector_name", "")[:18],
                    s.get("etf_ticker", ""),
                    s.get("impact_direction", "").upper(),
                    f"{s.get('impact_magnitude', 0):.2f}",
                    f"{s.get('confidence', 0):.0%}",
                    s.get("reasoning", "")[:35],
                ])

            col_widths = [1.3*inch, 0.5*inch, 0.7*inch, 0.7*inch, 0.7*inch, 2.3*inch]
            t = Table(t_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("No sector impact data available.", self._styles["BodyText2"]))

        supply_chain = data.get("supply_chain_impacts", [])
        if supply_chain:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Supply Chain Disruption Assessment", self._styles["SubHeader"]))
            t_data = [["Node", "Severity", "Disruption", "Confidence"]]
            for sc in supply_chain[:5]:
                t_data.append([
                    sc.get("node", "")[:25],
                    sc.get("impact_severity", "").upper(),
                    f"{sc.get('estimated_disruption_days', 0)} days",
                    f"{sc.get('confidence', 0):.0%}",
                ])
            t = Table(t_data, colWidths=[2.5*inch, 1.2*inch, 1.2*inch, 1.2*inch], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ]))
            story.append(t)

    def _build_stock_predictions(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("STOCK RECOMMENDATIONS", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        bullish = data.get("top_bullish", [])
        bearish = data.get("top_bearish", [])

        if bullish or bearish:
            if bullish:
                story.append(Paragraph("Bullish Picks", self._styles["SubHeader"]))
                t_data = [["Ticker", "Sector", "Relevance", "Direction", "Reasoning"]]
                for s in bullish[:5]:
                    t_data.append([
                        s.get("ticker", ""),
                        s.get("sector", "")[:15],
                        f"{s.get('relevance', 0):.2f}",
                        s.get("direction", "").upper(),
                        s.get("reasoning", "")[:40],
                    ])
                t = Table(t_data, colWidths=[0.7*inch, 1.2*inch, 0.7*inch, 0.7*inch, 2.8*inch], repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), BULLISH_GREEN),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ]))
                story.append(t)

            if bearish:
                story.append(Spacer(1, 0.15 * inch))
                story.append(Paragraph("Bearish Picks", self._styles["SubHeader"]))
                t_data = [["Ticker", "Sector", "Relevance", "Direction", "Reasoning"]]
                for s in bearish[:5]:
                    t_data.append([
                        s.get("ticker", ""),
                        s.get("sector", "")[:15],
                        f"{s.get('relevance', 0):.2f}",
                        s.get("direction", "").upper(),
                        s.get("reasoning", "")[:40],
                    ])
                t = Table(t_data, colWidths=[0.7*inch, 1.2*inch, 0.7*inch, 0.7*inch, 2.8*inch], repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), BEARISH_RED),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ]))
                story.append(t)
        else:
            story.append(Paragraph("No stock recommendations generated in this cycle.", self._styles["BodyText2"]))

    def _build_historical_analogies(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("HISTORICAL ANALOGUES", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        analogies = data.get("analogies", [])
        if analogies:
            chart_path = self.charts.historical_analogy_table_chart(analogies)
            if Path(chart_path).exists():
                story.append(Image(chart_path, width=6.5 * inch, height=min(4, len(analogies) * 0.5) * inch))
                story.append(Spacer(1, 0.1 * inch))

            for a in analogies[:4]:
                story.append(Paragraph(
                    f"<b>{a.get('event_title', 'Unknown')}</b> ({a.get('event_date', '')}) "
                    f"&mdash; Similarity: {a.get('similarity_score', 0):.0%}",
                    self._styles["BodyBold"],
                ))
                sims = a.get("key_similarities", [])
                diffs = a.get("key_differences", [])
                impact = a.get("market_impact_description", "")
                if sims:
                    story.append(Paragraph(f"<b>Similarities:</b> {', '.join(sims[:3])}", self._styles["SmallText"]))
                if diffs:
                    story.append(Paragraph(f"<b>Differences:</b> {', '.join(diffs[:3])}", self._styles["SmallText"]))
                if impact:
                    story.append(Paragraph(f"<b>Market Impact:</b> {impact[:150]}", self._styles["SmallText"]))
        else:
            story.append(Paragraph("No close historical analogues identified.", self._styles["BodyText2"]))

    def _build_risk_assessment(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("RISK & VOLATILITY ASSESSMENT", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        volatility = data.get("volatility_outlook", {})
        if volatility:
            vix_est = volatility.get("estimated_vol_expansion", 15)
            regime = volatility.get("expected_regime", "normal")

            chart_path = self.charts.volatility_gauge(vix_est, regime)
            if Path(chart_path).exists():
                story.append(Image(chart_path, width=5 * inch, height=2.2 * inch))
                story.append(Spacer(1, 0.1 * inch))

            metrics_data = [[
                Paragraph(f"<b>Expected Regime</b><br/>{regime.upper()}", self._styles["SmallText"]),
                Paragraph(f"<b>VIX Estimate</b><br/>{vix_est:.0f}", self._styles["SmallText"]),
                Paragraph(f"<b>Tail Risk</b><br/>{volatility.get('tail_risk_assessment', 'N/A')[:40]}", self._styles["SmallText"]),
                Paragraph(f"<b>VIX Implication</b><br/>{volatility.get('vix_implication', '')[:50]}", self._styles["SmallText"]),
            ]]
            t = Table(metrics_data, colWidths=[1.5*inch, 1.2*inch, 1.8*inch, 1.8*inch])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)

        risk_factors = data.get("risk_factors", [])
        if risk_factors:
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph("Key Risk Factors", self._styles["SubHeader"]))
            t_data = [["Risk Factor", "Severity", "Probability", "Impact"]]
            for rf in sorted(risk_factors, key=lambda r: r.get("severity", 0), reverse=True)[:6]:
                t_data.append([
                    rf.get("risk_factor", "")[:30],
                    f"{rf.get('severity', 0):.2f}",
                    f"{rf.get('probability', 0):.0%}",
                    rf.get("impact_description", "")[:50],
                ])
            t = Table(t_data, colWidths=[1.8*inch, 0.7*inch, 0.7*inch, 2.8*inch], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BEARISH_RED),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ]))
            story.append(t)

    def _build_outcome_scenarios(self, story: List, data: Dict[str, Any]) -> None:
        story.append(Paragraph("OUTCOME SCENARIOS", self._styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=12))

        outcomes = data.get("outcomes", [])
        if outcomes:
            chart_path = self.charts.outcome_probability_pie(outcomes)
            if Path(chart_path).exists():
                story.append(Image(chart_path, width=4.5 * inch, height=4.5 * inch))
                story.append(Spacer(1, 0.1 * inch))

            t_data = [["Scenario", "Prob.", "Direction", "5d Return", "30d Return"]]
            for o in sorted(outcomes, key=lambda x: x.get("probability", 0), reverse=True):
                t_data.append([
                    o.get("scenario_label", "")[:25],
                    f"{o.get('probability', 0):.0%}",
                    o.get("direction", "").upper(),
                    f"{o.get('market_return_5d', 0):+.1f}%",
                    f"{o.get('market_return_30d', 0):+.1f}%",
                ])
            t = Table(t_data, colWidths=[2.2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ]))
            story.append(t)

            for o in sorted(outcomes, key=lambda x: x.get("probability", 0), reverse=True):
                story.append(Spacer(1, 6))
                story.append(Paragraph(
                    f"<b>{o.get('scenario_label', '')}</b> ({o.get('probability', 0):.0%}) &mdash; "
                    f"<font color='{'green' if o.get('direction') == 'bullish' else 'red' if o.get('direction') == 'bearish' else 'gray'}'>"
                    f"{o.get('direction', '').upper()}</font>",
                    self._styles["BodyBold"],
                ))
                story.append(Paragraph(o.get("narrative", "")[:200], self._styles["BodyText2"]))
                cats = o.get("key_catalysts", [])
                if cats:
                    story.append(Paragraph(f"<b>Catalysts:</b> {', '.join(cats[:4])}", self._styles["SmallText"]))
        else:
            story.append(Paragraph("No outcome scenarios generated.", self._styles["BodyText2"]))

    def _build_disclaimers(self, story: List) -> None:
        story.append(Spacer(1, 0.3 * inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=NEUTRAL_GRAY, spaceAfter=8))
        story.append(Paragraph("DISCLAIMERS", self._styles["SectionHeader"]))
        disclaimers = [
            "This report is generated by an AI system (GeoMarketGPT) for informational purposes only.",
            "All scenarios are hypothetical and do not constitute investment advice.",
            "Past performance of historical analogues does not guarantee future results.",
            "Actual market outcomes depend on numerous factors not captured in this analysis.",
            "Consult a qualified financial advisor before making investment decisions.",
        ]
        for d in disclaimers:
            story.append(Paragraph(d, self._styles["DisclaimerText"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(
            f"Report generated by GeoMarketGPT AI | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            self._styles["FooterStyle"],
        ))
