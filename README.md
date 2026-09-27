# Portfolio Strategy Lab

Reproducible research comparing investment strategy families before any user-specific strategy.

## START HERE
Read docs/README_RESEARCH_MAP.txt, docs/PHASE1_PROTOCOL.txt, docs/PHASE1B_PROTOCOL.txt, and docs/PHASE2_PROTOCOL.txt before continuing. For Stage 2E execution read docs/PHASE2E_PROTOCOL.txt. For the post-Phase-2 rebalancing extension read docs/PHASE2F_REBALANCE_PROTOCOL.txt.

## Current status — 2026-09-27
Phase 1 is COMPLETE. Phase 1B fixed-ensemble extension is CLOSED. Phase 2 frozen robustness gate is COMPLETE: Stage 2A, 2B, 2C, 2D and 2E are complete. Phase 2E did not establish a robust universal separation among S1-S4, so no Phase 2 strategy winner is declared. A separate post-Phase-2 hybrid rebalancing sensitivity (Phase 2F) is now being executed; it does not modify the frozen Phase 2 definitions.

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

## Phase 2C failed-dispatch checkpoint — 2026-09-26
The first manual GitHub Actions dispatch of Stage 2C failed before research execution because scripts/run_phase2c.py contained literal \\n characters inside the result pd.concat expression, causing a Python syntax error. No Phase 2C results were produced or interpreted from that failed run.

Commit a88ba1b78532b0d5e26a970f69cae30753a09698 corrected only that syntax defect. The frozen Phase 2C protocol, deployment schedules, D3 rule, data and strategy definitions were not changed. The next action is to rerun the existing GitHub Actions workflow; no research definition needs to be revisited.


## Phase 2C second-failure checkpoint — 2026-09-26
The second manual dispatch (run 4, workflow run 36260808659) failed with the same syntax error because the prior correction accidentally wrote the two-character sequence \\n into the Python source rather than real line breaks. The GitHub job log confirms the failure at line 364 with SyntaxError: unexpected character after line continuation character; execution stopped before any Phase 2C calculations.

Commit ff0249456bc2038408bcd5baacdf23c0859a1852 now replaces that entire result-concatenation block with actual Python line breaks. The corrected file was re-read from GitHub and verified in the relevant block. No Phase 2C research definitions were changed.


## Phase 2C completion checkpoint — 2026-09-26
Stage 2C executed successfully in GitHub Actions run 5 (36260873980) after the line-ending correction in commit ff0249456bc2038408bcd5baacdf23c0859a1852. The artifact phase2c-deployment-speeds was extracted and validated. All six pre-registered deployment schedules were tested across S1-S4 with D3, 5% cash floor and common/expanding histories. Common-history results show a material deployment-speed effect, with scheduled 6-12 month deployment producing higher contribution-flow-adjusted return metrics than immediate deployment; 24 months moderates, and opportunities-only serves as the pre-registered no-forced-deployment control. No strategy or schedule is declared a winner. Stage 2C is now complete; Stage 2D cash-floor sensitivity is next. Research definitions remain frozen.


## Phase 2D first execution checkpoint — 2026-09-26
Phase 2D workflow run 1 (36263098087) reached the research script but failed before calculations because the temporary runpy copy of run_phase2a.py recomputed ROOT from its /tmp location, causing portfolio_allocation.csv to be searched under /tmp. No Phase 2D results were produced or interpreted from this run.

Commit eaa69b7a845e718f2c5cc9dd15d9a9bc8ee3a1a7 corrected only the Phase 2D wrapper so the patched temporary engine retains the repository ROOT. The frozen Phase 2A engine, Phase 2D protocol, strategy definitions, D3 rule, data and cash-floor comparison remain unchanged. The next push-triggered Phase 2D run must be validated before interpreting results.


## Phase 2D completion checkpoint — 2026-09-26
Stage 2D run 2 (workflow 36263161838) completed successfully after the wrapper root-path correction. The artifact phase2d-cash-floor was extracted and validated.

The frozen comparison tested 0% cash floor versus the validated 5% baseline using the same S1-S4 strategies, D3 deepest-first allocation, daily trigger evaluation, weekly HH52/Wilder ATR20W, USD 1,000/month recurring contributions, zero initial capital, costs and universe. The 0% run itself completed with finite metrics.

