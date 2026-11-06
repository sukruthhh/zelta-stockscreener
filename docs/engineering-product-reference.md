# Zelta engineering and product reference

This records the first reliability checkpoint. See [the delivery plan](delivery-plan.md) for the
subsequent cache-freshness milestone, current remaining work and measurement contracts. The user
has since confirmed that no frontend/backend deployment exists yet.

## Objective and scope

Make the existing product understandable and reliable enough for a family member to analyze a
ticker and keep a personal watchlist. November 8, 2026 is a resume checkpoint, not a declaration
of product completion. The pasted working brief governs this work. The four Word documents in
the supplied ZIP describe historical plans; their agent, native Android, staffing, scale, and
performance language is not evidence of current functionality or accomplishments.

## Recovered state on November 6 2026

- Local starting revision: `bcfdbaa3b8872ffbfd8d0a76517dc2bd7b67568a`, matching `main` on
  `sukruthhh/zelta-stockscreener` through the connected GitHub API.
- Local `origin` points to `http://github.com/harshalas/zelta-stockscreener.git`, the parent
  repository. It was not rewritten. Untracked `frontend/android/` was preserved.
- Next.js / React / TypeScript frontend; Supabase email-link sign-in and JWT-protected FastAPI
  product routes; PostgreSQL / pgvector persistence; Redis caches for selected market endpoints.
- Current job path: submit ticker, fetch prices, optionally harvest and score news, calculate
  assessment, save result, retrieve status/result. FastAPI BackgroundTasks runs work in-process.
- Six technical indicator groups produce an explainable score. News uses embedding-vector
  similarity with a 30% weight when available. Generative agents are outside this path, but a
  deprecated authenticated experiment endpoint still exists. News embedding ingestion can incur
  OpenAI API charges; this checkpoint did not call it or regenerate anchors.
- The responsive PWA has manifest/icons and service-worker registration. Actual installation,
  offline behavior, delivered email links, and deployed user flows have not been verified here.
- The README provides deployment instructions. No production URL, running deployment, real
  users, or recurring backtest scheduler was established by this audit.

## Delivered reliability milestone

Optional news must not discard a valid technical result. Freshness lookup, harvesting, chunk
retrieval, anchor loading, scoring, and blending failures are covered by controlled tests. News
refresh failures may still use stored coverage, with a warning. Other news failures preserve the
technical assessment and explicitly disclose technical-only operation. Price-fetch and required
storage failures still fail the job.

Insufficient price history must not become a directional call because positive news is present.
The worker skips optional news for incomplete analysis, and the engine rejects blending into an
incomplete result. The UI displays “Assessment unavailable,” hides its score bars, and exposes
the market-data date. For valid assessments, the heuristic confidence field is labeled as a
computed signal score and explicitly distinguished from a probability of correctness.

Acceptance evidence includes HTTP submission/readback, persisted result timestamps, analysis
ownership, watchlist persistence, duplicate handling, deletion, cross-user isolation, and three
invalid-input cases. Authentication identity and external prices/news are test fixtures; JWT
verification against real Supabase and browser polling are not covered by those tests.

## Reproducible evidence

Run the commands in the README. `compose.test.yml` uses Python 3.12 and a separate PostgreSQL
16 database with pgvector, temporary storage, no published ports, and no paid-provider keys.
Direct Python dependencies retain existing pins. Transitive Python dependencies are not locked;
the captured environment lists the actual installed versions.

Evidence lives in `docs/evidence/2026-11-06/`:

- `backend-before.txt`: expanded regression suite against the original implementation:
  **7 failed, 66 passed**. This includes new tests, so it is not an untouched historical suite.
- `backend-after.txt`: **81 passed**, including seven HTTP acceptance cases and one additional
  engine guard test. Real database checks ran; no database tests were skipped.
- `backend-acceptance-collection-failed.txt`: retained intermediate failure caused by a syntax
  error while adding acceptance tests; corrected before the passing run.
- `frontend-lint.txt`: lint passed after excluding generated legacy Android files. They previously
  produced 10 errors and 1,891 warnings and are unrelated to the current PWA source.
- `frontend-build.txt`: retained failed Turbopack build. It failed starting a CSS worker both
  inside and outside the Windows sandbox after dependency restoration.
- `frontend-build-webpack.txt`: production build and TypeScript checks passed with the supported
  webpack option. This does not establish that the default Turbopack build works.
