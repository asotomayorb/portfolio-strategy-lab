# Backtest Protocol — Phase 1

## Common rules
- Universe: VT, SMH, BTC, INDA, MSFT, NVDA, AVGO, GLD, URA, XLE, VHT, PLTR, QQQ.
- No leverage.
- No shorting.
- Same transaction-cost and slippage assumptions.
- Monthly decision frequency for Phase 1.
- Signals use information available at the decision timestamp only.
- Orders are executed no earlier than the next session to avoid look-ahead bias.
- Contributions occur on a fixed monthly schedule and are recorded separately from investment returns.
- Cash is explicitly tracked.
- Dividends use total-return/adjusted data when reliably available; the exact source treatment must be recorded.
- Assets with insufficient history are not backfilled with future information.

## History problem
The universe has different inception dates. Do not pretend all assets existed for the full period.
Report:
1. common-history results;
2. expanding-universe results where an asset becomes eligible only after its first valid date;
3. individual/strategy diagnostics by asset history.

## Phase 1 strategy definitions

### B0 Buy & Hold
Maintain the target weights as closely as possible. No tactical selection.

### B1 DCA
Allocate new monthly contributions according to target weights. Rebalancing policy must be frozen before testing.

### S1 Momentum
At each monthly decision date, rank eligible assets by trailing 12-month total return. Use a fixed top-group rule. The 12-month lookback is frozen for Phase 1.

### S2 Value
Use a predeclared valuation score only for comparable assets. Do not invent a synthetic universal valuation metric for BTC/gold/sector ETFs. If an asset lacks comparable fundamentals, mark it ineligible for the value sleeve and document the cash treatment. The data source and exact formula must be frozen before results.

### S3 Rotation
Monthly cross-sectional rotation using the same 12-month return ranking. Select a fixed top-N group. Top-N is frozen for Phase 1.

### S4 Moving Average
Each asset is eligible when close > 200-day SMA. Otherwise its sleeve remains cash. The 200-day window is frozen for Phase 1.

### S5 Dynamic Allocation
Convert a predeclared positive momentum score into weights, normalize, and apply a fixed maximum weight. No parameter tuning in Phase 1.

### S6 Risk Parity
Target equal risk contribution. Use a fixed historical volatility/covariance window. Do not tune the window during Phase 1.

## Metrics
CAGR, annualized volatility, max drawdown, Sharpe, Sortino, Calmar, worst calendar year, recovery time, turnover, number of trades, average/max cash, final value.

## Robustness
A strategy should not be selected because it has the highest CAGR in one window. Compare:
- common-history vs expanding-universe;
- multiple market regimes;
- rolling/walk-forward out-of-sample windows;
- sensitivity around the Phase 2 parameter;
- turnover and implementation burden.

## Phase 2
Only after Phase 1:
- test parameter ranges;
- use train/validation/test separation;
- inspect parameter surfaces rather than a single optimum;
- freeze final parameters before the final out-of-sample test.
