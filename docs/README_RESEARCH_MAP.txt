PORTFOLIO STRATEGY LAB — RESEARCH MAP
========================================

START HERE
Read this map, docs/PHASE1_PROTOCOL.txt and docs/PHASE1B_PROTOCOL.txt before continuing.

CURRENT DECISION STATE
Phase 1 is COMPLETE.
Phase 1B fixed-ensemble extension is CLOSED.
No robust Phase 1 winner has been established.
No robust Phase 1B ensemble improvement has been established.
Value is omitted until comparable point-in-time historical valuation data are available.
Phase 2 is ACTIVE — Stage 2A entry-engine research is running.

PHASE 1B RESULT
Frozen combinations:
C1 = 50% B0 + 50% Momentum
C2 = 50% Momentum + 50% Dynamic Allocation
C3 = 1/3 B0 + 1/3 Momentum + 1/3 Dynamic Allocation

Development and walk-forward testing were completed. C2 was the closest candidate, but it did not consistently improve S5 Dynamic Allocation across common and expansive histories. C1 and C3 showed severe expansive-history drawdowns. Therefore no ensemble is promoted as a robust Phase 1 benchmark.

The Phase 1B screen was closed after development plus walk-forward; later cost, external-universe, reserved-holdout and bootstrap tests were not run for the ensembles because no candidate survived the initial robustness gate. This is a screening conclusion, not a claim about untested later results.

PHASE 1 FINAL STATE
Phase 1 core families: B0, B1, S1, S3, S4, S5, S6. Value omitted.
All Phase 1 robustness/generalization tests were completed.
Robust Phase 1 winner = NONE.

NEXT PHASE
Phase 2 may now be considered separately. It must not retroactively alter Phase 1 or Phase 1B results.

ANTI-REGRESSION RULE
Do not use Phase 2 concepts to modify historical Phase 1/1B definitions.
Freeze Phase 2 definitions before evaluating its results.


PHASE 2 CURRENT STATE
Stage 2A protocol is frozen in docs/PHASE2_PROTOCOL.txt.
Baseline engine: daily triggers, weekly confirmed HH52 + Wilder ATR20W, ATR 1.5/3/5/8, cumulative 25/50/75/100%, S1-S4 matrix, 5% cash floor, no leverage, unused cash carries.
Initial capital deployment is intentionally isolated; Stage 2A uses recurring contributions only.
Simultaneous-trigger distribution is explicitly tested as D1 target-weighted, D2 equal-weighted and D3 deepest-first.
