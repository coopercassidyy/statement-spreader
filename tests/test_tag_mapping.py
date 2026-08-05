"""Tests for the tag fallback resolution and fiscal-year derivation logic in
src/spreader.py, using synthetic companyfacts fixtures (no network calls)."""

from src.spreader import get_available_fiscal_years, spread_company


def _instant_fact(end, val, fy, filed, form="10-K", fp="FY"):
    return {"end": end, "val": val, "fy": fy, "fp": fp, "form": form, "filed": filed, "accn": "x"}


def _duration_fact(start, end, val, fy, filed, form="10-K", fp="FY"):
    return {"start": start, "end": end, "val": val, "fy": fy, "fp": fp, "form": form, "filed": filed, "accn": "x"}


def _facts(tags: dict) -> dict:
    return {"entityName": "Test Co", "facts": {"us-gaap": {
        tag: {"units": {"USD": entries}} for tag, entries in tags.items()
    }}}


def test_fallback_uses_second_tag_when_first_is_absent():
    facts = _facts({
        "Assets": [_instant_fact("2023-12-31", 1000, 2099, "2024-02-01")],
        "StockholdersEquity": [_instant_fact("2023-12-31", 400, 2099, "2024-02-01")],
        # No "CostOfRevenue" tag at all -- only the fallback tag.
        "CostOfGoodsAndServicesSold": [_duration_fact("2023-01-01", "2023-12-31", 600, 2099, "2024-02-01")],
        "RevenueFromContractWithCustomerExcludingAssessedTax": [
            _duration_fact("2023-01-01", "2023-12-31", 900, 2099, "2024-02-01")
        ],
    })
    spread = spread_company(facts, num_years=1)
    year_data = next(iter(spread.values()))
    assert year_data["cost_of_revenue"]["value"] == 600
    assert year_data["cost_of_revenue"]["tag"] == "CostOfGoodsAndServicesSold"


def test_fiscal_year_derived_from_end_date_not_mislabeled_fy_field():
    # Reproduces the real SEC quirk: a later filing re-reports an older period
    # under its OWN filing-level `fy`, which does not match the period covered.
    facts = _facts({
        "Assets": [
            _instant_fact("2022-12-31", 1000, 2022, "2023-02-01"),
            _instant_fact("2022-12-31", 1000, 2023, "2024-02-01"),  # re-reported as comparative
            _instant_fact("2023-12-31", 1200, 2023, "2024-02-01"),
        ],
        "StockholdersEquity": [
            _instant_fact("2022-12-31", 400, 2023, "2024-02-01"),
            _instant_fact("2023-12-31", 500, 2023, "2024-02-01"),
        ],
    })
    years = get_available_fiscal_years(facts, num_years=2)
    assert years == [2022, 2023]


def test_dedup_prefers_most_recently_filed_value_for_same_period():
    facts = _facts({
        "Assets": [
            _instant_fact("2023-12-31", 1200, 2023, "2024-02-01"),
            _instant_fact("2023-12-31", 1250, 2023, "2024-11-01"),  # restated later
        ],
        "StockholdersEquity": [_instant_fact("2023-12-31", 500, 2023, "2024-11-01")],
    })
    spread = spread_company(facts, num_years=1)
    year_data = next(iter(spread.values()))
    assert year_data["total_assets"]["value"] == 1250


def test_missing_line_item_is_none_not_guessed():
    facts = _facts({
        "Assets": [_instant_fact("2023-12-31", 1000, 2023, "2024-02-01")],
        "StockholdersEquity": [_instant_fact("2023-12-31", 400, 2023, "2024-02-01")],
    })
    spread = spread_company(facts, num_years=1)
    year_data = next(iter(spread.values()))
    assert year_data["research_and_development"]["value"] is None


def test_total_liabilities_derived_when_tag_absent():
    facts = _facts({
        "Assets": [_instant_fact("2023-12-31", 1000, 2023, "2024-02-01")],
        "StockholdersEquity": [_instant_fact("2023-12-31", 400, 2023, "2024-02-01")],
        # No "Liabilities" tag at all.
    })
    spread = spread_company(facts, num_years=1)
    year_data = next(iter(spread.values()))
    assert year_data["total_liabilities"]["value"] == 600
    assert year_data["total_liabilities"]["derived"] is True
