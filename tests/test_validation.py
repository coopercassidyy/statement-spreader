"""Tests for the offline tie-out and completeness checks in src/validation.py."""

from src.validation import check_balance_sheet_ties, check_completeness, validate_spread


def _year(assets=None, liabilities=None, equity=None, revenue=1, net_income=1, cfo=1):
    return {
        "total_assets": {"value": assets, "tag": "Assets", "derived": False},
        "total_liabilities": {"value": liabilities, "tag": "Liabilities", "derived": False},
        "stockholders_equity": {"value": equity, "tag": "StockholdersEquity", "derived": False},
        "revenue": {"value": revenue, "tag": "Revenues", "derived": False},
        "net_income": {"value": net_income, "tag": "NetIncomeLoss", "derived": False},
        "cfo": {"value": cfo, "tag": "NetCashProvidedByUsedInOperatingActivities", "derived": False},
    }


def test_balance_sheet_ties_when_equal():
    result = check_balance_sheet_ties(_year(assets=1000, liabilities=600, equity=400))
    assert result["ok"] is True
    assert result["diff"] == 0


def test_balance_sheet_flags_mismatch():
    # Diff must exceed the $1M rounding tolerance to be flagged.
    result = check_balance_sheet_ties(_year(assets=10_000_000, liabilities=6_000_000, equity=1_000_000))
    assert result["ok"] is False
    assert result["diff"] == 3_000_000


def test_balance_sheet_tolerates_rounding_noise():
    result = check_balance_sheet_ties(_year(assets=1000, liabilities=600, equity=400.5))
    assert result["ok"] is True


def test_balance_sheet_returns_none_when_data_missing():
    result = check_balance_sheet_ties(_year(assets=None, liabilities=600, equity=400))
    assert result["ok"] is None
    assert result["diff"] is None


def test_completeness_flags_missing_required_item():
    year_data = _year(assets=1000, liabilities=600, equity=400)
    year_data["net_income"]["value"] = None
    missing = check_completeness(year_data)
    assert "net_income" in missing


def test_completeness_empty_when_all_present():
    year_data = _year(assets=1000, liabilities=600, equity=400)
    assert check_completeness(year_data) == []


def test_validate_spread_across_multiple_years():
    spread = {
        2022: _year(assets=1000, liabilities=600, equity=400),
        2023: _year(assets=10_000_000, liabilities=6_000_000, equity=1_000_000),  # mismatched
    }
    result = validate_spread(spread)
    assert result[2022]["balance_sheet_ties"]["ok"] is True
    assert result[2023]["balance_sheet_ties"]["ok"] is False
