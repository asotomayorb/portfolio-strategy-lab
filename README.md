# Portfolio Strategy Lab

Reproducible research comparing investment strategy families before any user-specific strategy.

## START HERE
Read docs/README_RESEARCH_MAP.txt, docs/PHASE1_PROTOCOL.txt, docs/PHASE1B_PROTOCOL.txt, and docs/PHASE2_PROTOCOL.txt before continuing. For Stage 2E execution read docs/PHASE2E_PROTOCOL.txt. For the post-Phase-2 rebalancing extension read docs/PHASE2F_REBALANCE_PROTOCOL.txt.

## Current status — 2026-09-27
Phase 1 is COMPLETE. Phase 1B fixed-ensemble extension is CLOSED. Phase 2 frozen robustness gate is COMPLETE: Stage 2A, 2B, 2C, 2D and 2E are complete. Phase 2E did not establish a robust universal separation among S1-S4, so no Phase 2 strategy winner is declared. Post-Phase-2 extensions 2F, 2G and 2H are complete; they do not modify the frozen Phase 2 definitions.

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

All frozen S1-S4 candidates are tested because Phase 2E did not establish a robust winner. The comparison is contribution-only reweighting (future contributions correct current underweights, with no sales) versus contribution-first hybrid rebalancing with sale thresholds of 20% and 30% relative overweight. The monthly USD 1,000 contribution and 50% DCA / 50% dip-or-ATR8 structure are preserved; the DCA half is directed to current underweights first, while existing holdings are sold only beyond the registered threshold.

Phase 2F results passed artifact and baseline-control validation. Thresholds are sensitivity cases, not post-result optimization parameters.


## Phase 2G — first-year contributions then nine-year hold — 2026-09-27
Phase 2G is a separate post-Phase-2 deployment-pattern extension defined in docs/PHASE2G_FIRST_YEAR_ONLY_PROTOCOL.txt and implemented in scripts/run_phase2g_first_year_only.py with workflow .github/workflows/phase2g_first_year_only.yml.

The frozen S1-S4 definitions are reused without modification. Each historical cohort receives USD 1,000 on the first observed trading day of each of its first 12 calendar months (USD 12,000 total), followed by zero new contributions for the remainder of an approximately 10-year horizon. The validated run covered 18 cohorts.

Post-contribution CAGR medians across the 18 cohorts were approximately 60.25% (S1), 42.42% (S2), 60.24% (S3), and 59.40% (S4). Median final-equity multiples were 91.95x, 25.21x, 91.93x and 88.30x respectively. Median full-cohort max drawdowns were approximately -86.34%, -76.53%, -86.34% and -86.33%. The outcomes are highly dispersed and descriptive historical observations, not forecasts or expected returns; no Phase 2 winner is declared.

A separate lump-sum-at-day-one scenario is Phase 2H.
 
## Phase 2F execution results — 2026-09-27
The post-Phase-2 hybrid rebalancing sensitivity completed successfully in GitHub Actions run 36291833551. The artifact passed validation with 24 rows covering S1-S4, contribution-only/hybrid20/hybrid30 and common/expanding histories. Durable results are recorded in reports/PHASE2F_REBALANCE_2026-09-27.txt.

On the common 2020-09-30 to 2026-09-24 history, baseline CAGR was approximately 27.87%-28.13% with max drawdown -25.20% to -29.41%. Hybrid20 reduced CAGR to approximately 22.76%-23.67% while leaving max drawdown almost unchanged (-25.16% to -29.37%). Hybrid30 produced approximately 23.09%-24.16% CAGR with similarly little drawdown change (-25.16% to -29.37%). Sharpe was modestly higher in the hybrid cases, but cumulative rebalance turnover was substantial (~0.31-0.39 in the common history).

The expanding-history hybrid overlays materially reduced the previously observed ~-89% to -91% drawdowns to roughly -30% to -35%, but also reduced CAGR substantially. These are descriptive observations, not a basis for selecting a threshold. Phase 2F therefore provides no evidence that contribution-first hybrid rebalancing should replace the frozen Phase 2 baseline for the recurring-contribution case. It remains an implementation sensitivity where tighter weight control is preferred despite lower historical growth and additional sales.

