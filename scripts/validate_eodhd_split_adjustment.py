"""Read-only split-adjustment validation using EODHD's Corporate Actions API."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://eodhd.com/api"
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


def _valid_ohlc_rows(payload) -> list[dict]:
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
            all(isfinite(v) and v > 0 for v in values)
            and high >= max(open_, low, close)
            and low <= min(open_, high, close)
        ):
            rows.append({**row, **dict(zip(OHLC_KEYS, values))})
    return rows


def parse_split_events(payload) -> list[dict]:
    """Parse EODHD new-shares/old-shares ratios without assuming integer ratios."""
    if not isinstance(payload, list):
        raise ProviderRequestError("unexpected splits response shape")
    events = []
    for row in payload:
        if not isinstance(row, dict) or not row.get("date") or not row.get("split"):
            raise ProviderRequestError("malformed split event")
        try:
            event_date = str(row["date"])
            datetime.strptime(event_date, "%Y-%m-%d")
            numerator, denominator = (float(part) for part in str(row["split"]).split("/", 1))
        except (ValueError, TypeError):
            raise ProviderRequestError("malformed split ratio") from None
        if not isfinite(numerator) or not isfinite(denominator) or numerator <= 0 or denominator <= 0:
            raise ProviderRequestError("invalid split ratio")
        events.append({
            "date": event_date,
            "ratio": numerator / denominator,
            "source_ratio": str(row["split"]),
        })
    return sorted(events, key=lambda event: event["date"])


def apply_split_adjustments(rows: list[dict], events: list[dict]) -> list[dict]:
    """Express historical OHLC in the latest share units using later event ratios."""
    adjusted = []
    for row in rows:
        factor = 1.0
        for event in events:
            if event["date"] > row["date"]:
                factor *= event["ratio"]
        if not isfinite(factor) or factor <= 0:
            raise ProviderRequestError("invalid cumulative corporate-action factor")
        adjusted.append({
            **row,
            **{key: row[key] / factor for key in OHLC_KEYS},
            "split_adjustment_factor": factor,
        })
    return adjusted


def compare_symbol(symbol: str, token: str, start_date: str, end_date: str) -> dict:
    raw_payload = _get_json(
        f"eod/{symbol}", {"from": start_date, "to": end_date, "order": "a"}, token
    )
    splits_payload = _get_json(
        f"splits/{symbol}", {"from": start_date, "to": end_date}, token
    )
    raw_rows = _valid_ohlc_rows(raw_payload)
    events = parse_split_events(splits_payload)
    adjusted_rows = apply_split_adjustments(raw_rows, events)

    changed = sum(
        any(abs(adjusted[key] - raw[key]) > max(1e-8, abs(raw[key]) * 1e-8) for key in OHLC_KEYS)
        for raw, adjusted in zip(raw_rows, adjusted_rows)
    )
    max_abs_change = max(
        (
            abs(adjusted[key] - raw[key])
            for raw, adjusted in zip(raw_rows, adjusted_rows)
            for key in OHLC_KEYS
        ),
        default=0.0,
    )
    return {
        "symbol": symbol,
        "raw_valid_rows": len(raw_rows),
        "split_adjusted_valid_rows": len(adjusted_rows),
        "first_valid_date": raw_rows[0]["date"] if raw_rows else None,
        "latest_valid_date": raw_rows[-1]["date"] if raw_rows else None,
        "split_event_count": len(events),
        "split_events": events,
        "pre_event_rows_available": sum(any(event["date"] > row["date"] for event in events) for row in raw_rows),
        "rows_adjusted": changed,
        "max_absolute_ohlc_difference": round(max_abs_change, 8),
        "data_valid": bool(raw_rows),
        "split_adjustment_detected": changed > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate split-adjusted OHLC reconstructed from EODHD EOD and splits endpoints."
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
        "adjustment_method": "raw EOD OHLC adjusted using later corporate-action split ratios",
        "results": results,
        "all_data_valid": bool(results) and all(r.get("data_valid") for r in results),
        "known_nvda_split_event_available": bool(nvda and any(event["date"] == "2024-06-10" and abs(event["ratio"] - 10.0) < 1e-8 for event in nvda.get("split_events", []))),
        "nvda_pre_split_history_available": bool(nvda and nvda.get("pre_event_rows_available", 0) > 0),
        "known_nvda_split_adjustment_detected": bool(nvda and nvda.get("split_adjustment_detected")),
        "notes": [
            "Corporate Actions splits endpoint returns new-shares/old-shares ratios; historical OHLC before each ex-date is divided by the ratio.",
            "Bars on and after an ex-date are already expressed in the post-action share units and are not adjusted for that event.",
            "The EODHD splits feed may include stock dividends, spin-offs and capital reorganisations; review non-standard events before production use.",
            "This probe checks NVDA.US (known 2024 10-for-1 split) and QQQ.US (comparison series), not the full portfolio.",
            "A split event can be confirmed even when the subscribed EOD history starts after its ex-date; in that case the algorithm is covered by offline tests but cannot be exercised on pre-split live bars.",
            "No Technical API entitlement is required; EOD and splits endpoints are each one API call per symbol.",
            "No strategy calculations, account data, or orders are accessed. The API token is never printed or persisted.",
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_data_valid"] and summary["known_nvda_split_event_available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
