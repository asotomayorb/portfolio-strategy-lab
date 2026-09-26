PORTFOLIO STRATEGY LAB — RESEARCH MAP
========================================

START HERE
Read this map and docs/PHASE1_PROTOCOL.txt before continuing. Phase 2 is blocked until Phase 1 is closed.

CURRENT DECISION STATE
No robust Phase 1 winner has been established.
Value is omitted until comparable point-in-time historical valuation data are available.
All pre-external robustness checks are complete.
External-universe generalization validation is complete.
Phase 2 must not start.

EXTERNAL-UNIVERSE RESULT
Frozen new universe: SPY, DIA, IWM, VGK, EEM, TLT, VNQ, XLV, XLP, XLU, XLI, HYG.
Window: 2007-01-01 to 2026-09-24.
Allocation: 95% invested, equal-weight; 5% cash.
Results:
B0 4.86% CAGR / -37.53% DD / 0.386 Sharpe
B1 4.82% / -34.59% / 0.383
S1 14.09% / -16.50% / 0.720
S3 15.18% / -14.58% / 0.760
S4 10.31% / -12.66% / 0.705
S5 12.67% / -11.44% / 0.800
S6 3.50% / -35.43% / 0.311
These are descriptive results, not a ranking. The test is an external-universe generalization test, not fully independent temporal OOS.

NO-LEAKAGE RULE
External results cannot be used to change strategy definitions, parameters, cadence, costs or selection rules.

NEXT EXECUTION ORDER
1. Run a genuinely reserved holdout unseen during all development and the external test.
2. Quantify statistical uncertainty.
3. Perform final Phase 1 synthesis and decide whether evidence supports any robust winner.
4. Only then unlock Phase 2.

ANTI-REGRESSION RULE
At the beginning of every research step, re-read this map and PHASE1_PROTOCOL.
At the end of every step, update them with current status/results/next step.
Never move to Phase 2 unless the Phase 1 checklist explicitly says complete.
