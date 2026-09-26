# Portfolio Strategy Lab

Reproducible research comparing investment strategy families before any user-specific strategy.

## START HERE
Read docs/README_RESEARCH_MAP.txt, docs/PHASE1_PROTOCOL.txt, docs/PHASE1B_PROTOCOL.txt, and docs/PHASE2_PROTOCOL.txt before continuing.

## Current status — 2026-09-26
Phase 1 is COMPLETE. Phase 1B fixed-ensemble extension is CLOSED. Phase 2 is ACTIVE — Stage 2A entry-engine research is running.

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


## Phase 2 current stage
Stage 2A is testing the frozen daily ATR/pullback entry engine before initial-capital deployment variants. See docs/PHASE2_PROTOCOL.txt, docs/PHASE2_CHECKLIST.csv and docs/PHASE2_RESULTS_LOG.txt.
