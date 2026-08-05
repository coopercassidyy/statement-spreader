#!/usr/bin/env python3
"""CLI entry point: pull 10-K data for a set of tickers and spread it into a
standardized 3-statement Excel workbook.

Usage:
    python main.py
    python main.py --tickers AAPL,MSFT,GOOGL --years 4 --out output/spread.xlsx
"""

from __future__ import annotations

import argparse
import os
import sys

from src.config import DEFAULT_NUM_YEARS, DEFAULT_OUTPUT_PATH, DEFAULT_TICKERS
from src.edgar_client import get_company_facts, get_ticker_cik_map, resolve_cik
from src.excel_builder import build_workbook
from src.spreader import spread_company
from src.validation import validate_spread


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=None,
                         help=f"Comma-separated tickers (default: {','.join(DEFAULT_TICKERS)})")
    parser.add_argument("--years", type=int, default=DEFAULT_NUM_YEARS,
                         help=f"Number of fiscal years to spread (default: {DEFAULT_NUM_YEARS})")
    parser.add_argument("--out", default=DEFAULT_OUTPUT_PATH,
                         help=f"Output .xlsx path (default: {DEFAULT_OUTPUT_PATH})")
    return parser.parse_args()


def main():
    args = parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",")] if args.tickers else DEFAULT_TICKERS

    ticker_map = get_ticker_cik_map()
    companies = {}
    any_mismatch = False

    for ticker in tickers:
        print(f"Processing {ticker}...")
        try:
            cik = resolve_cik(ticker, ticker_map)
            facts = get_company_facts(cik)
        except Exception as e:
            print(f"  SKIPPED: could not fetch data for {ticker}: {e}", file=sys.stderr)
            continue

        spread = spread_company(facts, args.years)
        if not spread:
            print(f"  SKIPPED: no annual 10-K data found for {ticker}", file=sys.stderr)
            continue

        validation = validate_spread(spread)
        companies[ticker] = {
            "entity_name": facts.get("entityName", ticker),
            "spread": spread,
            "validation": validation,
        }

        for fy, checks in validation.items():
            ties = checks["balance_sheet_ties"]
            if ties["ok"] is False:
                any_mismatch = True
                print(f"  WARNING: {ticker} FY{fy} balance sheet does not tie "
                      f"(diff ${ties['diff']:,.0f})", file=sys.stderr)
            missing = checks["missing_required"]
            if missing:
                print(f"  NOTE: {ticker} FY{fy} missing required items: {missing}")

    if not companies:
        print("No companies processed successfully.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    wb = build_workbook(companies)
    wb.save(args.out)

    print(f"\nDone. Spread {len(companies)}/{len(tickers)} companies -> {args.out}")
    if any_mismatch:
        print("Note: one or more balance sheets did not tie out — see warnings above.")


if __name__ == "__main__":
    main()