On the common 2020-09-30 to 2026-09-24 history, 0% cash-floor results were:
- S1: CAGR ~28.37%, max drawdown ~-29.27%, Sharpe ~1.068, cash utilization ~81.0%.
- S2: CAGR ~27.27%, max drawdown ~-24.73%, Sharpe ~1.115, cash utilization ~70.7%.
- S3: CAGR ~28.41%, max drawdown ~-29.26%, Sharpe ~1.069, cash utilization ~80.9%.
- S4: CAGR ~28.93%, max drawdown ~-25.69%, Sharpe ~1.127, cash utilization ~77.1%.

The corresponding expanding-history results remain subject to the previously observed extreme drawdowns (~-89.6% to -90.7%), so they are descriptive rather than evidence of robustness.

Phase 2D does not promote a strategy or alter the frozen baseline. Its role is to establish whether conclusions are materially sensitive to removing the 5% cash floor. Full interpretation requires direct comparison with the validated 5% baseline and then the remaining pre-registered robustness gates (walk-forward, universe, cost, external holdout and statistical uncertainty).


## Phase 2E protocol-freeze checkpoint — 2026-09-26
Stage 2E was frozen before execution in docs/PHASE2E_PROTOCOL.txt. The robustness set covers temporal folds, leave-one-asset-out universe sensitivity, six pre-registered friction scenarios, external-universe generalization, a newly reserved holdout, and circular moving-block bootstrap uncertainty. No Stage 2E result may change frozen definitions after inspection. Phase 3 remains blocked until the complete Phase 2 robustness gate is synthesized.


## Phase 2E execution checkpoint — 2026-09-26
The frozen Stage 2E suite is implemented in scripts/run_phase2e.py and .github/workflows/phase2e.yml. The implementation covers the pre-registered temporal, leave-one-asset-out, cost, external-generalization, newly reserved holdout and bootstrap tests without changing the frozen strategy definitions. The first workflow execution must be validated for engine integrity and artifact completeness before any Phase 2E results are interpreted.


## Phase 2E first execution — 2026-09-26
The installed Phase 2E workflow was triggered by the frozen script commit e530f374f4a6e689a569d6bfb526177ac9ae6f3f. Results remain uninterpreted until the GitHub Actions run and artifact are validated.


## Phase 2E first execution validation — 2026-09-26
The first frozen Stage 2E workflow (36266398095) completed successfully and uploaded all 10 expected artifact files. However, artifact validation found an integrity inconsistency: the external-generalization and reserved-holdout result rows report an end date of 2026-12-08 even though the frozen protocol cutoff is 2026-09-24 and the fetched Yahoo coverage files both end on 2026-09-24. The results are therefore **not interpreted** and Stage 2E is not marked complete.

This is treated as an execution/data-calendar integrity defect, not a strategy result. A guard has been added to scripts/run_phase2e.py so future runs fail rather than silently accepting a result calendar beyond the frozen cutoff or fetched coverage. The next step is to rerun the frozen suite, diagnose the underlying date propagation if the guard trips, and only then validate and synthesize the results. No Phase 2 definitions, parameters, candidates, weights or evaluation rules are changed.

## Phase 2E second execution checkpoint — 2026-09-26
The frozen Stage 2E rerun (workflow 36267441523) failed at the new integrity guard before artifact publication: the external-generalization result still reached 2026-12-08 while the protocol/download cutoff is 2026-09-24. The failure confirmed the guard is working, but the underlying calendar propagation defect required further isolation.

The diagnosis points to the shared OHLC date-normalization boundary as the next integrity point. The loader now parses ISO/YMD dates explicitly with ISO8601 while retaining day-first parsing for legacy exports, and Phase 2E now validates raw Yahoo coverage, parsed ticker coverage, and simulation result dates separately. A regression test was added for both ISO and legacy D/M/Y inputs. No strategy definitions, parameters, weights, data windows or candidate rules were changed.

The next action is to validate the new loader/diagnostic commit through GitHub Actions before interpreting any Stage 2E result.


