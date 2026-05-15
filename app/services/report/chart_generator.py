"""Chart generation for institutional-grade PDF reports using matplotlib."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from app.logging_config import get_logger

logger = get_logger(__name__)

CHART_DIR = Path("data/reports/charts")
CHART_DIR.mkdir(parents=True, exist_ok=True)

COLORS = {
    "bullish": "#2ecc71",
    "bearish": "#e74c3c",
    "neutral": "#95a5a6",
    "mixed": "#f39c12",
    "primary": "#1a5276",
    "secondary": "#2e86c1",
    "grid": "#d5dbdb",
    "text": "#2c3e50",
}


class ReportChartGenerator:
    """Generates publication-quality charts for institutional intelligence briefings."""

    def __init__(self, dpi: int = 150, figsize: Tuple[int, int] = (10, 5)) -> None:
        self.dpi = dpi
        self.figsize = figsize
        self._configure_style()

    def _configure_style(self) -> None:
        plt.rcParams.update({
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "axes.facecolor": "#fafafa",
            "axes.edgecolor": COLORS["grid"],
            "axes.grid": True,
            "grid.color": COLORS["grid"],
            "grid.alpha": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.color": COLORS["text"],
            "axes.labelcolor": COLORS["text"],
            "xtick.color": COLORS["text"],
            "ytick.color": COLORS["text"],
            "figure.facecolor": "white",
        })

    def sector_impact_bar(
        self,
        sectors: List[Dict[str, Any]],
        title: str = "Sector Impact Assessment",
    ) -> str:
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        names = [s.get("sector_name", s.get("name", ""))[:15] for s in sectors]
        magnitudes = [s.get("impact_magnitude", s.get("magnitude", 0)) for s in sectors]
        directions = [s.get("impact_direction", s.get("direction", "neutral")) for s in sectors]

        colors = [COLORS.get(d, COLORS["neutral"]) for d in directions]
        bars = ax.barh(names, magnitudes, color=colors, edgecolor="white", linewidth=0.5, height=0.6)

        for bar, mag in zip(bars, magnitudes):
            ax.text(
                bar.get_width() + 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{mag:.2f}",
                va="center", fontsize=8, color=COLORS["text"],
            )

        ax.set_xlim(0, max(magnitudes) * 1.2 if magnitudes else 1.0)
        ax.set_xlabel("Impact Magnitude", fontsize=9)
        ax.set_title(title, fontsize=13, fontweight="bold", color=COLORS["primary"], pad=15)
        ax.tick_params(axis="y", labelsize=9)
        ax.tick_params(axis="x", labelsize=8)

        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, facecolor=COLORS["bullish"], label="Bullish"),
            plt.Rectangle((0, 0), 1, 1, facecolor=COLORS["bearish"], label="Bearish"),
            plt.Rectangle((0, 0), 1, 1, facecolor=COLORS["neutral"], label="Neutral"),
        ]
        ax.legend(handles=legend_elements, loc="lower right", fontsize=8, framealpha=0.9)

        fig.tight_layout()
        path = self._save_chart("sector_impact", fig)
        plt.close(fig)
        return str(path)

    def return_comparison_chart(
        self,
        items: List[Dict[str, Any]],
        title: str = "Return Comparison (5d vs 30d)",
    ) -> str:
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        labels = [i.get("label", i.get("name", ""))[:12] for i in items]
        ret_5d = [i.get("return_5d", 0) for i in items]
        ret_30d = [i.get("return_30d", 0) for i in items]

        x = np.arange(len(labels))
        width = 0.35

        bars1 = ax.bar(x - width / 2, ret_5d, width, label="5d Return", color=COLORS["secondary"], edgecolor="white")
        bars2 = ax.bar(x + width / 2, ret_30d, width, label="30d Return", color=COLORS["primary"], edgecolor="white")

        ax.axhline(y=0, color="black", linewidth=0.5)
        ax.set_ylabel("Return (%)", fontsize=9)
        ax.set_title(title, fontsize=13, fontweight="bold", color=COLORS["primary"], pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.legend(fontsize=9, framealpha=0.9)
        ax.tick_params(axis="y", labelsize=8)

        for bar in bars1:
            h = bar.get_height()
            if h != 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + (0.3 if h >= 0 else -0.8),
                        f"{h:+.1f}%", ha="center", fontsize=7, color=COLORS["text"])
        for bar in bars2:
            h = bar.get_height()
            if h != 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + (0.3 if h >= 0 else -0.8),
                        f"{h:+.1f}%", ha="center", fontsize=7, color=COLORS["text"])

        fig.tight_layout()
        path = self._save_chart("return_comparison", fig)
        plt.close(fig)
        return str(path)

    def volatility_gauge(
        self,
        vix_estimate: float,
        regime: str,
        title: str = "Volatility Regime",
    ) -> str:
        fig, ax = plt.subplots(figsize=(6, 3), dpi=self.dpi)

        categories = ["Low", "Moderate", "Elevated", "High", "Crisis"]
        values = [10, 18, 28, 38, 50]
        colors_d = {"low": "#2ecc71", "moderate": "#f1c40f", "elevated": "#e67e22",
                     "high": "#e74c3c", "crisis": "#8e44ad"}

        bar_color = colors_d.get(regime.lower(), COLORS["neutral"])
        bar_height = 0.4
        ax.barh(0, vix_estimate, bar_height, color=bar_color, edgecolor="black", linewidth=1.5, alpha=0.8)
        ax.barh(0, 60, bar_height, color="lightgray", edgecolor="gray", linewidth=0.5, alpha=0.3, zorder=0)

        ax.set_xlim(0, 60)
        ax.set_yticks([])
        ax.set_title(f"{title}: {regime.upper()}", fontsize=13, fontweight="bold", color=COLORS["primary"], pad=15)
        ax.set_xlabel("VIX Level", fontsize=9)
        ax.tick_params(axis="x", labelsize=8)

        for i, (cat, val) in enumerate(zip(categories, values)):
            ax.axvline(x=val, color="gray", linewidth=0.3, linestyle="--", alpha=0.5)
            ax.text(val, -0.4, cat, ha="center", fontsize=7, color="gray", rotation=30)

        ax.text(vix_estimate + 1, 0, f"Est. VIX: {vix_estimate:.0f}",
                va="center", fontsize=10, fontweight="bold", color=bar_color)

        fig.tight_layout()
        path = self._save_chart("volatility_gauge", fig)
        plt.close(fig)
        return str(path)

    def confidence_waterfall(
        self,
        signals: Dict[str, float],
        title: str = "Signal Contribution Breakdown",
    ) -> str:
        fig, ax = plt.subplots(figsize=(8, 4), dpi=self.dpi)

        labels = list(signals.keys())
        values = list(signals.values())
        x = np.arange(len(labels))

        colors = [COLORS["bullish"] if v >= 0 else COLORS["bearish"] for v in values]
        bars = ax.bar(x, values, color=colors, edgecolor="white", linewidth=0.5, width=0.5)

        ax.axhline(y=0, color="black", linewidth=0.5)
        ax.set_ylabel("Contribution Score", fontsize=9)
        ax.set_title(title, fontsize=13, fontweight="bold", color=COLORS["primary"], pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels([l.replace("_", " ").title() for l in labels], fontsize=8)
        ax.tick_params(axis="y", labelsize=8)

        for bar, val in zip(bars, values):
            y_pos = val + (0.02 if val >= 0 else -0.08)
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                    f"{val:+.3f}", ha="center", fontsize=8, fontweight="bold",
                    color=COLORS["bullish"] if val >= 0 else COLORS["bearish"])

        fig.tight_layout()
        path = self._save_chart("confidence_waterfall", fig)
        plt.close(fig)
        return str(path)

    def historical_analogy_table_chart(
        self,
        analogies: List[Dict[str, Any]],
        title: str = "Historical Analogues",
    ) -> str:
        fig, ax = plt.subplots(figsize=(10, max(3, len(analogies) * 0.6)), dpi=self.dpi)
        ax.axis("off")

        col_labels = ["Event", "Date", "Match", "SPY 5d", "SPY 30d", "VIX \u0394"]
        rows = []
        for a in analogies:
            rows.append([
                a.get("event_title", "")[:30],
                str(a.get("event_date", ""))[:10],
                f"{a.get('similarity_score', 0):.0%}",
                f"{a.get('return_5d', 0):+.1f}%",
                f"{a.get('return_30d', 0):+.1f}%",
                f"{a.get('volatility_change', 0):+.1f}",
            ])

        table = ax.table(
            cellText=rows, colLabels=col_labels,
            cellLoc="center", loc="center",
            colWidths=[0.25, 0.12, 0.08, 0.08, 0.08, 0.08],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)

        for j, col in enumerate(col_labels):
            cell = table[0, j]
            cell.set_facecolor(COLORS["primary"])
            cell.set_text_props(color="white", fontweight="bold", fontsize=8)

        for i in range(len(rows)):
            for j in range(len(col_labels)):
                cell = table[i + 1, j]
                cell.set_facecolor("#f8f9fa" if i % 2 == 0 else "white")
                cell.set_edgecolor("#dee2e6")

        ax.set_title(title, fontsize=13, fontweight="bold", color=COLORS["primary"], pad=20)

        fig.tight_layout()
        path = self._save_chart("historical_analogies", fig)
        plt.close(fig)
        return str(path)

    def outcome_probability_pie(
        self,
        outcomes: List[Dict[str, Any]],
        title: str = "Scenario Probabilities",
    ) -> str:
        fig, ax = plt.subplots(figsize=(6, 6), dpi=self.dpi)

        labels = [o.get("scenario_label", "")[:20] for o in outcomes]
        probs = [o.get("probability", 0) for o in outcomes]
        colors_out = [COLORS["bullish"], COLORS["primary"], COLORS["bearish"],
                      COLORS["mixed"], COLORS["neutral"]]

        wedges, texts, autotexts = ax.pie(
            probs, labels=None, autopct="%1.0f%%",
            colors=colors_out[:len(outcomes)],
            startangle=90, pctdistance=0.75,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for t in autotexts:
            t.set_fontsize(9)
            t.set_fontweight("bold")
            t.set_color("white")

        ax.legend(
            wedges, [f"{l} ({p:.0%})" for l, p in zip(labels, probs)],
            loc="center left", bbox_to_anchor=(1, 0.5),
            fontsize=8, framealpha=0.9,
        )
        ax.set_title(title, fontsize=13, fontweight="bold", color=COLORS["primary"], pad=15)

        fig.tight_layout()
        path = self._save_chart("outcome_probabilities", fig)
        plt.close(fig)
        return str(path)

    def _save_chart(self, name: str, fig: plt.Figure) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = CHART_DIR / filename
        fig.savefig(path, bbox_inches="tight", facecolor="white", edgecolor="none")
        logger.debug("Saved chart: %s", path)
        return path

    @staticmethod
    def cleanup_old_charts(max_age_hours: int = 2) -> int:
        removed = 0
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600
        for p in CHART_DIR.glob("*.png"):
            if p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
        if removed:
            logger.info("Cleaned up %d old chart files", removed)
        return removed
