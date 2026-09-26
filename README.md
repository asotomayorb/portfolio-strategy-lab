# Portfolio Strategy Lab

Reproducible research comparing investment strategy families before any user-specific strategy.

## START HERE
Read docs/README_RESEARCH_MAP.txt, docs/PHASE1_PROTOCOL.txt, and docs/PHASE2_PROTOCOL.txt before continuing.

## Current status — 2026-09-26
**Phase 1 is NOT finished. Phase 2 must NOT start.**

Evaluated: Buy & Hold, DCA, Momentum, Rotation, Moving Average, Dynamic Allocation, Risk Parity. Value is intentionally omitted until comparable point-in-time historical valuation data are available; it is not treated as a failed strategy.

Completed: common/expansive histories, cross-history comparison, Pareto robustness, walk-forward, regime analysis, parameter-neighbor sensitivity, corrected leave-one-asset-out universe sensitivity, cost/slippage sensitivity, and concentration/dependence synthesis.

**Current step: external-universe validation.** A frozen 12-ETF universe is being evaluated with unchanged Phase 1 definitions. This is an external-universe generalization test, not fully independent temporal OOS, because its calendar period overlaps periods already observed in the original research.

**No robust Phase 1 winner has been established.**

## Research rules
- Freeze definitions/config/data before evaluating results.
- Never optimize parameters after seeing results.
- Neighbor tests measure stability, not parameter selection.
- Robustness matters more than peak CAGR.
- Do not declare a winner from a single metric or period.
- Do not use Phase 2 concepts to alter Phase 1.
- At the beginning of every step, reread the research map and Phase 1 protocol.
- At the end of every step, update the research map/protocol/checklist.

## Repository
- tickers/ — historical CSV inputs.
- scripts/run_phase1.py — baseline Phase 1.
- scripts/run_strategy_robustness.py — robustness comparison.
- scripts/run_walkforward_robustness.py — walk-forward.
- scripts/run_phase1_sensitivity.py — parameter/universe sensitivity.
- scripts/run_phase1_external_universe.py — frozen external-universe validation.
- docs/ — durable protocol, status and results log.
- reports/ — reproducible reports/results.

The ATR/pullback strategy belongs exclusively to Phase 2 and remains blocked.
