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


def _crypto_price_record(quote: dict[str, Any]) -> dict[str, Any]:
    """Normalize Tiingo's documented priceData object and list-shaped variants."""
    price_data = quote.get("priceData")
    if isinstance(price_data, dict):
        return price_data
    if isinstance(price_data, list):
        return _first_record(price_data)
    return {}


def check_equity(ticker: str, token: str, start_date: str, include_history: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"symbol": ticker, "asset_type": "US equity/ETF"}
    try:
        quote = _first_record(_get_json(f"/tiingo/equity/intraday/{ticker}", token))
        result["quote_endpoint"] = "ok" if str(quote.get("ticker", "")).upper() == ticker else "unexpected_payload"
        result["reference_price_available"] = _positive(quote.get("tngoLast")) or _positive(quote.get("lqRefPrice"))
        result["reference_price_field"] = "tngoLast" if _positive(quote.get("tngoLast")) else ("lqRefPrice" if _positive(quote.get("lqRefPrice")) else None)
        result["quote_timestamp"] = quote.get("timestamp")
    except Exception as exc:
        result["quote_endpoint"] = "error"
        result["quote_error"] = f"{type(exc).__name__}: {exc}"

    if include_history:
        try:
            history = _get_json(
                f"/tiingo/daily/{ticker}/prices?{urlencode({'startDate': start_date})}",
                token,
            )
            rows = _valid_ohlc_rows(history)
            result["valid_daily_ohlc_rows"] = rows
            result["history_status"] = "available" if rows else "no_history_in_requested_window"
        except Exception as exc:
            result["valid_daily_ohlc_rows"] = 0
            result["history_status"] = "unavailable"
            result["history_error"] = f"{type(exc).__name__}: {exc}"

    result["coverage_pass"] = (
        result.get("quote_endpoint") == "ok"
        and result.get("reference_price_available") is True
    )
    return result


def check_crypto(pair: str, token: str, start_date: str, include_history: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {"symbol": pair, "asset_type": "crypto"}
    try:
        query = urlencode({"tickers": pair})
        raw_quote = _get_json(f"/tiingo/crypto/prices?{query}", token)
        quote = _first_record(raw_quote)
        result["response_shape"] = "list" if isinstance(raw_quote, list) else type(raw_quote).__name__
        result["response_fields"] = sorted(quote.keys())
        result["pair_metadata_pass"] = (
            str(quote.get("ticker", "")).lower() == pair
            and str(quote.get("baseCurrency", "")).lower() == "btc"
            and str(quote.get("quoteCurrency", "")).lower() == "usd"
        )
        raw_price_data = quote.get("priceData")
        price_data = _crypto_price_record(quote)
        result["price_data_shape"] = (
            "list" if isinstance(raw_price_data, list)
            else "object" if isinstance(raw_price_data, dict)
            else "missing_or_null" if raw_price_data is None
            else type(raw_price_data).__name__
        )
        result["price_data_fields"] = sorted(price_data.keys())
        result["reference_price_available"] = _positive(price_data.get("close"))
        result["reference_price_field"] = "priceData.close" if result["reference_price_available"] else None
        result["quote_timestamp"] = price_data.get("date")
    except Exception as exc:
        result["pair_metadata_pass"] = False
        result["reference_price_available"] = False
        result["quote_error"] = f"{type(exc).__name__}: {exc}"

    if include_history:
        try:
            hist_query = urlencode({
                "tickers": pair,
                "startDate": start_date,
                "resampleFreq": "1day",
            })
            history = _get_json(f"/tiingo/crypto/prices?{hist_query}", token)
            history_record = _first_record(history)
            rows = _valid_ohlc_rows(
                history_record.get("priceData") if isinstance(history_record, dict) else None
            )
            result["valid_daily_ohlc_rows"] = rows
            result["history_status"] = "available" if rows else "no_history_in_requested_window"
        except Exception as exc:
            result["valid_daily_ohlc_rows"] = 0
            result["history_status"] = "unavailable"
            result["history_error"] = f"{type(exc).__name__}: {exc}"

    result["coverage_pass"] = (
        result.get("pair_metadata_pass") is True
        and result.get("reference_price_available") is True
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Tiingo REST coverage for the current portfolio.")
    parser.add_argument("--allocation", type=Path, default=DEFAULT_ALLOCATION)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--include-history", action="store_true", help="Query optional daily OHLC diagnostics; does not affect current-price coverage.")
    args = parser.parse_args()

    token = os.environ.get("TIINGO_API_KEY", "").strip()
    if not token:
        print("ERROR: set TIINGO_API_KEY in the environment; never pass it as a CLI argument.", file=sys.stderr)
        return 2

    equities, crypto_pair = load_market_symbols(args.allocation)
    results = [check_equity(symbol, token, args.start_date, include_history=args.include_history) for symbol in equities]
    if crypto_pair:
        results.append(check_crypto(crypto_pair, token, args.start_date, include_history=args.include_history))

    summary = {
        "provider": "Tiingo",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "history_start_date": args.start_date,
        "results": results,
        "coverage_passed": sum(bool(row.get("coverage_pass")) for row in results),
        "coverage_total": len(results),
        "all_passed": bool(results) and all(row.get("coverage_pass") for row in results),
        "notes": [
            "REST current-price coverage probe only; WebSocket delivery/latency soak test remains separate.",
            "Historical OHLC requests are disabled by default; pass --include-history only when explicitly needed.",
            "Current reference-price availability gates symbol coverage; history length is informational and never a minimum eligibility requirement.",
            "Newly listed assets are reported with the history actually returned; 52-week indicators remain unavailable until sufficient observations exist.",
            "Crypto Top-of-Book is intentionally not queried; Crypto Prices is used for BTC reference/last price.",
            "Crypto diagnostics report response and priceData shapes/field names only; credentials and raw exchange payloads are never printed.",
            "This probe does not authorize trading or validate executable prices.",
        ],
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
