"""Phase 1 external-universe validation using frozen strategy definitions.

External-universe generalization test, not fully independent temporal OOS.
"""
from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path
import sys

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from experiment import run_phase1

TICKERS = ["SPY", "DIA", "IWM", "VGK", "EEM", "TLT", "VNQ", "XLV", "XLP", "XLU", "XLI", "HYG"]
START = "2007-01-01"
END = "2026-09-24"
CASH = 0.05
SOURCE = "Yahoo Finance chart API (daily OHLCV, raw OHLC; retrieved at CI runtime)"


def fetch(symbol: str, out: Path) -> tuple[str, str, int]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?period1={int(pd.Timestamp(START, tz='UTC').timestamp())}"
        f"&period2={int((pd.Timestamp(END, tz='UTC') + pd.Timedelta(days=1)).timestamp())}"
        "&interval=1d&events=div%7Csplit&includeAdjustedClose=true"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 portfolio-strategy-lab"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)["chart"]["result"][0]
    q = result["indicators"]["quote"][0]
    frame = pd.DataFrame({
        "Date": pd.to_datetime(result["timestamp"], unit="s", utc=True).date,
        "Open": q["open"], "High": q["high"], "Low": q["low"],
        "Close": q["close"], "Volume": q["volume"],
    }).dropna(subset=["Open", "High", "Low", "Close"])
    frame["Date"] = frame["Date"].astype(str)
    frame = frame[(frame["Date"] >= START) & (frame["Date"] <= END)]
    if frame.empty:
        raise RuntimeError(f"{symbol}: no data in frozen window")
    frame.to_csv(out, index=False)
    return frame["Date"].iloc[0], frame["Date"].iloc[-1], len(frame)


def main():
    alloc = ROOT / "external_allocation_ci.csv"
    try:
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "tickers"
            data_dir.mkdir()
            coverage = []
            for symbol in TICKERS:
                first, last, n = fetch(symbol, data_dir / f"{symbol}.csv")
                coverage.append({"ticker": symbol, "first": first, "last": last, "rows": n})

            w = (1.0 - CASH) / len(TICKERS)
            pd.DataFrame({
                "Ticker": TICKERS + ["cash"],
                "Allocation %": [f"{w*100:.10f}%"] * len(TICKERS) + [f"{CASH*100:.10f}%"],
            }).to_csv(alloc, index=False)

            cfg = yaml.safe_load((ROOT / "config" / "phase1.yaml").read_text())
            cfg["portfolio"]["allocation_file"] = str(alloc)
            cfg["dataset_version"] = "external-universe-yahoo-v1"
            cfg["config_version"] = "v3-external-universe-frozen"
            cfg_path = Path(td) / "phase1_external.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

            result = run_phase1(ticker_dir=data_dir, cfg_path=cfg_path, history_mode="expanding")
            result["validation_type"] = "external_universe_generalization"
            result["universe"] = ",".join(TICKERS)
            result["window_start"] = START
            result["window_end"] = END
            result["source"] = SOURCE
            result.to_csv(ROOT / "external_universe_validation_ci.csv", index=False)
            pd.DataFrame(coverage).to_csv(ROOT / "external_universe_data_coverage_ci.csv", index=False)

            with open(ROOT / "external_universe_validation_summary.txt", "w", encoding="utf-8") as f:
                f.write("PHASE 1 EXTERNAL-UNIVERSE VALIDATION\n===================================\n")
                f.write(f"Window: {START} to {END}\n")
                f.write(f"Universe ({len(TICKERS)}): {', '.join(TICKERS)}\n")
                f.write(f"Investable target: {1-CASH:.0%}, equal-weight; cash: {CASH:.0%}\n")
                f.write(f"Source: {SOURCE}\n")
                f.write("Classification: external-universe generalization test; not fully independent temporal OOS.\n\n")
                f.write(result[["strategy", "CAGR", "max_drawdown", "Sharpe", "Sortino"]].to_string(index=False))
                f.write("\n\nCoverage:\n" + pd.DataFrame(coverage).to_string(index=False) + "\n")
            print(result[["strategy", "CAGR", "max_drawdown", "Sharpe", "Sortino"]].to_string(index=False))
    finally:
        if alloc.exists():
            alloc.unlink()


if __name__ == "__main__":
    main()
