"""Read-only Tiingo REST coverage probe. Never prints or persists the API token."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = "https://api.tiingo.com"
DEFAULT_ALLOCATION = ROOT / "portfolio_allocation.csv"


def load_market_symbols(path: Path = DEFAULT_ALLOCATION) -> tuple[list[str], str]:
    """Read market symbols from the current portfolio allocation file."""
    equities: list[str] = []
    crypto_pair = ""
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ticker = str(row.get("Ticker", "")).strip().upper()
            if not ticker or ticker in {"CASH", "CASHUSD", "CASH USD"}:
                continue
            if ticker in {"BTC", "BTCUSD"}:
                crypto_pair = "btcusd"
            else:
                equities.append(ticker)
    return equities, crypto_pair


def _get_json(path: str, token: str, timeout: int = 20) -> Any:
    request = Request(
        API_ROOT + path,
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _first_record(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return payload[0] if payload and isinstance(payload[0], dict) else {}
    return payload if isinstance(payload, dict) else {}


def _valid_ohlc_rows(payload: Any) -> int:
    if isinstance(payload, dict) and "priceData" in payload:
        payload = payload["priceData"]
    rows = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    valid = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            values = [float(row[k]) for k in ("open", "high", "low", "close")]
        except (KeyError, TypeError, ValueError):
            continue
        o, h, l, c = values
        if all(v > 0 for v in values) and h >= max(o, l, c) and l <= min(o, h, c):
            valid += 1
    return valid


def _positive(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def check_equity(ticker: str, token: str, start_date: str) -> dict[str, Any]:
    result: dict[str, Any] = {"symbol": ticker, "asset_type": "US equity/ETF"}
    try:
        quote = _first_record(_get_json(f"/tiingo/equity/intraday/{ticker}", token))
        result["quote_endpoint"] = "ok" if quote.get("ticker", "").upper() == ticker else "unexpected_payload"
        result["reference_price_available"] = _positive(quote.get("tngoLast"))
        result["quote_timestamp"] = quote.get("timestamp")
        history = _get_json(
            f"/tiingo/daily/{ticker}/prices?{urlencode({'startDate': start_date})}",
            token,
        )
        result["valid_daily_ohlc_rows"] = _valid_ohlc_rows(history)
        result["history_endpoint"] = "ok" if result["valid_daily_ohlc_rows"] >= 250 else "insufficient_history"
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, AttributeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:  # keep the probe diagnostic rather than crashing on provider payload changes
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["coverage_pass"] = (
        result.get("quote_endpoint") == "ok"
        and result.get("history_endpoint") == "ok"
    )
    return result


def check_crypto(pair: str, token: str, start_date: str) -> dict[str, Any]:
    result: dict[str, Any] = {"symbol": pair, "asset_type": "crypto"}
    try:
        query = urlencode({"tickers": pair})
        quote = _first_record(_get_json(f"/tiingo/crypto/prices?{query}", token))
        result["pair_metadata_pass"] = (
            str(quote.get("ticker", "")).lower() == pair
            and str(quote.get("baseCurrency", "")).lower() == "btc"
            and str(quote.get("quoteCurrency", "")).lower() == "usd"
        )
        price_data = quote.get("priceData") or {}
        result["reference_price_available"] = _positive(
            price_data.get("close") if isinstance(price_data, dict) else None
        )
        result["quote_timestamp"] = price_data.get("date") if isinstance(price_data, dict) else None
        hist_query = urlencode({
            "tickers": pair,
            "startDate": start_date,
            "resampleFreq": "1day",
        })
        history = _get_json(f"/tiingo/crypto/prices?{hist_query}", token)
        history_record = _first_record(history)
        result["valid_daily_ohlc_rows"] = _valid_ohlc_rows(
            history_record.get("priceData") if isinstance(history_record, dict) else None
        )
        result["history_endpoint"] = "ok" if result["valid_daily_ohlc_rows"] >= 250 else "insufficient_history"
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, AttributeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["coverage_pass"] = (
        result.get("pair_metadata_pass") is True
        and result.get("reference_price_available") is True
        and result.get("history_endpoint") == "ok"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Tiingo REST coverage for the current portfolio.")
    parser.add_argument("--allocation", type=Path, default=DEFAULT_ALLOCATION)
    parser.add_argument("--start-date", default="2024-01-01")
    args = parser.parse_args()

    token = os.environ.get("TIINGO_API_KEY", "").strip()
    if not token:
        print("ERROR: set TIINGO_API_KEY in the environment; never pass it as a CLI argument.", file=sys.stderr)
        return 2

    equities, crypto_pair = load_market_symbols(args.allocation)
    results = [check_equity(symbol, token, args.start_date) for symbol in equities]
    if crypto_pair:
        results.append(check_crypto(crypto_pair, token, args.start_date))

    summary = {
        "provider": "Tiingo",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "history_start_date": args.start_date,
        "results": results,
        "coverage_passed": sum(bool(row.get("coverage_pass")) for row in results),
        "coverage_total": len(results),
        "all_passed": bool(results) and all(row.get("coverage_pass") for row in results),
        "notes": [
            "REST coverage probe only; WebSocket delivery/latency soak test remains separate.",
            "A missing live reference price outside an active feed window is reported but does not alone fail historical/symbol coverage.",
            "Crypto Top-of-Book is intentionally not queried; Tiingo documents that endpoint as deprecated.",
            "This probe does not authorize trading or validate executable prices.",
        ],
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