## Phase 2E completion — 2026-09-26
The frozen Phase 2E robustness gate completed successfully in run 5 (commit dc74ce1381e59b7e1e3972fd781e7af14f6f0d35). Calendar integrity passed through the 2026-09-24 cutoff. Walk-forward, leave-one-asset-out universe sensitivity, six friction scenarios, external 12-ETF generalization, reserved 10-ETF holdout and 5,000-replicate circular moving-block bootstrap all completed.

The combined evidence does not establish a robust universal separation among S1-S4. S1 and S3 remain nearly indistinguishable; S2 and S4 show different return/drawdown/cash-utilization profiles rather than consistent dominance. No post-result parameter, strategy, allocation, cash-floor or deployment definition was changed.

Phase 3 remains blocked. Any further research is a separate extension and must not reopen the frozen Phase 2E definitions.

## Phase 2F — post-Phase-2 hybrid rebalancing sensitivity — 2026-09-27
Phase 2F is a separate sensitivity extension defined in docs/PHASE2F_REBALANCE_PROTOCOL.txt and implemented in scripts/run_phase2f_rebalance.py with workflow .github/workflows/phase2f_rebalance.yml.

All frozen S1-S4 candidates are tested because Phase 2E did not establish a robust winner. The comparison is baseline/no overlay versus contribution-first hybrid rebalancing with sale thresholds of 20% and 30% relative overweight. The monthly USD 1,000 contribution and 50% DCA / 50% dip-or-ATR8 structure are preserved; the DCA half is directed to current underweights first, while existing holdings are sold only beyond the registered threshold.

Phase 2F results must first pass artifact and baseline-control validation. Thresholds are sensitivity cases, not post-result optimization parameters.


## Phase 2G — first-year contributions then nine-year hold — 2026-09-27
Phase 2G is a separate post-Phase-2 deployment-pattern extension defined in docs/PHASE2G_FIRST_YEAR_ONLY_PROTOCOL.txt and implemented in scripts/run_phase2g_first_year_only.py with workflow .github/workflows/phase2g_first_year_only.yml.

The frozen S1-S4 definitions are reused without modification. Each historical cohort receives USD 1,000 on the first observed trading day of each of its first 12 calendar months (USD 12,000 total), followed by zero new contributions for the remainder of an approximately 10-year horizon. Cohorts are annual historical windows plus the most recent available decade when the repository data permit it.

The key metric is post-contribution CAGR: annualized time-weighted growth from the final contribution date through the end of the cohort. This avoids incorrectly applying the recurring-contribution CAGR to a no-contribution holding period. Final-equity multiple, contribution-year ending equity and full-cohort drawdown are also recorded.

The Phase 2G implementation is complete; results must be validated from the GitHub Actions artifact before interpretation. A lump-sum-at-day-one scenario remains a separate sensitivity.
 
## Phase 2F execution results — 2026-09-27
The post-Phase-2 hybrid rebalancing sensitivity completed successfully in GitHub Actions run 36291833551. The artifact passed validation with 24 rows covering S1-S4, baseline/hybrid20/hybrid30 and common/expanding histories. Durable results are recorded in reports/PHASE2F_REBALANCE_2026-09-27.txt.

On the common 2020-09-30 to 2026-09-24 history, baseline CAGR was approximately 27.87%-28.13% with max drawdown -25.20% to -29.41%. Hybrid20 reduced CAGR to approximately 22.76%-23.67% while leaving max drawdown almost unchanged (-25.16% to -29.37%). Hybrid30 produced approximately 23.09%-24.16% CAGR with similarly little drawdown change (-25.16% to -29.37%). Sharpe was modestly higher in the hybrid cases, but cumulative rebalance turnover was substantial (~0.31-0.39 in the common history).

The expanding-history hybrid overlays materially reduced the previously observed ~-89% to -91% drawdowns to roughly -30% to -35%, but also reduced CAGR substantially. These are descriptive observations, not a basis for selecting a threshold. Phase 2F therefore provides no evidence that contribution-first hybrid rebalancing should replace the frozen Phase 2 baseline for the recurring-contribution case. It remains an implementation sensitivity where tighter weight control is preferred despite lower historical growth and additional sales.
