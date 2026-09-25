"""Deterministic Phase 1 experiment runner."""
from __future__ import annotations
from pathlib import Path
import hashlib
import pandas as pd
import yaml
from data_loader import load_csv_folder, close_matrix, open_matrix
from backtest import simulate
from metrics import summarize

from strategies import (
    buy_and_hold,
    dca,
    momentum,
    rotation,
    moving_average,
    dynamic_allocation,
    risk_parity,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "config" / "phase1.yaml"
TICKER_DIR = ROOT / "tickers"


def load_config(path=CONFIG):
    return yaml.safe_load(Path(path).read_text())


def allocation_path(cfg):
    configured = cfg.get("portfolio", {}).get("allocation_file", "portfolio_allocation.csv")
    return ROOT / configured


def load_targets(cfg, path=None):
    """Load user-controlled allocation CSV without normalizing away cash."""
    path = Path(path) if path is not None else allocation_path(cfg)
    frame = pd.read_csv(path)
    required = {"Ticker", "Allocation %"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{path} must contain columns: Ticker, Allocation %")

    result = {}
    for _, row in frame.iterrows():
        ticker = str(row["Ticker"]).strip().upper()
        if not ticker:
            continue
        raw = str(row["Allocation %"]).strip().replace("%", "").replace(",", ".")
        try:
            weight = float(raw) / 100.0
        except ValueError as exc:
            raise ValueError(f"Invalid allocation for {ticker}: {row['Allocation %']}") from exc
        if weight < 0 or weight > 1:
            raise ValueError(f"Allocation for {ticker} must be between 0% and 100%")
        if ticker in {"CASH", "CASHUSD", "CASH USD"}:
            ticker = "CASH"
        if ticker == "BTCUSD":
            ticker = "BTC"
        if ticker == "CASH":
            result["CASH"] = result.get("CASH", 0.0) + weight
        else:
            result[ticker] = result.get(ticker, 0.0) + weight

    total = sum(result.values())
    if total <= 0 or total > 1.0 + 1e-9:
        raise ValueError(f"Total portfolio allocation must be > 0 and <= 100%; got {total:.2%}")
    return result


def allocation_metadata(cfg, path=None):
    path = Path(path) if path is not None else allocation_path(cfg)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    targets = load_targets(cfg, path)
    return {
        "allocation_file": str(path.relative_to(ROOT)),
        "allocation_sha256": digest,
        "allocation_total": sum(targets.values()),
        "cash_target": targets.get("CASH", 0.0),
    }


def prepare_price_matrices(ticker_dir=TICKER_DIR):
    assets = load_csv_folder(ticker_dir)
    return close_matrix(assets), open_matrix(assets)


def prepare_prices(ticker_dir=TICKER_DIR):
    return prepare_price_matrices(ticker_dir)[0]


def _signals(prices, targets, cfg):
    invest_targets = {k: v for k, v in targets.items() if k != "CASH"}
    return {
        "B0_buy_hold": buy_and_hold(prices, invest_targets),
        "B1_dca": dca(prices, invest_targets),
        "S1_momentum": momentum(
            prices,
            cfg["strategies"]["momentum"]["lookback_months"],
            cfg["strategies"]["momentum"]["top_n"],
        ),
        "S3_rotation": rotation(
            prices,
            cfg["strategies"]["rotation"]["lookback_months"],
            cfg["strategies"]["rotation"]["top_n"],
        ),
        "S4_moving_average": moving_average(
            prices, cfg["strategies"]["moving_average"]["window_days"]
        ),
        "S5_dynamic_allocation": dynamic_allocation(
            prices,
            cfg["strategies"]["dynamic_allocation"]["lookback_months"],
            cfg["strategies"]["dynamic_allocation"]["max_weight"],
        ),
        "S6_risk_parity": risk_parity(
            prices, cfg["strategies"]["risk_parity"]["volatility_window_days"]
        ),
    }


def run_phase1(
    ticker_dir=TICKER_DIR,
    cfg_path=CONFIG,
    initial_capital=None,
    monthly_contribution=None,
):
    cfg = load_config(cfg_path)
    prices, execution_prices = prepare_price_matrices(ticker_dir)
    alloc_path = allocation_path(cfg)
    targets = load_targets(cfg, alloc_path)
    missing = sorted(set(targets) - {"CASH"} - set(prices.columns))
    if missing:
        raise ValueError("Allocation contains tickers without price data: " + ", ".join(missing))

    invest_targets = {k: v for k, v in targets.items() if k != "CASH"}
    initial_capital = (
        cfg["portfolio"]["initial_capital"] if initial_capital is None else initial_capital
    )
    monthly_contribution = (
        cfg["portfolio"]["monthly_contribution"]
        if monthly_contribution is None
        else monthly_contribution
    )

    signals = _signals(prices, targets, cfg)
    # B0/B1 use the user's explicit 95% investable allocation. Tactical
    # strategies are normalized to the same 95% invested ceiling so the
    # configured 5% cash reserve is preserved consistently.
    invest_total = sum(invest_targets.values())
    for name in list(signals):
        if name not in {"B0_buy_hold", "B1_dca"} and invest_total < 1.0:
            signals[name] = signals[name] * invest_total
    meta = allocation_metadata(cfg, alloc_path)
    meta.update({
        "history_start": prices.index.min().strftime("%Y-%m-%d"),
        "history_end": prices.index.max().strftime("%Y-%m-%d"),
        "history_rows": int(len(prices)),
    })
    rows = []

    for name, sig in signals.items():
        if name in {"B0_buy_hold", "B1_dca"} and not invest_targets:
            continue

        invest = name != "B0_buy_hold"
        rebalance = name not in {"B0_buy_hold", "B1_dca"}
        eq, turnover, trades = simulate(
            prices,
            sig,
            initial_capital,
            monthly_contribution if invest else 0.0,
            cfg["costs"]["commission_bps"],
            cfg["costs"]["slippage_bps"],
            invest_contributions=invest,
            rebalance=rebalance,
            execution_prices=execution_prices,
        )

        if eq.empty:
            if name in {"B0_buy_hold", "B1_dca"}:
                required = sorted(invest_targets)
                common = prices[required].dropna(how="any") if required else prices
                raise RuntimeError(
                    f"{name} simulation is empty: "
                    f"prices={prices.index.min()}..{prices.index.max()}, "
                    f"rows={len(prices)}, columns={list(prices.columns)}, "
                    f"required={required}, common_rows={len(common)}, "
                    f"common_range={common.index.min() if len(common) else None}"
                    f"..{common.index.max() if len(common) else None}, "
                    f"signal_rows={len(sig)}"
                )
            continue

        m = summarize(
            eq["equity"],
            turnover=turnover,
            trades=trades,
            external_cashflows=eq["contribution"],
            initial_capital=initial_capital,
            cash=eq["cash"],
        )
        m.update(
            {
                "strategy": name,
                "dataset_version": cfg["dataset_version"],
                "config_version": cfg["config_version"],
                **meta,
            }
        )
        rows.append(m)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--tickers", default=str(TICKER_DIR))
    p.add_argument("--output", default=None)
    a = p.parse_args()
    result = run_phase1(a.tickers)
    print(result.to_string(index=False))
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(a.output, index=False)
