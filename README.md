# Portfolio Strategy Lab

Reproducible research comparing investment strategy families before any user-specific strategy.

## START HERE
Read docs/README_RESEARCH_MAP.txt, docs/PHASE1_PROTOCOL.txt, docs/PHASE1B_PROTOCOL.txt, and docs/PHASE2_PROTOCOL.txt before continuing.

## Current status — 2026-09-26
Phase 1 is COMPLETE. Phase 1B fixed-ensemble extension is CLOSED. Phase 2 is ACTIVE — Stage 2A initial screen is complete and Stage 2B/later robustness work is pending.

Phase 1 compared Buy & Hold, DCA, Momentum, Rotation, Moving Average, Dynamic Allocation and Risk Parity. Value is intentionally omitted until comparable point-in-time historical valuation data are available; it is not treated as a failed strategy.

Phase 1 completed common/expansive histories, walk-forward, robustness and sensitivity tests, external-universe validation, reserved holdout and statistical uncertainty. No robust Phase 1 winner was established.

Phase 1B then tested three frozen fixed-weight ensembles:
- C1: 50% B0 + 50% Momentum
- C2: 50% Momentum + 50% Dynamic Allocation
- C3: 1/3 B0 + 1/3 Momentum + 1/3 Dynamic Allocation

C2 was the closest combination, but it did not consistently improve S5 Dynamic Allocation across common and expansive histories; C1 and C3 showed severe expansive-history drawdowns. No robust Phase 1B improvement was established.

Phase 1B was therefore closed after development plus walk-forward screening. Later ensemble cost/holdout/bootstrap tests were not used because no candidate survived the initial robustness gate.

Final Phase 1 synthesis: reports/PHASE1_FINAL_SYNTHESIS_2026-09-26.txt
Final Phase 1B synthesis: reports/PHASE1B_FINAL_SYNTHESIS_2026-09-26.txt

## Research rules
- Freeze definitions/config/data before evaluating results.
- Never optimize parameters or weights after seeing results.
- Robustness matters more than peak CAGR.
- Do not declare a winner from a single metric or period.
- Do not use Phase 2 concepts to alter Phase 1/1B.
- At the beginning of every step, reread the research map and applicable protocol.
- At the end of every step, update durable documentation.

## Repository
- tickers/ — historical CSV inputs.
- scripts/run_phase1.py — Phase 1 baseline.
- scripts/run_strategy_robustness.py — Phase 1 robustness.
- scripts/run_walkforward_robustness.py — Phase 1 walk-forward.
- scripts/run_phase1_sensitivity.py — Phase 1 parameter/universe sensitivity.
- scripts/run_phase1_external_universe.py — Phase 1 external-universe validation.
- scripts/run_phase1b.py — frozen Phase 1B ensemble screen.
- docs/ — durable protocols, status and results logs.
- reports/ — reproducible reports.

The ATR/pullback strategy belongs exclusively to Phase 2 and was not used in Phase 1 or Phase 1B.

## Phase 1 data-continuity audit — 2026-09-26
The Phase 2A missing-price issue does not apply to the frozen Phase 1 backtest engine. Phase 1 uses src/backtest.py, which maintains a mark_prices series and updates each asset only when a valid execution price exists; held positions continue to be marked at the latest valid price rather than being dropped from equity. Therefore the specific Phase 2A discontinuity found in run_phase2a.py could not have generated the Phase 1 results.

This audit does not reopen or alter Phase 1. It documents the engine-level distinction so Phase 2 corrections remain isolated from the closed Phase 1/1B results.

## Phase 2A checkpoint — 2026-09-26
Run 7 on commit 01fd4a06581fea55e0b815cc4fff826f48633c37 was rejected because held positions could disappear from daily equity when a daily close was unavailable.

Commit 42391fdfcae01c07d8c6f11d45b8bea80793e761 corrected that data-continuity issue by carrying forward the latest valid close and preserving pending orders when a valid execution open was temporarily unavailable. This was an engine/data-integrity correction, not a strategy or parameter change.

Run 8 completed successfully on the corrected engine and produced finite metrics plus the expected artifact. It tested all frozen S1-S4 strategies under D1/D2/D3 on common and expanding histories. Common-history CAGR was approximately 27.3%-28.5% with max drawdowns approximately -24.7% to -29.6%; expanding-history max drawdowns remained approximately -89.5% to -90.7%. These results are descriptive and do not establish a winner.

Stage 2A is therefore no longer blocked by the previously identified integrity issue, but Phase 2 remains open. Stage 2B rule reconciliation is complete with D3 frozen as the operational simultaneous-capital rule. Stage 2C deployment-speed research is frozen in docs/PHASE2C_PROTOCOL.txt and implemented in scripts/run_phase2c.py with workflow .github/workflows/phase2c.yml. The workflow has not started automatically from the connector-created workflow commit, so a manual GitHub Actions dispatch is currently required to execute Stage 2C. Cash-floor sensitivity, walk-forward, universe robustness, cost sensitivity, external holdout and statistical uncertainty remain pending.

## Phase 3 — preliminary
docs/PHASE3_PROTOCOL.txt defines the preliminary Phase 3 scope: integration of the strategy/rule set selected only after the Phase 1 + Phase 2 robustness gates into the investment platform, with two operating modes:
- Semi-automatic: generate proposed purchase orders and require explicit user confirmation before broker submission.
- Automatic: generate and submit orders after all frozen eligibility, allocation, duplicate-order, market-status, reconciliation and safety checks pass, with explicit enable/disable and emergency-stop controls.

Phase 3 is blocked until the research phases identify and freeze a strategy/rule set for integration. Phase 3 must not alter research logic retrospectively.
