"""Pre-registered statistical uncertainty analysis for frozen Phase 1 strategies.

Uses only the original repository universe, not external or reserved holdouts.
Monthly portfolio returns are bootstrapped with circular moving blocks to retain
short-term time dependence. The method and block lengths are fixed before
observing this run's results.

Primary block length: 6 months.
Sensitivity block lengths: 3 and 12 months.
Bootstrap replicates: 5000 per strategy/history/block length.
95% percentile intervals are reported for CAGR, annualized Sharpe and max drawdown.

Monthly return convention:
r_t = equity_t / (equity_{t-1} + contribution_t) - 1
because the simulator records the contribution before that month's investment.
The first observation is omitted.

No parameters, strategy definitions, or selection rules are changed by this test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from backtest import simulate
from experiment import CONFIG, TICKER_DIR, _signals, load_config, load_targets, prepare_price_matrices
from history import common_history_start

STRATEGIES = [
    "B0_buy_hold", "B1_dca", "S1_momentum", "S3_rotation",
    "S4_moving_average", "S5_dynamic_allocation", "S6_risk_parity",
]
HISTORIES = ["common", "expanding"]
BLOCK_LENGTHS = [3, 6, 12]
PRIMARY_BLOCK = 6
N_BOOT = 5000
SEED = 20260926


def monthly_returns(eq: pd.DataFrame) -> pd.Series:
    e = eq["equity"].astype(float)
    c = eq["contribution"].astype(float)
    prev = e.shift(1)
    r = e / (prev + c) - 1.0
    r = r.iloc[1:].replace([np.inf, -np.inf], np.nan).dropna()
    return r


def run_equities(history_mode: str):
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
    signals = _signals(prices, targets, cfg)
    invest_total = sum(invest_targets.values())
    for name in list(signals):
        if name not in {"B0_buy_hold", "B1_dca"} and invest_total < 1.0:
            signals[name] = signals[name] * invest_total

    out = {}
    initial = float(cfg["portfolio"]["initial_capital"])
    contribution = float(cfg["portfolio"]["monthly_contribution"])
    for name, sig in signals.items():
        invest = name != "B0_buy_hold"
        rebalance = name not in {"B0_buy_hold", "B1_dca"}
        eq, _, _ = simulate(
            prices, sig, initial,
            contribution if invest else 0.0,
            cfg["costs"]["commission_bps"],
            cfg["costs"]["slippage_bps"],
            invest_contributions=invest,
            rebalance=rebalance,
            execution_prices=execution_prices,
        )
        out[name] = monthly_returns(eq)
    return out


def circular_blocks(n: int, block_len: int, rng: np.random.Generator) -> np.ndarray:
    # Circular moving-block bootstrap: each sampled block wraps at the end.
    n_blocks = int(np.ceil(n / block_len))
    starts = rng.integers(0, n, size=n_blocks)
    idx = np.concatenate([
        (s + np.arange(block_len)) % n for s in starts
    ])[:n]
    return idx


def metrics(sample: np.ndarray) -> tuple[float, float, float]:
    # Monthly sample -> annualized CAGR, Sharpe and max drawdown.
    wealth = np.cumprod(1.0 + sample)
    years = len(sample) / 12.0
    cagr = wealth[-1] ** (1.0 / years) - 1.0 if wealth[-1] > 0 else -1.0
    std = sample.std(ddof=1)
    sharpe = (sample.mean() / std) * np.sqrt(12.0) if std > 0 else np.nan
    peak = np.maximum.accumulate(wealth)
    dd = wealth / peak - 1.0
    max_dd = float(dd.min())
    return float(cagr), float(sharpe), max_dd


def bootstrap_returns(r: pd.Series, block_len: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    x = r.to_numpy(dtype=float)
    arr = np.empty((n_boot, len(x)), dtype=float)
    for i in range(n_boot):
        arr[i] = x[circular_blocks(len(x), block_len, rng)]
    return arr


def ci(x: np.ndarray) -> tuple[float, float]:
    return tuple(np.quantile(x, [0.025, 0.975]).tolist())


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    pair_rows = []

    for history in HISTORIES:
        returns = run_equities(history)
        for block_len in BLOCK_LENGTHS:
            samples = {}
            metrics_boot = {}
            for strategy in STRATEGIES:
                r = returns[strategy]
                samples[strategy] = bootstrap_returns(r, block_len, N_BOOT, rng)
                vals = np.array([metrics(x) for x in samples[strategy]])
                metrics_boot[strategy] = vals
                point = np.array(metrics(r.to_numpy()))
                for j, metric_name in enumerate(["CAGR", "Sharpe", "max_drawdown"]):
                    lo, hi = ci(vals[:, j])
                    rows.append({
                        "history_mode": history,
                        "block_months": block_len,
                        "strategy": strategy,
                        "metric": metric_name,
                        "point_estimate": point[j],
                        "ci95_low": lo,
                        "ci95_high": hi,
                        "n_months": len(r),
                        "n_boot": N_BOOT,
                        "seed": SEED,
                    })

            # Paired bootstrap differences: identical sampled indices are used
            # across strategies, preserving the common market-shock pairing.
            base = samples[STRATEGIES[0]]
            for strategy in STRATEGIES[1:]:
                a = samples[strategy]
                b = base
                cagr_diff = np.array([metrics(x)[0] for x in a]) - np.array([metrics(x)[0] for x in b])
                lo, hi = ci(cagr_diff)
                pair_rows.append({
                    "history_mode": history,
                    "block_months": block_len,
                    "strategy_a": strategy,
                    "strategy_b": STRATEGIES[0],
                    "metric": "CAGR_difference_a_minus_b",
                    "point_estimate": metrics(returns[strategy].to_numpy())[0] - metrics(returns[STRATEGIES[0]].to_numpy())[0],
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "bootstrap_prob_a_gt_b": float(np.mean(cagr_diff > 0)),
                    "n_boot": N_BOOT,
                    "seed": SEED,
                })

    summary = pd.DataFrame(rows)
    pairs = pd.DataFrame(pair_rows)
    summary.to_csv(ROOT / "reports/phase1_statistical_uncertainty.csv", index=False)
    pairs.to_csv(ROOT / "reports/phase1_statistical_pairwise_cagr.csv", index=False)

    primary = summary[summary["block_months"] == PRIMARY_BLOCK].copy()
    print("PHASE1 STATISTICAL UNCERTAINTY")
    print("Method: circular moving-block bootstrap of monthly time-weighted returns")
    print(f"Primary block: {PRIMARY_BLOCK} months; sensitivity: {BLOCK_LENGTHS}")
    print(f"Bootstrap replicates: {N_BOOT}; seed: {SEED}")
    print("\nPRIMARY 95% INTERVALS")
    print(primary.to_string(index=False))
    print("\nPAIRED CAGR VS B0, PRIMARY BLOCK")
    print(pairs[pairs["block_months"] == PRIMARY_BLOCK].to_string(index=False))


if __name__ == "__main__":
    main()
