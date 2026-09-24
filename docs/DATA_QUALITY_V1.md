# Dataset validation — v1

Source: BOLSA HISTORICOS corregido.xlsx

## Result
- `Copia de QQQ`: absent.
- `IBIT`: absent; `BTC` present.
- Target portfolio weights sum to 100%.
- All non-BTC OHLC sheets have unique dates, valid OHLC relationships, positive closes, and no missing OHLC values.
- INDA uses `Vol.` instead of `Volume`; loader should normalize this field name.
- BTC contains 31 OHLC-consistency violations. These will be flagged/excluded from derived calculations rather than silently repaired.

## Coverage
- VT: 2008-06-26 → 2026-09-11
- SMH: 2000-05-11 → 2026-09-11
- BTC: 2010-07-18 → 2026-09-24
- INDA: 2012-02-06 → 2026-09-24
- MSFT: 2000-01-03 → 2026-09-11
- NVDA: 2000-01-03 → 2026-09-11
- AVGO: 2009-08-06 → 2026-09-11
- GLD: 2004-11-18 → 2026-09-11
- URA: 2010-11-05 → 2026-09-11
- XLE: 2000-01-03 → 2026-09-11
- VHT: 2004-01-30 → 2026-09-11
- PLTR: 2020-09-30 → 2026-09-11
- QQQ: 2000-01-03 → 2026-09-11

## BTC data-quality note
The BTC series has 31 rows where Open/High/Low/Close do not satisfy standard OHLC inequalities. Most are small inconsistencies, but at least one row is materially anomalous (2014-02-26). Because the research uses weekly OHLC/ATR, silently correcting these values would introduce assumptions. Phase 1 will flag invalid BTC bars and exclude them from calculations that depend on their OHLC values.

## Decision
Dataset is structurally usable for the backtester after validation/normalization. The BTC anomalies remain visible in the data-quality log and are handled deterministically.


## Loader verification update

The source workbook layout was checked against the actual spreadsheet structure: each asset sheet contains a metadata row followed by the OHLC header row. The loader now locates the row containing `Date` rather than assuming the first row is the header.

A recheck of the corrected workbook finds:
- 0 invalid OHLC rows for every non-BTC asset.
- 33 invalid OHLC rows for BTC.
- The two additional BTC rows are 2010-08-30 and 2010-10-08; both contain a zero Low and are therefore excluded under the same deterministic validation rule.
- No correction is fabricated; invalid BTC OHLC observations remain flagged/excluded from OHLC-derived calculations.
