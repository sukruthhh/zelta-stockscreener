# Backend grading and historical evaluation evidence

## Outcome

Backend work can produce useful evidence without hosted deployment. This milestone fixes seven
reproduced grading defects, adds versioned evaluation provenance, and evaluates the unchanged
technical model on a saved historical market-data snapshot. It does not demonstrate an investing
advantage: the model matched an always-up baseline on the evaluated sample.

## Corrected product grading

`calendar-5d-next-session-v2` uses five calendar days after the prediction's generation date in
America/New_York. The first provided completed closing session on/after that date is eligible,
with at most seven further calendar days allowed for a missing/weekend/holiday session. Today's
daily bar is never graded, even after market close; grading conservatively waits until the next
New York date. No exchange-calendar dependency was added, so “first session” means the first
session actually returned by the provider, not independently verified exchange-calendar coverage.

Each new saved prediction carries the target policy version; each grade records the actual
session date. Old pending targets and old grades without this provenance are counted separately,
not silently reinterpreted or erased. Invalid/non-positive prices, Neutral/unchanged target
levels, stale/incomplete result statuses and unversioned mock-generator rows are ineligible.
An unchanged realized price is not a correct bearish prediction. A provider exception for one
prediction no longer aborts subsequent predictions. Updates only count as saved if the row was
still pending under the expected policy; repeat runs do not overwrite completed grades.

`before.txt` records seven failing regression cases against revision
`34f5acaf2d57dcadf81ea71fa8188c6a120ed95c`. The final suite passes **142 tests**, including the
regressions, real PostgreSQL provenance/eligibility checks, and tests that modifying future
prices cannot change earlier model calls. The injected fetcher now returns a dated observation;
the same regression scenarios were adapted to that stronger contract. Frontend lint and a
webpack production build also pass. The frontend labels the old absolute-error field as
“Risk-bound distance” because ATR bounds are not calibrated point-price forecasts.

## Real data experiment

Before fetching data, the script fixed this workload: AAPL, MSFT and SPY; January 1, 2024 through
January 1, 2026 exclusive; seed 31337; a candidate every five provided sessions after the minimum
50-session history. The source was Yahoo Finance through existing pinned yfinance 0.2.65 with
adjusted daily OHLCV. Each symbol returned 502 records: **1,506 source records total** with no
download failures. No OpenAI/Finnhub calls, paid APIs or product-database writes were involved.

For each candidate, the engine receives only the price prefix ending on that signal date.
Signals are generated after that day's close. This is a retrospective directional diagnostic;
it assumes a comparison to the snapshot close and does not model executable trades. Historical
news is excluded. The technical weights were unchanged for this experiment.

| Sample accounting | Count |
| --- | ---: |
| Candidate assessments | 273 |
| Directional calls before exclusions | 197 (72.2%) |
| Eligible calls compared across every strategy | 181 (66.3% of candidates) |
| Excluded as Neutral | 73 |
| Excluded for dividends/splits within the horizon | 16 |
| Excluded for a missing target close | 3 |

Exclusions are applied in order, so categories are mutually exclusive. There are 76 Neutral
assessments in total; three are counted under missing target close instead. Both directional-call
coverage and eligibility fraction are retained to avoid conflating abstention with missing data.

| Strategy on the same 181 eligible calls | Correct | Directional hit rate |
| --- | ---: | ---: |
| Zelta technical model | 108 | 59.7% |
| Always up | 108 | 59.7% |
| Sign of five-day price momentum | 100 | 55.2% |
| Seeded random up/down | 88 | 48.6% |

The random generator uses seed 31337 separately for each symbol. This is one reproducible
realization, not a claim that random guessing has an empirically fixed 48.6% success rate.
Momentum uses the same indicator rounding as the product. Ties count as incorrect directional
calls; the model's Neutral calls are excluded and every baseline uses that same selected sample.

