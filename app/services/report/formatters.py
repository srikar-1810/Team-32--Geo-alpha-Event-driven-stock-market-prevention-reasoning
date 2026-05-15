from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class ReportFormatter:
    """Utility class for formatting report data into various output formats."""

    @staticmethod
    def to_dataframe(data: List[Dict[str, Any]]):
        try:
            import pandas as pd
            return pd.DataFrame(data)
        except ImportError:
            return None

    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @staticmethod
    def to_json(data: Any, pretty: bool = True) -> str:
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)

    @staticmethod
    def to_table(data: List[Dict[str, Any]]) -> str:
        if not data:
            return ""
        headers = list(data[0].keys())
        col_widths = {h: len(h) for h in headers}
        for row in data:
            for h in headers:
                col_widths[h] = max(col_widths[h], len(str(row.get(h, ""))))

        sep = "+" + "+".join("-" * (w + 2) for w in col_widths.values()) + "+"
        header_row = "| " + " | ".join(h.ljust(col_widths[h]) for h in headers) + " |"
        lines = [sep, header_row, sep]

        for row in data:
            line = "| " + " | ".join(
                str(row.get(h, "")).ljust(col_widths[h]) for h in headers
            ) + " |"
            lines.append(line)
        lines.append(sep)
        return "\n".join(lines)

    @staticmethod
    def format_timestamp(dt: Optional[datetime] = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def format_currency(value: float, currency: str = "USD") -> str:
        if currency == "USD":
            return f"${value:,.2f}"
        return f"{value:,.2f} {currency}"

    @staticmethod
    def format_percentage(value: float) -> str:
        return f"{value:+.2%}" if value != 0 else "0.00%"
