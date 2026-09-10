# HANDOFF — Ovnicom Sentinel-DNS submission

Written 2026-09-09, mid-build, so work can resume from a different machine/
session with zero lost context. Read this before touching code.

**Update (same day, later)**: repo created and pushed —
https://github.com/alioth-stat/ovnicom-sentinel-dns (public, standalone,
separate from the Philips repo). Frontend dashboard is now built and
verified (see "Done and verified" below, updated). Work was stopped here on
explicit user instruction ("stop building here") — the remaining items
under "Not started" are still genuinely not started, most importantly the
**README.md** (required before this is a valid submission — the reuse
declaration is not optional, see hackathon rules quoted below) and the demo
video.

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

**Backend**
- All backend Python modules exist and are internally consistent
  (`ast.parse` clean on every file).
- **9/9 unit tests pass**: `.venv/bin/python -m pytest -q` → `9 passed`.
  Covers DGA/typosquat/tunneling/beaconing heuristics and the QoE score's
  three status buckets.
- `tetherto.qvac_sdk` **is now installed** in `.venv` (`pip install
  tetherto.qvac_sdk` + `python -m tetherto.qvac_sdk install-worker`, worker
  0.19.0 landed in `~/.cache/qvac/worker/`).
- **Live end-to-end QVAC call verified working**: ran
  `qvac_judge.classify()` directly (not through the full server) against a
  synthetic DGA-shaped domain. Real result:
  `{'verdict': 'dga', 'confidence': 0.85, 'reasoning': 'El dominio
  xk7qz9mdpltrvw.top muestra señales claras de generación algorítmica de
  dominios (dga) con un score de 0.85, sin señales de otros tipos como
  typosquatting, tunneling o beaconing.'}` — schema-constrained JSON came
  back well-formed on the first attempt (no retry needed), reasoning is
  coherent and in Spanish as prompted. Cold model load + inference took
  **~52s** on this machine's Vulkan/AMD Radeon Vega 8 iGPU backend (a
  `common_fit_params: failed to fit params to free device memory... short
  by 189 MiB` warning appeared but did not block the run — worth watching
  if it ever *does* fail outright, but harmless here). A handful of
  `Task was destroyed but it is pending!` / `RuntimeError: Event loop is
  closed` messages printed at interpreter shutdown — these are teardown
  noise from a one-off test script exiting without the process staying
  alive (this is not how `qvac_client.py`'s loop is meant to be torn
  down — a real server process just keeps running, never triggering this
  path). **Not a code bug**, but if it's ever seen happening *during* a
  live `uvicorn` run (not at shutdown), that would be worth investigating.
  **Not yet verified**: a full `./run.sh` end-to-end run through the actual
  FastAPI server + `pipeline.run_forever()` background loop + frontend
  polling it live. Only the isolated `qvac_judge.classify()` call has been
  proven; the asyncio `run_in_executor` wiring in `pipeline.py` is
  reasoned-through and code-reviewed but not yet run.

**Real dataset**
- `/home/alstat/Downloads/LogsDNSQueries 2.zip` extracted into
  `data/dns_logs/` (36 files, 721MB, gitignored — confirmed **not** staged
  by git, `git status` shows it untracked as expected).
- `bind_log.parse_line` verified against a 3-file (~379k line) sample:
  **100.0% match rate** (379,111/379,120 lines parsed; the ~9 misses are
  almost certainly blank/truncated lines, not a format the regex misses).
- `generator.next_batch()` confirmed pulling **real** qnames/client IPs
  (`www.apple.com`, `oec-im-tt-sg.tiktokglobalshopv.com`, real public IPs)
  blended with synthetic attack traffic (DGA/typosquat/tunneling/beaconing)
  in the same batch, each attack type appearing with the expected shape.
  Zone assignment for real IPs confirmed stable (same IP → same zone).

