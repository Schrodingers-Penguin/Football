"""Unit tests for the backfill orchestrator core (no browser, no DB)."""

from src.ingest.backfill import Fixture, run_backfill


def _fx(mid: int) -> Fixture:
    return Fixture(match_id=mid, url=f"http://x/{mid}", competition_id=2, season_label="2025-2026")


class _Harness:
    """Records ingest + sleep calls; lets tests mark matches done or failing."""

    def __init__(self, done=(), fail=()):
        self.done = set(done)
        self.fail = set(fail)
        self.ingested: list[int] = []
        self.sleeps: list[float] = []

    def is_done(self, fx):
        return fx.match_id in self.done

    def ingest_one(self, fx):
        if fx.match_id in self.fail:
            raise RuntimeError("scrape boom")
        self.ingested.append(fx.match_id)
        return {"player_rows": 11}

    def sleep(self, secs):
        self.sleeps.append(secs)

    def run(self, fixtures, **kw):
        return run_backfill(
            fixtures,
            is_done=self.is_done,
            ingest_one=self.ingest_one,
            sleep=self.sleep,
            log=lambda _m: None,
            **kw,
        )


def test_all_new_ingest_and_rate_limit_between_scrapes():
    h = _Harness()
    s = h.run([_fx(1), _fx(2), _fx(3)], delay_seconds=30)
    assert s == {"total": 3, "ingested": 3, "skipped": 0, "failed": 0}
    assert h.ingested == [1, 2, 3]
    assert h.sleeps == [30, 30]  # 2 gaps between 3 scrapes, none before the first


def test_done_match_skipped_without_scrape_or_sleep():
    h = _Harness(done={2})
    s = h.run([_fx(1), _fx(2), _fx(3)], delay_seconds=30)
    assert s["ingested"] == 2 and s["skipped"] == 1 and s["failed"] == 0
    assert h.ingested == [1, 3]  # 2 never scraped
    assert h.sleeps == [30]  # only one real gap (1 -> 3); the skip adds no delay


def test_leading_skips_do_not_trigger_initial_delay():
    h = _Harness(done={1})
    h.run([_fx(1), _fx(2)], delay_seconds=30)
    assert h.ingested == [2]
    assert h.sleeps == []  # 2 is the first actual scrape -> no delay before it


def test_failure_is_counted_and_queue_continues():
    h = _Harness(fail={2})
    s = h.run([_fx(1), _fx(2), _fx(3)], delay_seconds=30)
    assert s == {"total": 3, "ingested": 2, "skipped": 0, "failed": 1}
    assert h.ingested == [1, 3]  # 3 still processed after 2 failed


def test_resume_reprocesses_previously_failed():
    # First run: 2 fails. Second run (nothing marked done) retries it.
    h = _Harness(fail={2})
    h.run([_fx(1), _fx(2), _fx(3)])
    h.fail.clear()
    h.ingested.clear()
    s2 = h.run([_fx(1), _fx(2), _fx(3)], delay_seconds=0)
    # is_done still False for all (harness has no done set) -> all reprocessed
    assert s2["ingested"] == 3 and 2 in h.ingested


def test_empty_queue():
    h = _Harness()
    assert h.run([]) == {"total": 0, "ingested": 0, "skipped": 0, "failed": 0}
