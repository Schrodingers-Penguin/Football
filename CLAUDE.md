# CLAUDE.md

Project: a personal-use FBref-style football scouting dashboard. See `SPEC.md` for the full build specification.

This file governs how you (Claude Code) execute against the spec.

---

## How Max wants you to communicate

- **Be succinct.** No flattery, no compliments, no "great question". Skip preamble.
- **Stay neutral.** Don't editorialise about choices already made in the spec.
- **Challenge ideas and assertions.** If something in the spec or in Max's instructions looks wrong, say so before implementing it.
- **Don't end every message with a question.** Wait for Max to direct the next step unless you genuinely cannot proceed without input.

## Error tolerance

- **0% margin for error.** Re-read what you've written before declaring something done. Check your own work multiple times. Particularly: stat definitions, coordinate handling, schema migrations, percentile formulas. Mistakes in any of these compound and silently corrupt the dashboard.
- If unsure about a fact, library API, or WhoScored behaviour: stop and verify (read docs, test in a small script) rather than guessing.

## Execution discipline

- **Phase-gated.** The spec defines phases 0–9 each with a validation criterion. Complete one phase, show Max the validation output, **wait for explicit approval before proceeding** to the next phase. Don't chain phases together unprompted.
- **Show your validation work.** When a phase's validation says "user verifies X", produce the artefact (script output, screenshot of DB row, query result) that lets Max verify it.
- **Don't over-build.** Don't add features not in the spec without asking. If you see something worth adding, propose it as a separate item, don't sneak it in.

## Honesty

- If a task is harder than expected, say so. Don't quietly compromise the spec.
- If you implemented something and it doesn't quite match the spec definition, flag it explicitly. Don't paper over divergences.
- If a scrape fails, a test fails, or a stat tagger doesn't produce sensible output: stop and report. Don't move on.

## Tech stack constraints

| Layer | What to use |
|---|---|
| Scraper | Python 3.11+, Playwright with stealth, `httpx` for any non-browser HTTP, `polars` or `pandas` for data work |
| Scraper hosting | GitHub Actions cron for daily incremental; local Mac for backfill |
| DB | Supabase Postgres (new project, separate from existing plant DB) |
| Object storage | Supabase Storage |
| Backend | Next.js 14 App Router, server components by default |
| Frontend | React, Tailwind, shadcn/ui where useful, recharts for radar/charts |
| Auth | None (private, single-user) |
| Hosting | Vercel hobby tier |

## Coding conventions

- **Python**: type hints throughout; `ruff` for lint + format; one function per concept; no monolithic scripts. Stat-tagging functions go in `scraper/stats/<stat_name>.py` so each is independently testable.
- **TypeScript**: strict mode on; no `any`; Zod schemas for API boundaries.
- **SQL**: migrations in `db/migrations/<timestamp>_<name>.sql`; never edit applied migrations, always add new ones.
- **Tests**: every stat tagger gets a unit test with hand-checked event input. Skipping tests is not acceptable for stat code.
- **Secrets**: never commit. `.env.local` is gitignored. GitHub Actions uses repo secrets.

## File layout

```
/
├── SPEC.md                    # build specification (authoritative)
├── CLAUDE.md                  # this file
├── MAINTENANCE.md             # operational runbook (created in Phase 9)
├── README.md                  # quick start for Max
├── .gitignore
├── scraper/                   # Python scraping + ingestion
│   ├── pyproject.toml
│   ├── src/
│   │   ├── whoscored/         # browser + extraction
│   │   ├── parser/            # matchCentreData → normalized events
│   │   ├── stats/             # one file per stat tagger
│   │   ├── aggregate/         # match-level and season-level rollups
│   │   ├── storage/           # Supabase Storage upload/download
│   │   └── ingest/            # end-to-end pipeline
│   └── tests/
├── db/
│   └── migrations/            # numbered SQL migration files
└── web/                       # Next.js
    ├── package.json
    ├── app/
    ├── components/
    ├── lib/
    └── ...
```

## Supabase access pattern

- All Supabase calls happen server-side only — Next.js server components, API routes, or server actions — using the service role key loaded from environment variables.
- Never use the Supabase anon key.
- Never import or use `supabase-js` in a client component (`'use client'`).
- If frontend interactivity needs data, fetch it server-side and pass it as props, or expose a server action / API route.

## When something breaks later

If Max comes back in months with "the scraper broke":

1. Read `MAINTENANCE.md` first. It documents the exact selectors, JSON paths, and known fragilities.
2. Ask Max for the failing match URL and the error/traceback.
3. Fetch the page yourself (or have Max paste the relevant HTML) to see what changed.
4. Patch the smallest possible surface area. Don't rewrite working code while fixing a small break.
5. Update `MAINTENANCE.md` with what changed and what the new selector/path is.

## Things to push back on if Max requests them

- Storing events in Postgres on the free Supabase tier (won't fit; see SPEC §6 and §14)
- Publishing the dashboard or sharing the URL (legal exposure under EU database rights; see context in Max's chat history)
- Mixing data sources (Sofascore + WhoScored etc.) — creates inconsistencies; spec is single-source
- Skipping Phase 1 validation — coordinate orientation must be empirically verified before Phase 3
- Running the full ~7,500-match backfill on GitHub Actions — will exhaust free minutes; use Mac

## Starting point

When Max first opens this in a Claude Code session, your opening move is:

1. Read `SPEC.md` in full.
2. Read this `CLAUDE.md` in full.
3. State which phase you understand you're starting (probably Phase 0 if the repo is empty).
4. List the Phase 0 deliverables and what you need from Max (Supabase project URL + service role key, Vercel project setup, GitHub secrets).
5. Wait for Max to confirm before creating files.
