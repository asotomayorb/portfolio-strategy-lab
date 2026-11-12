"""Read-only validation of EODHD split-adjusted daily OHLC against raw EOD bars."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://eodhd.com/api"
# NVDA has a known 10-for-1 split in June 2024; QQQ is a comparison instrument.
DEFAULT_SYMBOLS = ("NVDA.US", "QQQ.US")
OHLC_KEYS = ("open", "high", "low", "close")


class ProviderRequestError(RuntimeError):
    """Sanitized provider error; never includes credential-bearing URLs."""


def _get_json(endpoint: str, params: dict[str, str], token: str, timeout: int = 30):
    query = urlencode({**params, "api_token": token, "fmt": "json"})
    request = Request(
        f"{API_ROOT}/{endpoint}?{query}",
        headers={"Accept": "application/json", "User-Agent": "portfolio-strategy-lab/split-adjustment-validation"},
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


def _valid_rows(payload) -> list[dict]:
    if not isinstance(payload, list):
        return []
    rows = []
    for row in payload:
        if not isinstance(row, dict) or not row.get("date"):
            continue
        try:
            datetime.strptime(str(row["date"]), "%Y-%m-%d")
            values = [float(row[key]) for key in OHLC_KEYS]
        except (KeyError, TypeError, ValueError):
            continue
        open_, high, low, close = values
        if (
            all(v > 0 for v in values)
            and high >= max(open_, low, close)
            and low <= min(open_, high, close)
        ):
            rows.append({**row, **dict(zip(OHLC_KEYS, values))})
    return rows


def compare_symbol(symbol: str, token: str, start_date: str, end_date: str) -> dict:
    raw_payload = _get_json(
        f"eod/{symbol}", {"from": start_date, "to": end_date, "order": "a"}, token
    )
    split_payload = _get_json(
        f"technical/{symbol}",
        {
            "function": "splitadjusted",
            "agg_period": "d",
            "from": start_date,
            "to": end_date,
            "order": "a",
        },
        token,
    )
    if not isinstance(raw_payload, list) or not isinstance(split_payload, list):
        raise ProviderRequestError("unexpected response shape")

    raw_rows = _valid_rows(raw_payload)
    split_rows = _valid_rows(split_payload)
    raw_by_date = {row["date"]: row for row in raw_rows}
    split_by_date = {row["date"]: row for row in split_rows}
    overlap = sorted(raw_by_date.keys() & split_by_date.keys())
    changed = 0
    max_abs_change = 0.0
    for day in overlap:
        for key in OHLC_KEYS:
            raw_value = raw_by_date[day][key]
            split_value = split_by_date[day][key]
            difference = abs(split_value - raw_value)
            max_abs_change = max(max_abs_change, difference)
            if difference > max(1e-8, abs(raw_value) * 1e-8):
                changed += 1
                break

    return {
        "symbol": symbol,
        "raw_valid_rows": len(raw_rows),
        "split_adjusted_valid_rows": len(split_rows),
        "overlapping_dates": len(overlap),
        "first_overlap": overlap[0] if overlap else None,
        "latest_overlap": overlap[-1] if overlap else None,
        "rows_with_split_adjustment": changed,
        "max_absolute_ohlc_difference": round(max_abs_change, 8),
        "data_valid": bool(overlap) and len(overlap) == len(split_rows),
        "split_adjustment_detected": changed > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare EODHD raw EOD OHLC with Technical API split-adjusted OHLC."
    )
    parser.add_argument("--start-date", default="2023-01-01")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    args = parser.parse_args()
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        parser.error("--start-date must use YYYY-MM-DD.")

    token = os.environ.get("EODHD_API_KEY", "").strip()
    if not token:
        print("ERROR: set EODHD_API_KEY in the environment; never pass it as a CLI argument.", file=sys.stderr)
        return 2

    end_date = date.today().isoformat()
    results = []
    for symbol in args.symbols:
        try:
            results.append(compare_symbol(symbol, token, args.start_date, end_date))
        except ProviderRequestError as exc:
            results.append({"symbol": symbol, "data_valid": False, "error": str(exc)})
        except Exception as exc:
            results.append({"symbol": symbol, "data_valid": False, "error": type(exc).__name__})

    nvda = next((r for r in results if r.get("symbol") == "NVDA.US"), None)
    summary = {
        "provider": "EODHD",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_from": args.start_date,
        "requested_to": end_date,
        "endpoint": "Technical API function=splitadjusted, agg_period=d",
        "results": results,
        "all_data_valid": bool(results) and all(r.get("data_valid") for r in results),
        "known_split_adjustment_detected": bool(nvda and nvda.get("split_adjustment_detected")),
        "notes": [
            "Technical API splitadjusted returns OHLC adjusted for splits, not dividends.",
            "Raw EOD OHLC is retained as the audit baseline; adjusted_close is not used.",
            "Technical API requests consume five API calls each according to EODHD documentation.",
            "This is a two-symbol entitlement and semantics probe, not approval for all portfolio symbols or production use.",
            "No strategy calculations, account data, or orders are accessed.",
            "The API token is never printed or persisted by this script.",
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_data_valid"] and summary["known_split_adjustment_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
