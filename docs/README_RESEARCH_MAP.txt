PORTFOLIO STRATEGY LAB — RESEARCH MAP
========================================

START HERE
Read this map and docs/PHASE1_PROTOCOL.txt before continuing. Phase 2 is blocked until Phase 1 is closed.

CURRENT DECISION STATE
Phase 1 is COMPLETE.
No robust Phase 1 winner has been established.
Value is omitted until comparable point-in-time historical valuation data are available.
All robustness and generalization tests completed so far are descriptive; no parameters were selected from them. Statistical uncertainty is now quantified with a pre-registered circular moving-block bootstrap on original development histories only.
Phase 2 has not started and remains a separate next phase.

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

STATISTICAL UNCERTAINTY RESULT
Primary method: circular moving-block bootstrap of monthly time-weighted returns; 3/6/12-month blocks, 6-month primary; 5,000 replicates; 95% percentile intervals. Common history has 71 months and expansive history 319 months. Intervals are wide, especially for common history. Under the primary 6-month block, paired CAGR differences versus B0 have 95% intervals crossing zero for every other strategy in both histories. This is uncertainty evidence, not a selection rule.

FINAL PHASE 1 SYNTHESIS
No robust winner. B0/B1 are strong original-universe benchmarks but have large expansive drawdowns and limited cross-universe generalization. S1/S3 show relatively consistent behavior but no dominance across all dimensions. S5 shows comparatively constrained drawdowns in several tests but no universal dominance. S4 is inconsistent. S6 is highly universe-dependent. Statistical uncertainty is broad and paired CAGR intervals versus B0 cross zero for all comparators in both histories.

NEXT PHASE
Phase 1 is closed. Phase 2 may now be considered separately; it has not been started.

ANTI-REGRESSION RULE
At the beginning of every research step, re-read this map and PHASE1_PROTOCOL.
At the end of every step, update them with current status/results/next step.
Never move to Phase 2 unless the Phase 1 checklist explicitly says complete.
