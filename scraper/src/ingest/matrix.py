"""Drive a backfill across many competition-seasons.

Thin sequential orchestrator: each job (one competition + season) is processed
by an injected `process_one`, so the loop is unit-testable without a browser or
DB. A job that raises is logged and counted but never aborts the run — the next
job continues — mirroring the per-match resilience of `run_backfill`.

Resumability is inherited: every underlying step (match ingest, season rollup)
is idempotent against the DB, so re-running the whole matrix resumes cleanly.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SeasonJob:
    competition_id: int
    season_label: str


def run_matrix(
    jobs: list[SeasonJob],
    *,
    process_one: Callable[[SeasonJob], dict],
    log: Callable[[str], None] = print,
) -> list[dict]:
    """Process each job in order. Returns one result dict per job."""
    results: list[dict] = []
    for i, job in enumerate(jobs):
        tag = f"[{i + 1}/{len(jobs)}] comp {job.competition_id} {job.season_label}"
        log(f"{tag} === start ===")
        try:
            outcome = process_one(job)
            results.append({"job": job, "status": "ok", **outcome})
            log(f"{tag} === done: {outcome} ===")
        except Exception as e:  # noqa: BLE001 — isolate one job's failure from the rest
            results.append({"job": job, "status": "failed", "error": str(e)})
            log(f"{tag} === FAILED: {e} ===")
    return results


def build_jobs(
    competition_ids: list[int],
    season_labels: list[str],
    *,
    skip: set[tuple[int, str]] = frozenset(),
) -> list[SeasonJob]:
    """Season-major job list (all comps for the newest season first), minus any
    (competition_id, season_label) pairs in `skip`."""
    jobs: list[SeasonJob] = []
    for season in season_labels:
        for comp in competition_ids:
            if (comp, season) in skip:
                continue
            jobs.append(SeasonJob(comp, season))
    return jobs
