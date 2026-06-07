"""Unit tests for the reprocess orchestration core (no storage, no DB)."""

from src.ingest.reprocess import run_reprocess


def _item(match_id: int, season_id: int) -> dict:
    return {"meta": {"id": match_id, "season_id": season_id}, "match_data": {}}


def test_reprocesses_all_and_rolls_up_touched_seasons():
    rolled: list[list[int]] = []
    s = run_reprocess(
        [_item(1, 10), _item(2, 10), _item(3, 20)],
        process_one=lambda it: 11,
        rollup_seasons=rolled.append,
        log=lambda _m: None,
    )
    assert s["matches"] == 3 and s["rows"] == 33 and s["failed"] == 0
    assert s["seasons_rolled"] == 2
    assert rolled == [[10, 20]]  # deduped, sorted, rolled once after the loop


def test_one_failure_does_not_abort_and_excludes_its_season_when_alone():
    rolled: list[list[int]] = []

    def process(it):
        if it["meta"]["id"] == 2:
            raise RuntimeError("boom")
        return 5

    s = run_reprocess(
        [_item(1, 10), _item(2, 99), _item(3, 10)],
        process_one=process,
        rollup_seasons=rolled.append,
        log=lambda _m: None,
    )
    assert s["matches"] == 2 and s["failed"] == 1 and s["rows"] == 10
    # season 99 only had the failed match, so it is not rolled up
    assert rolled == [[10]]


def test_empty_input_still_calls_rollup_with_nothing():
    rolled: list[list[int]] = []
    s = run_reprocess(
        [], process_one=lambda it: 0, rollup_seasons=rolled.append, log=lambda _m: None
    )
    assert s == {"matches": 0, "rows": 0, "failed": 0, "seasons_rolled": 0}
    assert rolled == [[]]
