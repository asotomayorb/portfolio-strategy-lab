# Portfolio Strategy Lab

Reproducible research comparing investment strategy families before any user-specific strategy.

## START HERE
Read these files before continuing:
1. `docs/README_RESEARCH_MAP.txt` — short map, current status and next step.
2. `docs/PHASE1_PROTOCOL.txt` — complete Phase 1 protocol/checklist.
3. `docs/PHASE2_PROTOCOL.txt` — future Phase 2; currently **BLOCKED**.

## Current status — 2026-09-26
**Phase 1 is NOT finished. Phase 2 must NOT start.**

Evaluated: Buy & Hold, DCA, Momentum, Rotation, Moving Average, Dynamic Allocation, Risk Parity.
Value is intentionally omitted until comparable point-in-time historical valuation data are available; it is not treated as a failed strategy.

Completed: common/expansive histories, cross-history comparison, Pareto robustness, walk-forward, regime analysis, parameter-neighbor sensitivity, and corrected leave-one-asset-out universe sensitivity.

The validated universe test shows material dependence on individual assets for Momentum/Rotation and especially Risk Parity. Dynamic Allocation shows narrower dispersion in this test. These are descriptive robustness findings, not a ranking.

Pending: cost/slippage sensitivity, concentration/dependence synthesis, independent OOS, reserved holdout, statistical uncertainty, final Phase 1 synthesis.

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
- `tickers/` — historical CSV inputs.
- `scripts/run_phase1.py` — baseline Phase 1.
- `scripts/run_strategy_robustness.py` — robustness comparison.
- `scripts/run_walkforward_robustness.py` — walk-forward.
- `scripts/run_phase1_sensitivity.py` — parameter/universe sensitivity.
- `docs/` — durable protocol, status and results log.
- `reports/` — reproducible reports/results.

The ATR/pullback strategy belongs exclusively to Phase 2 and remains blocked.
