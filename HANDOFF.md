# HANDOFF — Ovnicom Sentinel-DNS submission

Written 2026-09-09, mid-build, so work can resume from a different machine/
session with zero lost context. Read this before touching code.

## What this is

Second submission (own repo, own video) for the **Decentralized AI
Hackathon** (ISD Summit, Panama, Sept 9-11 2026). Same team as
`Challenges/phillips-installed-base-intelligence/` in the parent `ISD` repo,
now tackling **Reto 4, Ovnicom's "Sentinel-DNS" corporate challenge**
($1,500, stacks with the general track). Hackathon started today 8:00 AM
Panama time, 48-hour window, **submission deadline Sept 11, 8:00 AM**.

Full challenge brief is in the parent repo at `../../Context/Retos` (plain
text, Spanish, "Reto 4"). Short version: Ovnicom runs DNS infra
(BIND9+dnstap → Vector → Kafka → ClickHouse → Grafana, Wazuh as SIEM) for
regulated banking/gov/health clients. DNS queries reveal browsing habits, so
nothing can leave the datacenter — no cloud AI calls, period. Build a QVAC
agent that attaches as an **additional consumer** of the DNS stream (must
not touch the production pipeline) and produces:
1. **Security**: real-time classification of suspicious domains (DGA,
   typosquatting, DNS tunneling, C2 beaconing) → alert to Wazuh.
2. **Experience**: a QoE score per zone/POP (latency, NXDOMAIN rate,
   saturation) → per-site dashboard.

Judges specifically check: classification runs over a live stream (not a
static file), alerts reach Wazuh in a SIEM-ingestible format, the QoE score
is operator-interpretable, and "no data leaves the building" is verifiable.

The full plan this build followed is at
`/home/alstat/.claude/plans/velvet-orbiting-elephant.md` on the machine that
started it — copy its contents here if that path isn't reachable from a new
session.

## Where the base code came from

This reuses pieces from the team's own **prior submission in this same
hackathon**, `Challenges/phillips-installed-base-intelligence/` (parent
repo, sibling directory). Per hackathon rules ("toda base preexistente debe
declararse en el README — omitirla descalifica"), **the final README.md for
this repo MUST declare this reuse explicitly** — that's still TODO, see
below. Reused, and why it's safe to trust as-is:
- `qvac_client.py` — copied verbatim, zero changes. Generic QVAC wrapper
  (connect once, one shared asyncio loop + lock for the process lifetime,
  lazy model loading). `extract_sync(text, json_schema, system_prompt)` is
  the primitive this whole project's AI step is built on.
- `api.py`'s shape: thin FastAPI wrapper, plain `def` routes, zero business
  logic, CORS open to `localhost:5173`.
- `db.py`'s shape: plain sqlite3 functions, no ORM.
- `confidence.py`'s shape (weighted-sum → bucketed status) → became `qoe.py`.
- `extract.py`'s shape (JSON-schema-constrained prompt + 2-attempt retry on
  malformed/all-null output) → became `qvac_judge.py`.
- Frontend: `Background.tsx`, `GlassPanel.tsx` + their dependencies
  (`lib/utils.ts`, `lib/motion.ts`, `hooks/use-prefers-reduced-motion.ts`,
  `index.css`, `main.tsx`, `vite.config.ts`, tsconfig, `package.json`)
  copied as-is. **Not** `StepShell.tsx` — this app is a live dashboard, not
  a multi-step wizard, so the step-slide machinery doesn't apply. That's a
  deliberate scope cut, not an oversight.

More detail on the source repo's reuse story: its own
`context/README.md`.

## A key discovery mid-build: a real dataset showed up

