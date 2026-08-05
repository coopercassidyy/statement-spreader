"""Thin client for SEC EDGAR's XBRL APIs: ticker->CIK lookup and company facts,
with local JSON caching so repeated runs don't re-hit the API."""

from __future__ import annotations

import json
import os
import time

import requests

from src.config import CACHE_DIR, REQUEST_DELAY_SECONDS, SEC_USER_AGENT

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

_session = requests.Session()
_session.headers.update({"User-Agent": SEC_USER_AGENT})


def _cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, name)


def _read_cache(name: str):
    path = _cache_path(name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _write_cache(name: str, data) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(name), "w") as f:
        json.dump(data, f)


def get_ticker_cik_map() -> dict:
    """Return {TICKER: '0000320193'} for every SEC-registered ticker, cached locally."""
    cached = _read_cache("ticker_cik_map.json")
    if cached is not None:
        return cached

    resp = _session.get(TICKER_MAP_URL, timeout=20)
    resp.raise_for_status()
    raw = resp.json()

    mapping = {
        entry["ticker"].upper(): f"{entry['cik_str']:010d}"
        for entry in raw.values()
    }
    _write_cache("ticker_cik_map.json", mapping)
    return mapping


def resolve_cik(ticker: str, ticker_map: dict | None = None) -> str:
    ticker_map = ticker_map or get_ticker_cik_map()
    cik = ticker_map.get(ticker.upper())
    if cik is None:
        raise ValueError(f"Unknown ticker: {ticker}")
    return cik


def get_company_facts(cik: str) -> dict:
    """Return the raw companyfacts JSON for a 10-digit zero-padded CIK, cached locally."""
    cache_name = f"companyfacts_{cik}.json"
    cached = _read_cache(cache_name)
    if cached is not None:
        return cached

    resp = _session.get(COMPANY_FACTS_URL.format(cik=cik), timeout=20)
    resp.raise_for_status()
    data = resp.json()

    _write_cache(cache_name, data)
    time.sleep(REQUEST_DELAY_SECONDS)
    return data
