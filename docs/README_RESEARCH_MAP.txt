PORTFOLIO STRATEGY LAB — RESEARCH MAP
========================================

START HERE
Read this map, docs/PHASE1_PROTOCOL.txt, docs/PHASE1B_PROTOCOL.txt and docs/PHASE2_PROTOCOL.txt before continuing. For Stage 2E execution also read docs/PHASE2E_PROTOCOL.txt.

CURRENT DECISION STATE
Phase 1 is COMPLETE.
Phase 1B fixed-ensemble extension is CLOSED.
No robust Phase 1 winner has been established.
No robust Phase 1B ensemble improvement has been established.
Value is omitted until comparable point-in-time historical valuation data are available.
Phase 2 is ACTIVE — Stages 2A, 2B, 2C and 2D are complete. Stage 2E robustness/generalization/uncertainty is frozen and pending execution.

PHASE 1B RESULT
Frozen combinations:
C1 = 50% B0 + 50% Momentum
C2 = 50% Momentum + 50% Dynamic Allocation
C3 = 1/3 B0 + 1/3 Momentum + 1/3 Dynamic Allocation

Development and walk-forward testing were completed. C2 was the closest candidate, but it did not consistently improve S5 Dynamic Allocation across common and expansive histories. C1 and C3 showed severe expansive-history drawdowns. Therefore no ensemble is promoted as a robust Phase 1 benchmark.

PHASE 1 FINAL STATE
Phase 1 core families: B0, B1, S1, S3, S4, S5, S6. Value omitted.
All Phase 1 robustness/generalization tests were completed.
Robust Phase 1 winner = NONE.

ANTI-REGRESSION RULE
Do not use Phase 2 concepts to modify historical Phase 1/1B definitions.
Freeze Phase 2 definitions before evaluating results.

PHASE 2 CURRENT STATE
Stage 2A contribution-only S1-S4 x D1-D3 is complete after the data-continuity correction.
Stage 2B froze D3 as the operational simultaneous-capital rule based on the pre-existing capital-priority design, not performance ranking.
Stage 2C deployment-speed research is complete; it remains a separate sensitivity dimension.
Stage 2D 0% versus 5% cash-floor sensitivity is complete; 5% remains the Phase 2E baseline.
Stage 2E protocol is frozen in docs/PHASE2E_PROTOCOL.txt.

PHASE 2E FROZEN ROBUSTNESS TESTS
A. Four chronological walk-forward/regime folds on common and expanding histories.
B. Leave-one-asset-out universe sensitivity on the current Phase 2 target universe.
C. Six pre-registered cost/slippage scenarios: 0/0, 10/0, 0/5, 10/5, 20/10, 30/20 bps.
D. External-universe generalization on the frozen 12-ETF Phase 1 external universe.
E. Newly reserved 10-ETF holdout: VUG, VTV, VEA, BND, LQD, SHY, DBC, XLF, XLK, VOO.
F. Circular moving-block bootstrap: 3/6/12 months, 6-month primary, 5,000 replicates, fixed seed 20260926, development universe only.

Core Phase 2E configuration: S1-S4, D3, 5% cash floor, zero initial capital, USD 1,000/month contribution, frozen daily/weekly ATR mechanics and baseline costs. Initial/extraordinary-capital deployment is not selected inside Stage 2E.

No Stage 2E result may alter definitions after inspection. No final Phase 2 strategy/rule set is selected until the complete 2A-2E evidence is synthesized.