The user dropped `/home/alstat/Downloads/LogsDNSQueries 2.zip` — this is
**real BIND9 query-log data**, almost certainly the Ovnicom-provided
synthetic-but-realistic dataset referenced in the brief (there's a private
SharePoint link for it in `../../Context/Retos`, "Reto 4"'s last line).
Verified facts about it:
- 36 files (`queries.0` … `queries.35`), plain text, ~721MB total,
  **4,605,865 lines**.
- Real BIND9 `named.log` query-channel format:
  `09-Sep-2026 08:04:59.901 queries: info: client @0x7fa2c438edf0
  190.102.59.241#35082 (www.apple.com): query: www.apple.com IN A + (172.19.1.2)`
- Only the **query** line is logged — no response/rcode/latency channel
  present anywhere in the corpus (checked: zero occurrences of NXDOMAIN,
  SERVFAIL, REFUSED). So rcode and latency are **not** in the data; we still
  synthesize those.
- Client IPs span effectively the whole public IPv4 space (not just
  Panama/LatAm ranges) — this reads as a large, real/realistic global
  recursive-resolver capture, not a small simulated office network. Domains
  are legitimate real-world traffic (Apple, Microsoft, Spotify, Bing,
  TikTok, Office365/Teams infra, etc.) — no obvious injected DGA/malicious
  traffic found by inspection.
- Each individual `queries.N` file was **not confirmed** to be strictly
  chronologically sorted internally (the `sort -c` check produced no
  conclusive output either way) — irrelevant to the design chosen below,
  which never depends on cross-file or intra-file ordering.

**Design decision made because of this**: treat the real capture as the
"benign backbone" of the stream (this satisfies the brief's "tráfico normal
simulado" requirement about as authentically as possible), and always layer
synthetic DGA/typosquat/tunneling/beaconing traffic on top of it, since a
real benign capture obviously contains none of those by construction. This
is implemented and working (see `generator.py`) but **the dataset itself is
not yet moved into place** — see TODO.

The zip is at `/home/alstat/Downloads/LogsDNSQueries 2.zip` on the user's
machine (outside any repo). It was test-unzipped to
`/tmp/dns_dataset_check/` during investigation (that's a scratch copy, not
part of any repo, and `/tmp` may not survive a reboot — treat the Downloads
zip as the source of truth, not the /tmp copy).

## Architecture as built (see also the plan file for the original design)

```
Challenges/ovnicom-sentinel-dns/         (git repo — NOT YET git-init'd, see TODO)
├── qvac_client.py     # copied as-is
├── bind_log.py        # NEW vs. plan: real BIND9 log-line parser + infinite multi-file cycling reader
├── generator.py       # event stream: real capture (if data/dns_logs/ present) blended with synthetic attacks
├── detectors.py       # cheap heuristics: entropy/digit-ratio (DGA), rapidfuzz distance to brand list (typosquat),
│                       #   long high-entropy label (tunneling), fixed-interval repeat queries (beaconing)
├── qvac_judge.py       # QVAC structured verdict on heuristic-flagged candidates only
├── qoe.py             # per-zone score: 0.5*latency + 0.3*NXDOMAIN + 0.2*saturation -> healthy/watch/degraded
├── db.py              # sqlite: alerts table + qoe_snapshots table (stands in for ClickHouse)
├── wazuh_sink.py       # appends confirmed alerts as JSON lines to wazuh_alerts.log
├── pipeline.py         # asyncio background task: batch -> detect -> (run_in_executor) QVAC judge -> db + sink
├── api.py             # FastAPI, lifespan hook starts pipeline.run_forever(), 2 GET routes
├── test_detectors.py   # 9 tests total between these two files, all passing, pure logic, no model needed
├── test_qoe.py
├── requirements.txt
├── run.sh             # bootstrap + run both servers, copied/adapted from Philips' run.sh
├── .gitignore          # covers .venv, __pycache__, *.db, wazuh_alerts.log, AND /data/ (the real dataset - never commit it, 721MB + private)
├── LICENSE            # copied from Philips (Apache 2.0) -- confirm this is actually wanted before shipping, wasn't explicitly asked for here
└── frontend/           # Vite/React/Tailwind/shadcn scaffold copied from Philips; App.tsx/api.ts NOT yet written (see TODO)
```

### The one non-obvious wiring detail (don't undo)

`qvac_judge.classify()` is a **blocking** call — it goes through
`qvac_client.extract_sync()`, which acquires a module-level
`threading.Lock` and runs on a **dedicated** asyncio loop that is separate
from FastAPI/uvicorn's own loop (see `qvac_client.py`'s `ponytail:`
comments — this is inherited, unmodified). `pipeline.run_forever()` runs as
a background task **on FastAPI's loop**, so calling `qvac_judge.classify()`
directly there would block that loop (and therefore block `/api/alerts` and
`/api/qoe` too, while the LLM call is in flight). That's why
`pipeline.py` dispatches it via
`await loop.run_in_executor(None, qvac_judge.classify, ...)` — this hands it
to a plain thread, which is exactly the same safety net Philips' plain
`def` routes get for free from FastAPI's own threadpool, just made explicit
here since a background task isn't a request handler.

### Zone assignment for real-capture clients

`generator._zone_for_ip(ip)` maps a real client IP to one of the 5 fictional
zones (`pty-01, pty-02, bog-01, gua-01, sal-01`) via
`hashlib.md5(ip.encode()).digest()[0] % 5` — deliberately **not** Python's
builtin `hash()`, which is randomly salted per-process
(`PYTHONHASHSEED`) and would reassign every client to a different zone on
every restart. This keeps each client's "home zone" stable across runs.

## Status: what's done vs. what's left

### Done and verified
- All backend Python modules listed above exist and are internally
  consistent (`ast.parse` clean on every file).
- `db.init_db(":memory:")` works standalone.
- `generator.next_batch(5)` produces plausible synthetic events end-to-end
  (verified by hand, output inspected).
- **9/9 tests pass**: `.venv/bin/python -m pytest -q` → `9 passed`. Covers
  DGA/typosquat/tunneling/beaconing heuristics and the QoE score's three
  status buckets. Ran in a throwaway venv with only
  `rapidfuzz pytest fastapi uvicorn` installed (deliberately did **not**
  install `tetherto.qvac_sdk` yet — not needed for pure-logic tests, and
  it's a heavier install with a worker/model download step).
- Frontend scaffold files are copied into place (`package.json`,
  `vite.config.ts`, tsconfigs, `index.html`, `index.css`, `main.tsx`,
  `Background.tsx`, `GlassPanel.tsx`, their `lib`/`hooks` deps). `npm
  install` has **not** been run yet in this `frontend/` (no
  `node_modules/`).

### Not started / explicitly deferred — pick up here

1. **Move the real dataset into place**, if using it: unzip
   `/home/alstat/Downloads/LogsDNSQueries 2.zip` so that
   `Challenges/ovnicom-sentinel-dns/data/dns_logs/queries.*` exist (36
   files). `generator.py` auto-detects this directory
   (`SENTINEL_DNS_LOG_DIR` env var overrides the default `data/dns_logs`
   path) and blends it in automatically — no code change needed, just the
   files being present. **Untested**: the real-log code path
   (`bind_log.stream_real_events` + `generator._next_benign`'s real-stream
   branch) has not actually been run against real files yet, only
   `ast.parse`-checked and read-through-reviewed. Run
   `python3 -c "import generator; print(generator.next_batch(20))"` after
   populating `data/dns_logs/` to confirm it actually pulls real qnames —
   watch for the regex in `bind_log.parse_line` possibly not matching every
   real line variant (it was written against ~15 sample lines, not the
   full 4.6M-line corpus; there may be other BIND9 log-line shapes in there
   it silently skips, which is safe but worth spot-checking with e.g. `grep
   -c` for lines matching vs. not matching the pattern).
2. **Frontend `App.tsx` and `api.ts`** — not written yet. Per the plan: a
   single dashboard (no wizard), two `GlassPanel`s side by side — a live
   security-alerts feed (domain, zone, verdict badge, QVAC's one-line
   reasoning, polling `GET /api/alerts` every ~3s) and a per-zone QoE table
   (score/latency/NXDOMAIN rate, color-coded by status, polling `GET
   /api/qoe`). No new charting dependency needed for this few-zone,
   few-metric view — plain table/cards, maybe inline SVG for a sparkline if
   there's time, per the ponytail cut already agreed in the plan.
3. **`README.md`** — not written yet. Must include, per the plan and
   hackathon rules:
   - Upfront declaration of reuse from the Philips submission (required —
     omitting it disqualifies the submission).
   - Explanation of what's simulated (Kafka/ClickHouse/Grafana/live-Wazuh-
     manager) vs. real (the actual DNS query data, if `data/dns_logs/` is
     populated), with the mapping to Ovnicom's real stack spelled out.
   - Run instructions (`./run.sh`, `pytest`).
   - Confirmation of the on-device-only QVAC inference requirement.
   - A note on how to obtain the real dataset (the private SharePoint link
     is in the parent repo's `Context/Retos`) for anyone trying to
     reproduce the real-capture path.
4. **End-to-end run against the real QVAC SDK** — never actually executed
   yet. `pip install tetherto.qvac_sdk` into `.venv`, run `./run.sh`, and
   watch `/api/alerts` actually populate with real QVAC-judged verdicts
   (not just the pure-logic unit tests). This is the first point where
   `qvac_judge.py`'s prompt/schema get validated against a live model —
   expect at least one round of prompt tweaking, same as `extract.py` in
   the Philips repo needed a retry loop for cold-load flakiness.
   `pipeline.TICK_SECONDS = 1.5` and `BATCH_SIZE = 25` are unvalidated
   guesses for demo pacing — adjust once you see it running live (e.g. if
   alerts take too long to show up, or the demo pace feels off in the
   video).
5. **Manual browser check** once the frontend exists: confirm the alerts
   feed populates within a few seconds and shows at least one of each
   verdict kind, and the QoE table shows all 5 zones with plausible,
   moving scores.
6. **`tail -f wazuh_alerts.log`** sanity check: confirm valid JSON lines
   land there with fields a Wazuh `<localfile>` JSON decoder could consume
   (schema is in `wazuh_sink.py` — not yet actually verified against a real
   Wazuh instance, only reasoned about).
7. **Confirm the `LICENSE` file (Apache 2.0, copied from Philips) is
   actually wanted for this submission** — Reto 3's rules say "no se exige
   licencia abierta" (open license not required for this hackathon), so
   this was a low-effort copy-along, not a requirement. Fine to keep for
   consistency with the sibling submission, but flag it — nobody explicitly
   asked for it on this repo yet.
8. **git init this directory** (currently not a git repo). Was about to be
   done as part of "push to GitHub under a new repo" when this handoff was
   requested — see the immediate next steps below.
9. **Demo video** (max 5 minutes, required deliverable) — not started, out
   of scope for code work but don't forget it exists as a hard requirement.

### Immediate next steps (what triggered writing this file)

The user asked, in order: (1) write this handoff doc — done, this file —
then (2) push this to GitHub as a new repo. That push has **not happened
yet** as of this file being written: no `git init`, no commit, no remote
created. Whoever/whatever picks this up next should do, in order:
1. `git init`, `git add`, first commit (mind `.gitignore` — `.venv/`,
   `frontend/node_modules/`, `__pycache__/`, `*.db`, `wazuh_alerts.log`,
   and `/data/` should never be staged; double-check `git status` before
   committing, per standing safety practice, since a broad `git add` was
   never run here and shouldn't blindly be assumed safe).
2. Create the new GitHub repo (ask the user for visibility
   public/private and the exact name if not already specified — the
   Philips repo is `alioth-stat/phillips-installed-base-intelligence`,
   suggesting the same GitHub account/org; a consistent name here would be
   something like `ovnicom-sentinel-dns`, but confirm rather than assume).
3. Push.
4. Then come back to the "not started" list above — the README and
   frontend are the two biggest gaps before this is demo-able at all.
