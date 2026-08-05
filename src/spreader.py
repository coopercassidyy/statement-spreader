"""Core engine: raw SEC companyfacts JSON -> normalized {fiscal_year: {line_item: value}}.

Only annual figures from 10-K filings (form == "10-K", fp == "FY") are used —
this is a deliberate scope decision to keep the spread comparable year over
year without mixing in quarterly (10-Q) data.

Gotcha this module works around: the `fy`/`fp` fields on each XBRL datapoint
describe the fiscal period of the *filing* that reported the fact, not the
period the fact itself covers. A single 10-K reports 2-3 years of comparative
data, and every one of those values is tagged with the *same* filing-level
`fy`. Naively filtering by `fy` mixes years together. Instead we derive the
fiscal year directly from each datapoint's own `end` date (which, for every
DEFAULT_TICKERS filer, matches how they name their fiscal year — e.g. NVIDIA
and Salesforce's fiscal year ending Jan 2024 is "fiscal 2024", not 2023) and
de-duplicate values that appear in multiple filings by keeping the one with
the most recent `filed` date (the latest-restated figure).
"""

from __future__ import annotations

from datetime import date

from src.tag_mapping import DERIVED_LINE_ITEMS, LINE_ITEMS, STATEMENT_PERIOD_TYPE

MIN_DURATION_DAYS = 300
MAX_DURATION_DAYS = 380


def _facts_for_tag(company_facts: dict, tag: str) -> list:
    """Return the raw list of datapoints for a us-gaap tag, trying common units."""
    tag_data = company_facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if not tag_data:
        return []
    units = tag_data.get("units", {})
    for unit_key in ("USD", "USD/shares", "shares", "pure"):
        if unit_key in units:
            return units[unit_key]
    if units:
        return next(iter(units.values()))
    return []


def _is_annual_10k(entry: dict) -> bool:
    return entry.get("form") == "10-K" and entry.get("fp") == "FY"


def _is_full_year_duration(entry: dict) -> bool:
    if "start" not in entry or "end" not in entry:
        return False
    start = date.fromisoformat(entry["start"])
    end = date.fromisoformat(entry["end"])
    days = (end - start).days
    return MIN_DURATION_DAYS <= days <= MAX_DURATION_DAYS


def _annual_points(entries: list, period_type: str) -> dict:
    """Collapse raw datapoints into {fiscal_year: value}, deduped and restatement-aware."""
    filtered = [e for e in entries if _is_annual_10k(e)]
    if period_type == "instant":
        filtered = [e for e in filtered if "start" not in e]
        period_key = lambda e: e["end"]
    else:
        filtered = [e for e in filtered if _is_full_year_duration(e)]
        period_key = lambda e: (e["start"], e["end"])

    best_by_period = {}
    for e in filtered:
        k = period_key(e)
        if k not in best_by_period or e.get("filed", "") > best_by_period[k].get("filed", ""):
            best_by_period[k] = e

    best_by_fy = {}
    for e in best_by_period.values():
        fy = int(e["end"][:4])
        if fy not in best_by_fy or e["end"] > best_by_fy[fy]["end"]:
            best_by_fy[fy] = e

    return {fy: e["val"] for fy, e in best_by_fy.items()}


def get_available_fiscal_years(company_facts: dict, num_years: int) -> list:
    """Most recent N fiscal years with an annual Assets figure (a tag every filer has)."""
    points = _annual_points(_facts_for_tag(company_facts, "Assets"), "instant")
    years = sorted(points.keys(), reverse=True)[:num_years]
    return sorted(years)


def _resolve_line_item(company_facts: dict, candidates: list, fy: int, period_type: str):
    for tag in candidates:
        points = _annual_points(_facts_for_tag(company_facts, tag), period_type)
        if fy in points:
            return points[fy], tag
    return None, None


def spread_company(company_facts: dict, num_years: int) -> dict:
    """Return {fy: {line_item_key: {"value": float|None, "tag": str|None, "derived": bool}}}."""
    fiscal_years = get_available_fiscal_years(company_facts, num_years)
    result = {}

    for fy in fiscal_years:
        year_data = {}
        for key, (statement, _label, candidates) in LINE_ITEMS.items():
            period_type = STATEMENT_PERIOD_TYPE[statement]
            value, tag = _resolve_line_item(company_facts, candidates, fy, period_type)
            year_data[key] = {"value": value, "tag": tag, "derived": False}
        result[fy] = year_data

    for fy, year_data in result.items():
        for target_key, (a_key, b_key, op) in DERIVED_LINE_ITEMS.items():
            if year_data[target_key]["value"] is not None:
                continue
            a, b = year_data[a_key]["value"], year_data[b_key]["value"]
            if a is None or b is None:
                continue
            value = a - b if op == "subtract" else None
            year_data[target_key] = {"value": value, "tag": None, "derived": True}

    return result
