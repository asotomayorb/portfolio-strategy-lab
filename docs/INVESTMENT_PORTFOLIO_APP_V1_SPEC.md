# Investment Portfolio App — V1 scope freeze

**Status:** Scope proposal frozen for the first implementation slice  
**Date:** 2026-11-11  
**Purpose:** Build a small, usable personal portfolio-monitoring application without coupling it to the research/backtest project.

## 1. Product objective

Give one user a reliable view of their investment portfolio: holdings, allocation, cash, reference prices, data freshness and a small set of descriptive indicators. The first release is a monitoring tool, not an autonomous investment adviser or trading system.

## 2. V1 user and operating mode

- Single user; private/local deployment during the first release.
- USD is the portfolio reporting currency; retain each instrument's native currency where relevant.
- Desktop-first responsive web interface.
- Read-only with respect to the broker. No orders are sent.
- Demo mode must work without credentials, external APIs or broker access.

## 3. Included in the first usable version

1. **Portfolio overview:** total portfolio value, cash, invested value, daily change when available, and allocation by instrument.
2. **Holdings:** ticker, name, asset type, quantity, average cost (optional), reference price, market value, portfolio weight and target weight.
3. **Portfolio editing:** add/remove instruments and edit quantities, cash and target weights. Clearly distinguish target allocation from actual holdings.
4. **Data status:** source, timestamp, currency and freshness for each price. Missing or stale values must be visible; never silently reuse a stale quote as current.
5. **Basic indicators:** available price history, 52-week high and 20-week ATR only when sufficient valid observations exist. Otherwise show “insufficient history”; never fabricate values.
6. **Demo data:** clearly labelled synthetic/sample prices so all screens and calculations can be tested before connecting an external provider.
7. **Persistence:** save the user's portfolio locally and allow export/import of a simple CSV backup.

## 4. Explicitly out of scope for V1

- Sending, modifying or cancelling IBKR orders.
- Automatic trading, leverage, CFDs or margin use.
- Selecting a winning Phase 1/Phase 2 strategy; the research did not establish a robust universal winner.
- Buy/sell recommendations or live order proposals until the user explicitly freezes operating rules.
- Multiple brokers, multiple users, public deployment, subscriptions or monetization.
- Complex analytics, backtesting, optimization, tax-lot accounting, news, social features or notifications.
- Supporting every asset class and exchange. Start with the current portfolio universe; new instruments may be added manually and must display partial data honestly.

## 5. Staged implementation

### Stage 0 — usable shell (first human test)

- Build the dashboard with demo data and local persistence.
- Load the current portfolio instrument list and target weights as initial defaults, not as actual positions.
- Let the user enter actual quantities and cash.
- Validate portfolio totals, weights, editing, reload/persistence and CSV round-trip.
- No API keys, broker connection or cloud services.

**Exit gate:** the user can open the app, edit a holding, see totals/weights update, restart the app without losing changes, and export/import the portfolio without errors.

### Stage 1 — market data

- Add one provider behind a small vendor-neutral interface.
- Start with current reference prices; show source and timestamp.
- Do not add a second provider unless the first fails a defined coverage or quality requirement.
- Keep external reference prices separate from executable broker prices.

**Exit gate:** all supported instruments show either a validated reference price or an explicit unavailable/stale state.

### Stage 2 — indicators

- Add historical OHLC only where required.
- Calculate HH52 and ATR20W only when their observation requirements are met.
- Add automated tests for splits, missing bars, duplicate dates, malformed OHLC and insufficient history.
- Do not calculate technical indicators from dividend-adjusted close.

**Exit gate:** indicator outputs pass deterministic fixtures and data-integrity tests.

### Stage 3 — IBKR read-only

- Read positions, cash and pending orders.
- Reconcile broker quantities against the locally stored portfolio.
- Display discrepancies; never silently overwrite user data.
- Do not request trading permissions.

**Exit gate:** read-only account data can be reconciled and stale/disconnected broker state is clearly indicated.

### Stage 4 — rule-based proposals (separate approval)

Only after the user selects and freezes an operating rule set, define a separate proposal workflow. Every proposal must pass allocation-room, pending-order, price-freshness, market-status and broker-quote checks and require explicit user confirmation. Automatic order submission remains out of scope.

## 6. Minimal technical approach

- Python application with Streamlit for the first local UI.
- Small modular structure: ui, portfolio, market_data, indicators, storage.
- Local SQLite storage; CSV import/export for portability.
- One provider adapter at a time; demo provider is the default in Stage 0.
- Unit tests for calculations and data normalization, plus one end-to-end smoke test.
- One lightweight CI workflow for tests. No workflow per feature and no cloud infrastructure in V1.

This stack is a speed-oriented implementation choice, not a permanent architectural constraint. Reassess only if a concrete V1 requirement cannot be met.

## 7. Data and safety rules

- Target weights are not actual holdings.
- Every price carries source, currency and observation timestamp.
- Stale, missing, malformed or mismatched data is never presented as live.
- Historical data and live reference prices are distinct from executable bid/ask quotes.
- IBKR is read-only in V1; no order endpoint or trading permission is implemented.
- Secrets stay outside source control and application logs.
- Do not expose provider data to other users; commercial licensing is a separate future gate.

## 8. Definition of done for V1

V1 is complete when the user can:
1. Open the local application without configuring credentials.
2. See the current portfolio universe and target weights as editable defaults.
3. Enter actual holdings and cash.
4. View correct portfolio value, weights and allocation calculations.
5. See demo/reference-price provenance and data freshness.
6. Close and reopen the app without losing local changes.
7. Export and re-import the portfolio successfully.
8. Run the automated tests successfully.

No live broker connection or trade execution is required to call V1 usable.

## 9. Project boundary

This specification is stored temporarily in the research repository for traceability. The application source code should live in a separate GitHub repository when implementation begins. The research repository remains the historical record for Phase 1/Phase 2 and provider evaluations; application code must not be added to its backtest engine or research workflows.