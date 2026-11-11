"""Read-only EODHD daily-history coverage probe. Never prints or persists the API token."""
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
API_ROOT = "https://eodhd.com/api"
DEFAULT_ALLOCATION = ROOT / "portfolio_allocation.csv"


class ProviderRequestError(RuntimeError):
    """Sanitized provider error that never includes the credential-bearing URL."""


def load_symbols(path: Path = DEFAULT_ALLOCATION) -> list[str]:
    """Map the current portfolio tickers to EODHD's SYMBOL.EXCHANGE format."""
    symbols: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ticker = str(row.get("Ticker", "")).strip().upper()
            if not ticker or ticker in {"CASH", "CASHUSD", "CASH USD"}:
                continue
            symbol = to_eodhd_symbol(ticker)
            if symbol not in symbols:
                symbols.append(symbol)
    return symbols


def to_eodhd_symbol(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker cannot be empty.")
    if ticker in {"BTC", "BTCUSD", "BTC-USD"}:
        return "BTC-USD.CC"
    if ticker.endswith((".US", ".CC", ".FOREX")):
        return ticker
    if "." in ticker:
        return ticker
    return f"{ticker}.US"


def _get_json(symbol: str, token: str, start_date: str, timeout: int = 25) -> Any:
    query = urlencode({"api_token": token, "fmt": "json", "from": start_date})
    request = Request(
        f"{API_ROOT}/eod/{symbol}?{query}",
        headers={"Accept": "application/json", "User-Agent": "portfolio-strategy-lab/market-data-validation"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ProviderRequestError(f"HTTP {exc.code}") from None
    except URLError:
        raise ProviderRequestError("network error") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderRequestError("invalid JSON response") from None
    except TimeoutError:
        raise ProviderRequestError("request timed out") from None


def _valid_ohlc_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    valid: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict) or not row.get("date"):
            continue
        try:
            datetime.strptime(str(row["date"]), "%Y-%m-%d")
            values = [float(row[key]) for key in ("open", "high", "low", "close")]
        except (KeyError, TypeError, ValueError):
            continue
        open_, high, low, close = values
        if (
            all(value > 0 for value in values)
            and high >= max(open_, low, close)
            and low <= min(open_, high, close)
        ):
            valid.append(row)
    return valid


def check_symbol(symbol: str, token: str, start_date: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol": symbol,
        "data_type": "daily EOD OHLCV",
        "ohlc_adjustment": "raw OHLC; adjusted_close includes splits and dividends",
    }
    try:
        payload = _get_json(symbol, token, start_date)
        if not isinstance(payload, list):
            raise ProviderRequestError("unexpected payload shape")
        rows = _valid_ohlc_rows(payload)
        dates = sorted(str(row["date"]) for row in rows)
        unique_dates = sorted(set(dates))
        result.update({
            "rows_returned": len(payload),
            "valid_daily_ohlc_rows": len(rows),
            "adjusted_close_rows": sum(
                _positive(row.get("adjusted_close")) for row in rows
            ),
            "duplicate_dates": len(dates) - len(unique_dates),
            "first_valid_date": unique_dates[0] if unique_dates else None,
            "latest_bar_date": unique_dates[-1] if unique_dates else None,
            "history_status": "available" if rows else "no_valid_history",
            "coverage_pass": bool(rows),
        })
    except ProviderRequestError as exc:
        result.update({
            "rows_returned": 0,
            "valid_daily_ohlc_rows": 0,
            "history_status": "request_error",
            "error": str(exc),
            "coverage_pass": False,
        })
    except Exception as exc:
        # Do not include arbitrary exception text: it may contain a URL or credential.
        result.update({
            "rows_returned": 0,
            "valid_daily_ohlc_rows": 0,
            "history_status": "unexpected_error",
            "error": type(exc).__name__,
            "coverage_pass": False,
        })
    return result


def _positive(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate EODHD daily OHLC history for the current portfolio."
    )
    parser.add_argument("--allocation", type=Path, default=DEFAULT_ALLOCATION)
    parser.add_argument(
        "--start-date",
        default="2023-01-01",
        help="Earliest date requested (YYYY-MM-DD); history length is informational.",
    )
    parser.add_argument(
        "--extra-symbol",
        action="append",
        default=[],
        help="Additional ticker or EODHD symbol, e.g. SPCX or SPCX.US. May be repeated.",
    )
    args = parser.parse_args()

    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        parser.error("--start-date must use YYYY-MM-DD.")

    token = os.environ.get("EODHD_API_KEY", "").strip()
    if not token:
        print(
            "ERROR: set EODHD_API_KEY in the environment; never pass it as a CLI argument.",
            file=sys.stderr,
        )
        return 2

    symbols = load_symbols(args.allocation)
    for extra in args.extra_symbol:
        symbol = to_eodhd_symbol(extra)
        if symbol not in symbols:
            symbols.append(symbol)

    results = [check_symbol(symbol, token, args.start_date) for symbol in symbols]
    summary = {
        "provider": "EODHD",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_from": args.start_date,
        "results": results,
        "coverage_passed": sum(bool(row.get("coverage_pass")) for row in results),
        "coverage_total": len(results),
        "all_passed": bool(results) and all(row.get("coverage_pass") for row in results),
        "notes": [
            "This checks daily end-of-day history, not a live intraday quote.",
            "A current/latest daily bar is not an executable price; IBKR remains the execution quote and account-state source.",
            "History length is informational: new listings pass when at least one valid bar exists.",
            "Raw OHLC is not split-adjusted; adjusted_close includes both splits and dividends.",
            "For ATR/HH calculations, use split-adjusted OHLC or a separately validated corporate-action adjustment. Do not calculate range indicators from adjusted_close.",
            "The probe does not validate WebSocket delivery, commercial licensing, IBKR discrepancies, or authorize orders.",
            "The API token is sent as a query parameter by EODHD; the probe sanitizes errors and never prints the request URL.",
        ],
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