| Symbol | Eligible calls | Zelta correct | Always-up correct |
| --- | ---: | ---: | ---: |
| AAPL | 57 | 33 | 34 |
| MSFT | 59 | 37 | 34 |
| SPY | 65 | 38 | 40 |

Zelta underperformed always-up on AAPL and SPY and outperformed it on MSFT. Aggregated, there
was no improvement over always-up. Do not select only MSFT or only the momentum comparison for
a resume or performance claim. The result supports keeping predictive-superiority claims out
of the product and prioritizing reliable, explainable workflows.

## Reproduction and retained trials

The original downloaded snapshot is retained locally at
`backend/data/local/yahoo-2024-2025.json` and is ignored by Git. Its SHA-256 is recorded in the
public result manifests. A fresh provider download may differ because adjusted history can be
revised; reproducing the exact artifact requires the retained snapshot.

From the repository root, run the isolated test environment and offline replay:

```powershell
docker compose -p zelta-validation -f compose.test.yml run --rm tests
docker compose -p zelta-validation -f compose.test.yml run --rm --volume "${PWD}/backend/data/local:/snapshots:ro" --volume "${PWD}/docs/evidence/2026-11-06/grading:/evidence" -e ZELTA_SOURCE_REVISION=<revision> tests python scripts/evaluate_assessments.py --snapshot /snapshots/yahoo-2024-2025.json --output /evidence/new-replay.json
docker compose -p zelta-validation -f compose.test.yml --profile smoke down
```

To fetch a new snapshot, omit `:ro`, choose a new snapshot filename, and add `--fetch`. This
contacts Yahoo through yfinance; it does not use paid embedding APIs. The script refuses to
overwrite an existing snapshot or output. Download and per-symbol evaluation failures are
retained and cause a nonzero exit. Run with `PYTHONPATH` pointing at `backend` outside Compose.

Evidence under `docs/evidence/2026-11-06/grading/` includes:

- `before.txt`: seven reproduced failures before the fix.
- `after.txt`: final full-suite result, 142 passed with one existing dependency deprecation warning.
- `historical.json`: initial trial using unrounded entry closes (107/181 for both model and always-up).
- `historical-final.json`: entry/momentum rounding aligned with stored product indicators (108/181).
- `historical-verified.json` and `historical-replay.json`: final corrected coverage definitions and
  failure retention. Offline replays produced byte-identical artifacts, SHA-256
  `e9e0fed7c3c23e9586a87c24a625e8e7977418eb9fae2745002f0debdcf228b9`.
- Corresponding stdout, frontend checks and environment/source hashes.

The initial trial and intermediate artifacts remain intact; the rounding correction changed one
outcome for both Zelta and always-up. Coverage was also clarified to distinguish generated calls
from eligibility after exclusions. No model weights were tuned or trials discarded to improve
the headline result. These historical records never populate the live prediction-performance API.

## Limits and defensible resume use

Three selected, correlated instruments and one retrospective period cannot establish general
predictive usefulness. Current-vintage adjusted history is not a point-in-time market feed;
corporate-action exclusions use hindsight and do not describe a deployable live strategy. Missing
provider sessions are not independently reconciled with an exchange calendar. Some outcomes
across dates/assets are correlated. There is no prospective holdout, slippage, transaction-cost,
liquidity, portfolio-return or calibrated-probability evaluation. Report descriptive counts and
rates; do not present a naive independent-binomial interval or a superiority claim.

SWE: “Made stock-signal evaluation reproducible across 1,506 historical price records by fixing
date-selection defects, persisting grading provenance, and comparing 181 eligible calls against
three baselines.”

PM: “Benchmarked a stock screener against three baselines and found its 59.7% directional hit
rate matched always-up; defined eligibility and disclosure rules to prevent unsupported accuracy
claims.”

These describe delivered engineering and analytical decisions, not adoption, user time saved,
profitable trading or validated forecast superiority. The next independent backend milestone can
measure job completion, failure recovery and processing time through the real database without
waiting for the hosted frontend.
