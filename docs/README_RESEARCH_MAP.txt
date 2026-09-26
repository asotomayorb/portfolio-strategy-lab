PORTFOLIO STRATEGY LAB — RESEARCH MAP
========================================

START HERE
Read this map and docs/PHASE1_PROTOCOL.txt before continuing. Phase 2 is blocked until Phase 1 is closed.

CURRENT DECISION STATE
No robust Phase 1 winner has been established.
Value is omitted until comparable point-in-time historical valuation data are available.
All robustness and generalization tests completed so far are descriptive; no parameters were selected from them.
Phase 2 must not start.

RESERVED HOLDOUT RESULT
Frozen new ticker universe: VTI, MDY, EFA, IAU, AGG, IEF, TIP, EMB, XLB, XLY.
Window: 2007-01-01 to 2026-09-24.
Allocation: 95% invested, equal-weight; 5% cash.
Results:
B0 5.51% CAGR / -21.17% DD / 0.474 Sharpe
B1 5.42% / -18.97% / 0.470
S1 14.62% / -11.02% / 0.793
S3 14.35% / -11.01% / 0.777
S4 9.07% / -14.39% / 0.706
S5 12.74% / -7.57% / 0.843
S6 3.59% / -20.65% / 0.378
EMB starts 2007-12-19; other holdout tickers start 2007-01-03. No synthetic prehistory was used.
This is a reserved ticker-universe generalization test, not independent temporal OOS.

NO-LEAKAGE RULE
Holdout results cannot be used to change strategy definitions, parameters, cadence, costs or selection rules.

NEXT EXECUTION ORDER
1. Quantify statistical uncertainty without using holdout outcomes to select methods.
2. Perform final Phase 1 synthesis.
3. Keep robust winner = NONE unless evidence across all frozen dimensions supports a defensible conclusion.
4. Only then unlock Phase 2.

ANTI-REGRESSION RULE
At the beginning of every research step, re-read this map and PHASE1_PROTOCOL.
At the end of every step, update them with current status/results/next step.
Never move to Phase 2 unless the Phase 1 checklist explicitly says complete.
