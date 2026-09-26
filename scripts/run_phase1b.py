"""Run the frozen Phase 1B fixed-ensemble extension on development histories."""
from __future__ import annotations

from pathlib import Path
import argparse
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experiment import load_config, allocation_path, load_targets, prepare_price_matrices
from experiment import _signals
from backtest import simulate
from metrics import summarize
from history import common_history_start

CONFIG = ROOT / "config" / "phase1.yaml"
TICKER_DIR = ROOT / "tickers"

ENSEMBLES = {
    "C1_B0_Momentum": {"B0_buy_hold": 0.50, "S1_momentum": 0.50},
    "C2_Momentum_Dynamic": {"S1_momentum": 0.50, "S5_dynamic_allocation": 0.50},
    "C3_B0_Momentum_Dynamic": {
        "B0_buy_hold": 1.0 / 3.0,
        "S1_momentum": 1.0 / 3.0,
        "S5_dynamic_allocation": 1.0 / 3.0,
    },
}


def run(history_mode: str = "expanding"):
    cfg = load_config(CONFIG)
    prices, execution_prices = prepare_price_matrices(TICKER_DIR)
    if history_mode == "common":
        start = common_history_start(prices)
        prices = prices.loc[prices.index >= start].copy()
        execution_prices = execution_prices.reindex(prices.index).copy()
    elif history_mode != "expanding":
        raise ValueError("history_mode must be common or expanding")

    targets = load_targets(cfg, allocation_path(cfg))
    invest_targets = {k: v for k, v in targets.items() if k != "CASH"}
    invest_total = sum(invest_targets.values())
    signals = _signals(prices, targets, cfg)

    for name in list(signals):
        if name not in {"B0_buy_hold", "B1_dca"} and invest_total < 1.0:
            signals[name] = signals[name] * invest_total

    initial = cfg["portfolio"]["initial_capital"]
    monthly = cfg["portfolio"]["monthly_contribution"]
    commission = cfg["costs"]["commission_bps"]
    slippage = cfg["costs"]["slippage_bps"]

    sleeve_curves = {}
    for name in {s for e in ENSEMBLES.values() for s in e}:
        sig = signals[name]
        is_b0 = name == "B0_buy_hold"
        eq, turnover, trades = simulate(
            prices,
            sig,
            initial,
            monthly if not is_b0 else 0.0,
            commission,
            slippage,
            invest_contributions=not is_b0,
            rebalance=not is_b0,
            execution_prices=execution_prices,
        )
        sleeve_curves[name] = (eq, turnover, trades)

    rows = []
    for ensemble, weights in ENSEMBLES.items():
        # Each sleeve receives its fixed share of both initial capital and contributions.
        pieces = []
        for sleeve, weight in weights.items():
            eq, _, _ = sleeve_curves[sleeve]
            x = eq[["equity", "contribution", "cash"]].copy()
            x["equity"] *= weight
            x["contribution"] *= weight
            x["cash"] *= weight
            pieces.append(x)
        combo = pieces[0].copy()
        for x in pieces[1:]:
            combo = combo.add(x, fill_value=0.0)

        # Turnover/trades are weighted sleeve aggregates; this is descriptive for costs.
        turnover = sum(sleeve_curves[s][1] * w for s, w in weights.items())
        trades = sum(sleeve_curves[s][2] * w for s, w in weights.items())
        m = summarize(
            combo["equity"],
            turnover=turnover,
            trades=trades,
            external_cashflows=combo["contribution"],
            initial_capital=initial,
            cash=combo["cash"],
        )
        m.update({
            "strategy": ensemble,
            "history_mode": history_mode,
            "history_start": prices.index.min().strftime("%Y-%m-%d"),
            "history_end": prices.index.max().strftime("%Y-%m-%d"),
            "sleeve_weights": ";".join(f"{k}={v:.6f}" for k,v in weights.items()),
            "config_version": cfg["config_version"],
            "dataset_version": cfg["dataset_version"],
        })
        rows.append(m)
    return pd.DataFrame(rows)