- `environment.json` and `python-packages.txt`: source hashes, starting revision, local runtime
  details, test image identifier, and installed backend packages.

The original Windows virtual environment contained pip but no pytest/application dependencies.
The existing frontend install also lacked Supabase. `npm ci` restored the existing lockfile; no
dependency versions were changed. Backend checks used the production Dockerfile's Python 3.12
version instead of changing pins to suit the laptop's Python 3.14.

These are correctness checks, not throughput or investment-performance experiments. Suite/build
durations are tool timings and are not end-user analysis latency. No live market-data or paid
provider verification was performed. CI configuration was added; see the final delivery message
for its actual remote run status, rather than assuming local success implies remote success.

## Historical resume claim audit

| Claim | Evidence and disposition |
| --- | --- |
| Built and deployed 9 REST endpoints | Current source has more routes; historical count/date not established. Deployment is unverified. Do not reuse “deployed” yet. |
| 147 ms to 1 ms median, 99% reduction across 5 workflows | `backend/test_cache_speed.py` makes only two calls to one history URL, using wall-clock timing. It proves neither medians nor five workflows nor controlled cold/warm state. No retained source measurements found. Exclude pending a new experiment. |
| TTLs of 15 seconds to 12 hours | Implemented cache policy exists in `cache_service.py`; correctness, market-hours freshness, and live hit rates remain unverified in this checkpoint. Scope claim only. |
| 397 chunks from 348 articles, 1,536 dimensions | Embedding dimension is configured in code/schema; no database snapshot or reproducible evidence for historical row counts was found. Omit counts. |
| Reproducible five-day evaluation against momentum/random baselines | Grading code exists but comparable baseline evaluation does not. Target date is five calendar days from saving. The fetcher selects the last returned close and can fall back to a recent close, so the effective horizon is not fixed. Exclude efficacy claims. |
| Six indicators and cited news | Six indicator groups and source-evidence records exist. Sources depend on available embedded coverage. This is implementation scope, not predictive accuracy. |

## Resume wording supported by this checkpoint

SWE: “Hardened a FastAPI stock-analysis pipeline against six optional-news failure paths while
preserving technical results; added PostgreSQL-backed acceptance checks for analysis persistence
and user-owned watchlists within an 81-test passing suite.”

PM: “Prioritized reliable ticker analysis for a family-use stock screener, defined acceptance
criteria for missing news and incomplete data, and resolved seven reproduced failure cases;
clarified score meaning and data freshness in the results experience.”

The seven failure cases are six controlled news cases plus insufficient price history. They are
not seven production incidents, users, or measured improvements in conversion. The 81 tests include
existing tests and newly added cases; do not claim to have authored all 81. Neither bullet implies
customer research, adoption, team leadership, investment returns, or hiring outcomes.

## Remaining release priorities

1. Verify actual deployed infrastructure and email-link sign-in, then test the complete phone
   workflow: sign in, analyze, interpret warnings, save/reload/remove a ticker, and sign out.
2. Fix evaluation-date selection, define trading/calendar-day policy and entry-price timestamps,
   exclude incomplete/stale or synthetic predictions as appropriate, and compare identical samples
   against explicit momentum/random baselines. A directional hit rate is insufficient evidence of
   profitable trading or calibrated confidence. ATR bounds are risk bands, not calibrated forecasts.
3. Make analysis durable across backend restarts; the current in-process worker can leave jobs
   stranded. Bound request/poll durations and support resuming an existing job after navigation.
4. Review service-worker origin/cache rules and offline experience, and remove zoom restrictions
   for phone accessibility. Installation is not established by having a manifest alone.
5. Protect or remove development/legacy endpoints before a public release. Some unauthenticated
   diagnostic and harvesting endpoints expose data or can trigger provider work. Audit ownership,
   rate limits, and operational errors without relying on CORS as access control.
6. Measure cold/warm endpoint latency and full job completion with source timestamps, raw trials,
   failures, environment, and cache-state assertions. Retain unfavorable results.

Interview explanation: prioritize optional-dependency isolation because the user needs a useful,
honest result even when news infrastructure fails. Keep required persistence failures visible;
never present missing data as a Neutral investment assessment. Test real SQL/HTTP boundaries while
labeling provider/authentication fixtures clearly, and avoid converting test counts into user impact.
