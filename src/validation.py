"""Pure, offline validation checks against a spread ({fy: {line_item: {...}}})."""

from __future__ import annotations

TOLERANCE = 1_000_000  # $1M slack for rounding / minor XBRL discrepancies

REQUIRED_LINE_ITEMS = [
    "revenue", "net_income",
    "total_assets", "total_liabilities", "stockholders_equity",
    "cfo",
]


def check_balance_sheet_ties(year_data: dict) -> dict:
    """Assets == Liabilities + Equity. Returns {"ok": bool, "diff": float|None}."""
    assets = year_data["total_assets"]["value"]
    liabilities = year_data["total_liabilities"]["value"]
    equity = year_data["stockholders_equity"]["value"]

    if assets is None or liabilities is None or equity is None:
        return {"ok": None, "diff": None}

    diff = assets - (liabilities + equity)
    return {"ok": abs(diff) <= TOLERANCE, "diff": diff}


def check_completeness(year_data: dict) -> list:
    """Return the list of required line items missing a value for this year."""
    return [key for key in REQUIRED_LINE_ITEMS if year_data.get(key, {}).get("value") is None]


def validate_spread(spread: dict) -> dict:
    """Run all checks across every fiscal year in a company's spread.

    Returns {fy: {"balance_sheet_ties": {...}, "missing_required": [...]}}.
    """
    return {
        fy: {
            "balance_sheet_ties": check_balance_sheet_ties(year_data),
            "missing_required": check_completeness(year_data),
        }
        for fy, year_data in spread.items()
    }
