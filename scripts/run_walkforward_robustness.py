"""Walk-forward regime robustness validation for frozen Phase 1 strategies.

No parameters are fitted on the evaluation windows. Each strategy is generated
once from the frozen Phase 1 definitions, then evaluated across chronological
blocks. The test is intended to expose strategies whose full-history result is
driven by a small number of regimes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backtest import simulate
from experiment import (
    CONFIG,
    TICKER_DIR,
    _signals,
    allocation_metadata,
    load_config,
    load_targets,
    prepare_price_matrices,
)
from history import common_history_start
from metrics import summarize


METRICS = ["CAGR", "Sharpe", "Sortino", "Calmar", "max_drawdown", "longest_recovery_months"]


def run_equity(history_mode: str):
    cfg = load_config(CONFIG)
    prices, execution_prices = prepare_price_matrices(TICKER_DIR)
    if history_mode == "common":
        start = common_history_start(prices)
        prices = prices.loc[prices.index >= start].copy()
        execution_prices = execution_prices.reindex(prices.index).copy()
    elif history_mode != "expanding":
        raise ValueError(history_mode)

    targets = load_targets(cfg)
    invest_targets = {k: v for k, v in targets.items() if k != "CASH"}
    missing = sorted(set(invest_targets) - set(prices.columns))
    if missing:
        raise ValueError("Missing tickers: " + ", ".join(missing))

    initial = float(cfg["portfolio"]["initial_capital"])
    contribution = float(cfg["portfolio"]["monthly_contribution"])
    signals = _signals(prices, targets, cfg)
    invest_total = sum(invest_targets.values())
    for name in list(signals):
        if name not in {"B0_buy_hold", "B1_dca"} and invest_total < 1.0:
            signals[name] = signals[name] * invest_total

    outputs = {}
    for name, sig in signals.items():
        invest = name != "B0_buy_hold"
        rebalance = name not in {"B0_buy_hold", "B1_dca"}
        eq, turnover, trades = simulate(
            prices,
            sig,
            initial,
            contribution if invest else 0.0,
            cfg["costs"]["commission_bps"],
            cfg["costs"]["slippage_bps"],
            invest_contributions=invest,
            rebalance=rebalance,
            execution_prices=execution_prices,
        )
        outputs[name] = (eq, turnover, trades)
    return prices, outputs


def block_edges(index: pd.DatetimeIndex, n_blocks: int = 4):
    months = pd.DatetimeIndex(index).to_period("M").unique()
    chunks = [c for c in pd.Series(months).array if c is not None]
    groups = pd.Series(chunks).groupby(
        pd.Series(range(len(chunks))) * n_blocks // max(len(chunks), 1)
    )
    # Use approximately equal chronological blocks, preserving every month.
    split = pd.Series(range(len(chunks))).map(lambda i: min(n_blocks - 1, i * n_blocks // len(chunks)))
    return [chunks[i] for i in range(len(chunks)) if i == 0], split


def make_blocks(index: pd.DatetimeIndex, n_blocks: int = 4):
    months = list(pd.DatetimeIndex(index).to_period("M").unique())
    out = []
    for i in range(n_blocks):
        lo = (len(months) * i) // n_blocks
        hi = (len(months) * (i + 1)) // n_blocks
        if lo < hi:
            out.append((months[lo], months[hi - 1]))
    return out


def main():
    rows = []
    for history_mode in ("common", "expanding"):
        prices, outputs = run_equity(history_mode)
        blocks = make_blocks(prices.index, 4)
        for strategy, (eq, turnover, trades) in outputs.items():
            for fold, (start, end) in enumerate(blocks, 1):
                part = eq[(eq.index.to_period("M") >= start) & (eq.index.to_period("M") <= end)]
                if len(part) < 3:
                    continue
                flows = part["contribution"]
                m = summarize(
                    part["equity"],
                    external_cashflows=flows,
                    initial_capital=float(part["equity"].iloc[0] - flows.iloc[0]),
                    cash=part["cash"],
                )
                if not m:
                    continue
                row = {
                    "history_mode": history_mode,
                    "fold": fold,
                    "fold_start": str(start),
                    "fold_end": str(end),
                    "strategy": strategy,
                }
                row.update({k: m[k] for k in METRICS})
                rows.append(row)

    data = pd.DataFrame(rows)
    data.to_csv(ROOT / "walkforward_robustness_ci.csv", index=False)

    # Pre-registered robustness test:
    # A candidate must be Pareto-efficient on the fold medians in BOTH
    # histories. This is a robustness filter, not a performance score.
    med = data.groupby(["history_mode", "strategy"], as_index=False)[METRICS].median()

    def pareto(frame):
        front = []
        for i, a in frame.reset_index(drop=True).iterrows():
            dominated = False
            for j, b in frame.reset_index(drop=True).iterrows():
                if i == j:
                    continue
                ge = (
                    b["CAGR"] >= a["CAGR"]
                    and b["Sharpe"] >= a["Sharpe"]
                    and b["Sortino"] >= a["Sortino"]
                    and b["Calmar"] >= a["Calmar"]
                    and b["max_drawdown"] >= a["max_drawdown"]
                    and b["longest_recovery_months"] <= a["longest_recovery_months"]
                )
                gt = (
                    b["CAGR"] > a["CAGR"]
                    or b["Sharpe"] > a["Sharpe"]
                    or b["Sortino"] > a["Sortino"]
                    or b["Calmar"] > a["Calmar"]
                    or b["max_drawdown"] > a["max_drawdown"]
                    or b["longest_recovery_months"] < a["longest_recovery_months"]
                )
                if ge and gt:
                    dominated = True
                    break
            if not dominated:
                front.append(a["strategy"])
        return front

    fronts = {
        mode: pareto(med[med["history_mode"] == mode].copy())
        for mode in ("common", "expanding")
    }
    intersection = sorted(set(fronts["common"]) & set(fronts["expanding"]))
    unique = intersection[0] if len(intersection) == 1 else "NONE"

    summary = (
        "WALK_FORWARD_ROBUSTNESS\n"
        + "common_median_pareto=" + ",".join(fronts["common"]) + "\n"
        + "expanding_median_pareto=" + ",".join(fronts["expanding"]) + "\n"
        + "walkforward_robust_winner=" + unique + "\n"
        + "\nMEDIANS\n"
        + med.to_csv(index=False)
    )
    (ROOT / "walkforward_robustness_summary.txt").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