## Phase 2H — lump sum / ten-year hold — 2026-09-27
Phase 2H is a separate post-Phase-2 sensitivity for a single initial USD 12,000 investment followed by zero contributions for approximately ten years. Because the frozen S1-S4 labels contain a 50% DCA sleeve, the registered lump-sum adaptation deploys that 50% sleeve immediately, target-weighted, while the remaining 50% follows the corresponding frozen dip/ATR8 opportunity logic. This adaptation is documented in docs/PHASE2H_LUMP_SUM_PROTOCOL.txt and implemented in scripts/run_phase2h_lump_sum.py with workflow .github/workflows/phase2h_lump_sum.yml.

The validated run covered 18 cohorts. Ten-year CAGR medians were approximately 68.17% (S1), 51.09% (S2), 68.17% (S3), and 67.50% (S4). Median final-equity multiples were 182.31x, 62.88x, 182.29x and 175.39x respectively. Median max drawdowns were approximately -87.57%, -85.44%, -87.54% and -87.66%. The results are highly cohort-dependent and descriptive historical observations, not forecasts or expected returns; no Phase 2 winner is declared.


## Phase 1 + Phase 2 synthesis — 2026-09-27
The complete research set is now synthesized. Phase 1 does not produce a robust universal winner, and Phase 2E likewise does not establish a robust universal separation among S1-S4. Therefore the research does not justify declaring a single historically superior strategy from the frozen evidence.

For the user's stated decision priorities — (1) CAGR, (2) lower drawdown, (3) implementation simplicity — the evidence can be narrowed without pretending that the robustness gate selected a winner:
- Phase 1: S5 Dynamic Allocation provides the lowest common-history drawdown among the main families (about -21.2%) but lower common-history CAGR (about 22.3%). Momentum/Rotation and Buy & Hold have higher historical CAGR in some development histories but materially different drawdown/generalization behavior. No Phase 1 family is promoted as the universal choice.
- Phase 2 common-history baseline: S4 has the highest CAGR among S1-S4 (about 28.13%) and S2 has the lowest max drawdown (about -25.20%); S1 and S3 are effectively indistinguishable. These differences are small relative to the robustness uncertainty and must not be treated as a winner declaration.
- Phase 2F shows that adding sales to the contribution-only reweighting baseline reduced common-history CAGR substantially while leaving drawdown almost unchanged; it is therefore an implementation sensitivity rather than an improvement to the no-sale baseline.
- Phase 2G/2H show that the recurring-contribution CAGR cannot be reused for one-year-only contributions or a lump sum. Those extensions are scenario sensitivities, not candidate-selection tests.
- Phase 3 remains blocked until a human decision explicitly accepts the non-separating robustness evidence and freezes the operating rule set.

Practical research shortlist for the next decision step: retain S2 and S4 as the two materially distinct Phase 2 profiles (lower-drawdown profile versus higher-CAGR profile), while treating S1/S3 as near-duplicates for decision purposes. This is a descriptive shortlist, not a statistical or historical winner selection.


## Phase 2I — operational comparison — 2026-09-27
The completed research is now reduced to an operational comparison of S2 and S4 without reopening the frozen Phase 2E robustness gate. Durable details are recorded in docs/PHASE2I_OPERATIONAL_COMPARISON_2026-09-27.txt.

For the recurring-contribution implementation, the validated baseline is contribution-only reweighting: future DCA contributions correct current underweights first, with no existing-position sales. Phase 2F found that adding sales materially reduced common-history CAGR while changing drawdown very little.

The two retained profiles are:
- S2: 50% DCA + 50% ATR8; common-history CAGR 28.01%, max drawdown -25.20%, Sharpe 1.110.
- S4: 100% ATR8 when active, otherwise S1; common-history CAGR 28.13%, max drawdown -27.85%, Sharpe 1.091.

S2 therefore has the lower observed drawdown and simpler state structure; S4 has the slightly higher observed CAGR and a more conditional rule. These are descriptive differences, not a robust statistical winner. Phase 2G/2H remain separate capital-deployment sensitivities.

Phase 3 remains blocked until the human freezes the operating rule set.
