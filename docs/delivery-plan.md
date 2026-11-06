# Zelta delivery plan and evidence rules

## Product outcome

A family member can open Zelta on a laptop or phone, sign in, analyze a stock, understand the
result and its limitations, and reopen a saved personal watchlist with the developer's laptop
switched off. The user confirmed on November 6, 2026 that only localhost and Supabase testing
exist. There is no hosted frontend or backend yet.

The CTO's feedback is the editorial standard: explain the problem solved or outcome first,
then implementation. Cache hit latency, TTL ranges, endpoint counts, and embedding dimensions
alone do not establish value. Never describe simulated calls avoided as observed production use.

## Work in delivery order

| Priority | Work | Completion evidence |
| --- | --- | --- |
| 1 | Establish an online deployment | Restore Supabase; configure hosted API and frontend; apply migrations; set auth redirects and CORS; verify health and the actual production URL with the laptop off. Keep credentials out of source control. Confirm hosting costs before provisioning paid resources. |
| 2 | Finish sign-in and personal watchlists | A real email link opens the deployed app; two separate accounts cannot see each other's data; add/reload/delete work on laptop and phone; expired sessions and backend outages show actionable errors. |
| 3 | Complete the analysis experience | Valid, invalid, missing-history, stale-data, unavailable-news, and provider-failure paths are understandable. Refresh/navigation can resume the same job; polling and upstream calls have bounded deadlines; a restarted backend does not strand jobs indefinitely. |
| 4 | Close public-release gaps | Disable/remove legacy experiment and diagnostic write endpoints or protect them appropriately; limit repeated expensive submissions; review service-worker origin/cache rules; support zoom and readable phone layouts. |
| 5 | Correct prediction evaluation | Define five calendar days versus five trading sessions explicitly; use the eligible completed session's close; retain timestamps and evaluation version; quarantine incorrect historical grading; define Neutral/unchanged-price behavior and eligible data. |
| 6 | Measure cache effectiveness and freshness | Fix New York/DST boundaries, verify expiration, count actual hits/misses/provider calls, record data and retrieval timestamps, and test errors/expiry. Distinguish controlled replays from live traffic and cache residence from feed age. |
| 7 | Measure and reduce workflow friction | Record submission-to-result time, successful/failed/timed-out jobs, sign-in completion, and watchlist persistence. Fix the largest observed blocker, then repeat the same scenario set. Avoid storing emails or tokens in measurement logs. |
| 8 | Produce evaluation and interview evidence | Compare identical eligible samples with explicit momentum, always-up, and seeded random baselines; report sample size, dates, directional coverage, uncertainty and failures. Finalize outcome-first SWE/PM bullets with linked evidence. |

Priorities 1–4 define usable product delivery. Priorities 5–8 make claims credible; none is a
reason to add unrelated features. Deployment can advance while evaluation and measurements are
implemented locally. Automatic alerts, brokerage connections and holdings/P&L are deferred.

## Measurement contracts

| Metric | Definition and capture | Honest use |
| --- | --- | --- |
| Analysis completion | Persist one row per submitted job: outcome, submission/result timestamps, price/news availability, model revision, and failure stage. Completion rate = completed jobs / all submitted jobs. Also report usable fresh results separately so insufficient-data or stale results do not inflate success. | Report the exact test workload, dates, and denominator. Scripted attempts are not users or adoption. |
| User wait | Measure from browser submission to visible result. Separately record queue and server execution durations. Report median/p95 and all failed/time-out trials. | A fast cache endpoint does not establish fast analysis or onboarding. Small samples get raw results, not confident production claims. |
| Cache hit rate | Cache-served lookups / all lookups; count errors separately and include cold misses. Segment by endpoint, time window and distinct symbols. | A repetitive replay is a replay. Observe real production traffic before claiming a production hit rate. |
| Upstream calls avoided | Compare actual provider invocation counts under identical uncached/cached request sequences; record retries and refresh calls. | Forecasting money saved requires measured billable usage and actual provider pricing. Fewer fixture calls prove engineering behavior only. |
| Freshness | Store source market-data time and fetch/cache-write time. Measure source age at display and cache residence; verify TTL limits through active-window transitions and DST. | A 15-second TTL cannot make a delayed or daily source real-time. Currently the ticker-check endpoint fetches `history(period="1d")`; do not market it as a real-time quote feed. |
| Sign-in and watchlist tasks | Record attempts, completion, error category, and whether the saved item survives reload/device switch. An optional observed session with Mom can identify confusion. | One family member is one participant. Do not invent interviews, broad usability gains or conversion lifts. No external testers are required for local acceptance work. |
| Prediction quality | Lock entry timestamp/data availability, eligible target close, model version, symbols/date range and baselines. Preserve Neutral coverage and missing-data exclusions. Use the same observations for every baseline; seed random comparisons. | Directional hit rate alone does not establish profit, investment usefulness or superiority. Historical replays must avoid using future prices/news. |

