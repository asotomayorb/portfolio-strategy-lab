PORTFOLIO STRATEGY LAB — RESEARCH MAP
========================================

START HERE
Read this map and docs/PHASE1_PROTOCOL.txt before continuing. Phase 2 is blocked until Phase 1 is closed.

CURRENT DECISION STATE
No robust Phase 1 winner has been established.
Value is omitted until comparable point-in-time valuation data are available.
Parameter-neighbor, universe, cost/slippage and concentration/dependence tests are complete and validated.
Phase 2 must not start.

CURRENT STEP — EXTERNAL-UNIVERSE VALIDATION
Frozen new ticker universe:
SPY, DIA, IWM, VGK, EEM, TLT, VNQ, XLV, XLP, XLU, XLI, HYG.
Frozen window: 2007-01-01 through 2026-09-24.
External allocation: 95% invested, equal weight across the 12 tickers; 5% cash.
Source: Yahoo Finance daily chart OHLCV retrieved at CI runtime.
Strategy definitions and parameters remain exactly those frozen in Phase 1.
Classification: external-universe generalization test, not fully independent temporal OOS because the calendar period overlaps previously observed data.

NO-LEAKAGE RULE
Results from this external universe must not be used to change strategy definitions, parameters, cadence, costs, or selection rules. Any change would invalidate this validation.

NEXT EXECUTION ORDER
1. Complete external-universe validation and record results.
2. Run a genuinely reserved holdout that remains unseen during all prior development and this external test.
3. Quantify statistical uncertainty.
4. Perform final Phase 1 synthesis and decide whether evidence supports any robust winner.
5. Only then unlock Phase 2.

ANTI-REGRESSION RULE
At the beginning of every research step, re-read this map and PHASE1_PROTOCOL.
At the end of every step, update them with current status/results/next step.
Never move to Phase 2 unless the Phase 1 checklist explicitly says complete.
