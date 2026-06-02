"""Unit tests for the multi-season matrix driver (no browser, no DB)."""

from src.ingest.matrix import SeasonJob, build_jobs, run_matrix


def test_processes_every_job_in_order():
    seen = []
    run_matrix(
        [SeasonJob(2, "2025-2026"), SeasonJob(4, "2025-2026")],
        process_one=lambda j: seen.append((j.competition_id, j.season_label)) or {"n": 1},
        log=lambda _m: None,
    )
    assert seen == [(2, "2025-2026"), (4, "2025-2026")]


def test_one_failure_does_not_abort_the_rest():
    def process(job):
        if job.competition_id == 4:
            raise RuntimeError("boom")
        return {"matches": 10}

    results = run_matrix(
        [SeasonJob(2, "2025-2026"), SeasonJob(4, "2025-2026"), SeasonJob(5, "2025-2026")],
        process_one=process,
        log=lambda _m: None,
    )
    statuses = [r["status"] for r in results]
    assert statuses == ["ok", "failed", "ok"]
    assert results[1]["error"] == "boom"


def test_build_jobs_is_season_major_and_respects_skip():
    jobs = build_jobs([2, 4], ["2025-2026", "2024-2025"], skip={(2, "2025-2026")})
    assert jobs == [
        SeasonJob(4, "2025-2026"),
        SeasonJob(2, "2024-2025"),
        SeasonJob(4, "2024-2025"),
    ]