Before a change, save the baseline workload, input snapshots and revision. After it, run the
same workload and preserve failed trials too. Keep local/fixture, live-provider and deployed-browser
results separate. Label measurements taken during closed markets as such. Never compute medians
from one cold and one warm request or quietly remove failed attempts.

## Delivered cache checkpoint November 6 2026

The old policy used the host's local time and could give a 03:59 New York entry another twelve
hours of life. The replacement uses `America/New_York`, retains 15-second TTLs during a daily
04:00–16:00 window, and caps overnight entries at the next 04:00 boundary (maximum twelve hours).
Elapsed-time calculation accounts for DST. This conservative daily schedule does not model
exchange holidays, early closes or extended hours after 16:00. Short TTLs are kept during the
same daytime window on weekends to avoid extending stale entries. Existing Redis entries written
under the old policy can retain their old TTL until expiration; release verification must check
that legacy keys have expired or invalidate the specific `ticker:live:*` keys.

All **94 backend tests passed**, including real PostgreSQL and Redis checks. No provider API was
called. The cache replay exercises the actual HTTP route and Redis, with fixture yfinance closes
and no artificial network delay. Three rounds each issue 100 uncached and 100 cached requests
over five repeated symbols, finishing each mode within the 15-second minimum TTL:

- 600 total requests; 300 uncached and 300 cached.
- Provider fixture calls: 300 without reads from Redis versus 15 with cache reads, including
  the cold misses: **95% fewer calls** for this workload.
- 285/300 cached-run requests were hits; every response matched its fixture price.
- No failed requests; all raw per-request timings, sources and correctness checks are retained
  in `docs/evidence/2026-11-06/cache/replay.json`.

A second 600-request verification is retained separately as `replay-final.json`; it also passed.
In the first replay, one cached round's median HTTP time was slightly slower than the uncached
round (about 2.45 ms versus 2.40 ms). There is no consistent latency win to claim from these
fixture-only timings. Calls avoided and payload correctness are the useful measured outcomes.

This intentionally high-reuse workload does not estimate natural demand or demonstrate production
adoption, live-feed speed, user time saved or dollar savings. The JSON retains response timings;
they are in-process HTTP timings with a fixture upstream, not live-service latency. This result
validates the current ticker-check cache only, not five market workflows or the analysis-job path.

Reproduce the suite with the README command. Then, from the repository root, run:

```powershell
docker compose -p zelta-validation -f compose.test.yml up -d test-db test-redis
docker compose -p zelta-validation -f compose.test.yml run --rm --volume "${PWD}/docs/evidence/2026-11-06/cache:/evidence" -e ZELTA_SOURCE_REVISION=<revision> tests python scripts/measure_cache.py --output /evidence/replay.json
docker compose -p zelta-validation -f compose.test.yml down
```

Choose a new output directory for another trial so earlier results survive. The script rejects
non-test Redis configurations, deletes only its five synthetic ticker keys, and retains failures
before raising. Do not run it against production. Installed packages come from the existing pinned
requirements; source hashes and environment are in this checkpoint's evidence directory.

## Resume wording

SWE, supported by the controlled replay:

“Reduced repeated provider calls 95% in a 600-request cache replay; fixed timezone and overnight
expiration bugs to keep cached ticker checks within a defined freshness policy.”

PM, supported by the decision and validation record:

“Addressed stale-price risk in a family-use stock screener by defining cache freshness criteria
and validating a policy that avoided 95% of provider calls in a controlled repeat-request replay.”

Use at most the stronger relevant cache bullet alongside the prior reliability accomplishment;
do not multiply the same work into several bullets. These are engineering/replay outcomes. More
compelling product bullets should follow deployed task completion, actual usage or measured wait
improvements. Their eventual template is “Enabled [user task], improving [observed metric] from
[baseline] to [result] across [sample], by [shipped change].” Fill it only after measurement.

## Work through the November 8 checkpoint

- November 6: finish the cache fix and controlled evidence; prepare deployment configuration and
  requirements without purchasing services. Current work does not establish a live deployment.
- November 7: deploy and verify sign-in/analysis/watchlists; fix release-blocking failures; collect
  a defined set of live workflow attempts. Correct grading independently, without making real
  users wait for five future days before shipping the core experience.
- November 8: rerun the agreed acceptance scenarios, summarize real results and limitations,
  select two or three non-overlapping bullets for each resume, and retain reproducible evidence.

This is sequencing, not a delivery-time guarantee. If deployment remains blocked, report local
results honestly and leave the unavailable live checks marked unverified. Do not replace missing
product outcomes with invented users, savings, investment performance or “led” language.