def make_blocks(index, n_blocks=4):
    months = list(pd.DatetimeIndex(index).to_period("M").unique())
    out = []
    for i in range(n_blocks):
        lo = (len(months) * i) // n_blocks
        hi = (len(months) * (i + 1)) // n_blocks
        if lo < hi:
            out.append((months[lo], months[hi - 1]))
    return out


def run_walkforward():
    rows = []
    for history_mode in ("common", "expanding"):
        cfg = load_config(CONFIG)
        prices, execution_prices = prepare_price_matrices(TICKER_DIR)
        if history_mode == "common":
            prices = prices.loc[prices.index >= common_history_start(prices)].copy()
            execution_prices = execution_prices.reindex(prices.index).copy()

        targets = load_targets(cfg, allocation_path(cfg))
        invest_targets = {k: v for k, v in targets.items() if k != "CASH"}
        signals = _signals(prices, targets, cfg)
        invest_total = sum(invest_targets.values())
        for name in list(signals):
            if name not in {"B0_buy_hold", "B1_dca"} and invest_total < 1.0:
                signals[name] = signals[name] * invest_total

        initial = cfg["portfolio"]["initial_capital"]
        monthly = cfg["portfolio"]["monthly_contribution"]
        curves = {}
        for sleeve in {s for e in ENSEMBLES.values() for s in e}:
            is_b0 = sleeve == "B0_buy_hold"
            curves[sleeve] = simulate(
                prices, signals[sleeve], initial,
                monthly if not is_b0 else 0.0,
                cfg["costs"]["commission_bps"], cfg["costs"]["slippage_bps"],
                invest_contributions=not is_b0,
                rebalance=not is_b0,
                execution_prices=execution_prices,
            )[0]

        ensemble_curves = {}
        for ensemble, weights in ENSEMBLES.items():
            pieces = []
            for sleeve, weight in weights.items():
                x = curves[sleeve][["equity","contribution","cash"]].copy() * weight
                pieces.append(x)
            combo = pieces[0].copy()
            for x in pieces[1:]:
                combo = combo.add(x, fill_value=0.0)
            ensemble_curves[ensemble] = combo

        for ensemble, eq in ensemble_curves.items():
            for fold, (start, end) in enumerate(make_blocks(prices.index, 4), 1):
                part = eq[(eq.index.to_period("M") >= start) & (eq.index.to_period("M") <= end)]
                if len(part) < 3:
                    continue
                m = summarize(
                    part["equity"],
                    external_cashflows=part["contribution"],
                    initial_capital=float(part["equity"].iloc[0] - part["contribution"].iloc[0]),
                    cash=part["cash"],
                )
                rows.append({
                    "history_mode": history_mode,
                    "fold": fold,
                    "fold_start": str(start),
                    "fold_end": str(end),
                    "strategy": ensemble,
                    "CAGR": m["CAGR"],
                    "Sharpe": m["Sharpe"],
                    "Sortino": m["Sortino"],
                    "Calmar": m["Calmar"],
                    "max_drawdown": m["max_drawdown"],
                    "longest_recovery_months": m["longest_recovery_months"],
                })
    data = pd.DataFrame(rows)
    data.to_csv(ROOT / "reports/phase1b_walkforward.csv", index=False)
    med = data.groupby(["history_mode","strategy"], as_index=False)[
        ["CAGR","Sharpe","Sortino","Calmar","max_drawdown","longest_recovery_months"]
    ].median()
    return med


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="reports/phase1b_results.csv")
    args = p.parse_args()
    result = pd.concat([run("common"), run("expanding")], ignore_index=True)
    med = run_walkforward()
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)
    print(result.to_string(index=False))
    print("
WALK-FORWARD MEDIANS")
    print(med.to_string(index=False))
    print(f"
Wrote {out}")


if __name__ == "__main__":
    main()

# Phase 1B frozen runner: trigger CI after workflow installation.

# Trigger CI with walk-forward artifact configuration.