**Frontend**
- Scaffold copied (`package.json`, `vite.config.ts`, tsconfigs,
  `index.html`, `index.css`, `main.tsx`, `Background.tsx`, `GlassPanel.tsx`,
  their `lib`/`hooks` deps) **plus now also** the generic shadcn
  `ui/badge.tsx` and `ui/table.tsx` primitives (copied from the Philips
  repo as-is — they're stock shadcn components, not Philips-domain code).
- **`App.tsx` and `api.ts` are written** (previously listed as TODO, now
  done): single dashboard, two `GlassPanel`s side by side — a security
  alerts table (time/zone/domain/verdict badge/reasoning) and a per-zone
  QoE table (status badge/score/latency/NXDOMAIN rate/QPS). A small
  `hooks/use-polling.ts` hook drives both panels via `GET /api/alerts` and
  `GET /api/qoe` every 3s.
- `npm install` run successfully. `npm run lint` (oxlint) → clean.
  `npm run build` (`tsc -b && vite build`) → **succeeds**, 47 modules,
  built in under a second. The `dist/` output was deleted afterward (build
  artifact, not meant to be committed).
- **Not yet verified**: actually opening `http://localhost:5173` in a
  browser against a live backend. The build compiling is not the same as
  confirming the tables render sensibly with real data — do that before
  calling the frontend done-done.

### Not started / explicitly deferred — pick up here

Work was stopped by explicit user instruction right after the items below
were confirmed still outstanding. **Nothing in this section has been
started.** This is the actual remaining punch list:

1. **`README.md`** — the single biggest gap. Must include, per the plan and
   hackathon rules:
   - Upfront declaration of reuse from the Philips submission (**required**
     — "toda base preexistente debe declararse en el README, omitirla
     descalifica" is a disqualification rule, not a suggestion).
   - Explanation of what's simulated (Kafka/ClickHouse/Grafana/live-Wazuh-
     manager) vs. real (the actual DNS query data, now confirmed working
     via `data/dns_logs/`), with the mapping to Ovnicom's real stack
     spelled out.
   - Run instructions (`./run.sh`, `pytest -q`).
   - Confirmation of the on-device-only QVAC inference requirement.
   - A note on how to obtain the real dataset (the private SharePoint link
     is in the parent repo's `Context/Retos`, "Reto 4"'s last line) for
     anyone trying to reproduce the real-capture path — the dataset itself
     is gitignored and was never pushed (721MB + likely not
     freely-redistributable), so a fresh clone of this repo runs
     synthetic-only until someone populates `data/dns_logs/` themselves.
2. **Full `./run.sh` live run** — the isolated `qvac_judge.classify()` call
   is proven (see above), but the actual FastAPI server +
   `pipeline.run_forever()` background loop has never been started and
   watched end-to-end. Do this before trusting `pipeline.TICK_SECONDS =
   1.5` / `BATCH_SIZE = 25` as reasonable demo pacing — they're
   unvalidated guesses.
3. **Manual browser check** at `http://localhost:5173` against a live
   backend: confirm the alerts table actually populates within a few
   seconds, shows at least one of each verdict kind with sane-looking
   reasoning text, and the QoE table shows all 5 zones with plausible,
   moving scores. The frontend compiling cleanly is not the same thing as
   this.
4. **`tail -f wazuh_alerts.log`** sanity check once alerts are flowing:
   confirm valid JSON lines with fields a Wazuh `<localfile>` JSON decoder
   could actually consume (schema is in `wazuh_sink.py` — reasoned about,
   never checked against a real Wazuh instance).
5. **Confirm the `LICENSE` file (Apache 2.0, copied from Philips) is
   actually wanted for this submission** — Reto 3's rules say "no se exige
   licencia abierta" (open license not required), so this was a low-effort
   copy-along, not a requirement. Fine to keep for consistency with the
   sibling submission, but nobody explicitly asked for it on this repo.
6. **Demo video** (max 5 minutes, required deliverable) — not started.

### Where things actually stand right now

- Repo: **https://github.com/alioth-stat/ovnicom-sentinel-dns** (public,
  standalone — separate history from the Philips repo by design, per the
  user's explicit instruction that "the Phillips project and the Ovnicom
  project function as two separate things").
- Two commits pushed to `master`: the initial backend scaffold, and a
  follow-up with the frontend dashboard + this status update (see git log
  for the exact message).
- Local-only, never pushed (by design): `.venv/` (has `tetherto.qvac_sdk` +
  the QVAC worker installed — a fresh clone needs to redo this),
  `frontend/node_modules/`, `data/dns_logs/` (the 721MB real dataset).
- The user said to stop building and cease action after this push. No
  further work should happen here without a new explicit instruction —
  don't auto-resume the "not started" list above on your own initiative.
