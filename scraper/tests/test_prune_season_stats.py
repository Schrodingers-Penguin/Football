"""Unit tests for pruning stale player_season_stats bucket rows (fake client)."""

from src.ingest.writers import prune_player_season_stats


class _Query:
    """Records filters, returns the parent's rows for the season it was asked for."""

    def __init__(self, table, mode):
        self.table = table
        self.mode = mode
        self.season_id = None
        self.ids = None

    def select(self, _cols):
        return self

    def eq(self, col, val):
        if col == "season_id":
            self.season_id = val
        return self

    def order(self, _col):
        return self

    def range(self, start, end):
        self._slice = (start, end)
        return self

    def in_(self, _col, ids):
        self.ids = list(ids)
        return self

    def execute(self):
        if self.mode == "select":
            rows = [r for r in self.table.rows if r["season_id"] == self.season_id]
            start, end = self._slice
            return type("Res", (), {"data": rows[start : end + 1]})()
        self.table.rows = [r for r in self.table.rows if r["id"] not in self.ids]
        self.table.deleted += self.ids
        return type("Res", (), {"data": []})()


class FakeClient:
    def __init__(self, rows):
        self.rows = list(rows)
        self.deleted = []

    def table(self, _name):
        self._t = self
        return self

    def select(self, cols):
        return _Query(self, "select").select(cols)

    def delete(self):
        return _Query(self, "delete")


def _existing(*triples):
    return [
        {"id": i, "season_id": s, "player_id": p, "position_bucket": b}
        for i, (s, p, b) in enumerate(triples, start=1)
    ]


def _emitted(*pairs):
    return [{"player_id": p, "position_bucket": b} for p, b in pairs]


def test_drops_bucket_the_rollup_no_longer_emits():
    # player 10 was AM+W, now only clears the threshold as W -> AM row must go
    client = FakeClient(_existing((1, 10, "AM"), (1, 10, "W")))
    pruned = prune_player_season_stats(client, 1, _emitted((10, "W")))
    assert pruned == 1
    assert [r["position_bucket"] for r in client.rows] == ["W"]


def test_keeps_every_bucket_still_emitted():
    client = FakeClient(_existing((1, 10, "AM"), (1, 10, "W")))
    pruned = prune_player_season_stats(client, 1, _emitted((10, "AM"), (10, "W")))
    assert pruned == 0
    assert len(client.rows) == 2


def test_leaves_other_seasons_untouched():
    client = FakeClient(_existing((1, 10, "AM"), (2, 10, "AM")))
    prune_player_season_stats(client, 1, _emitted((10, "W")))
    assert [r["season_id"] for r in client.rows] == [2]


def test_drops_player_absent_from_the_rollup_entirely():
    client = FakeClient(_existing((1, 10, "W"), (1, 20, "CB")))
    pruned = prune_player_season_stats(client, 1, _emitted((10, "W")))
    assert pruned == 1
    assert [r["player_id"] for r in client.rows] == [10]


def test_empty_rollup_prunes_nothing():
    # an empty rollup means the source fetch failed — must not wipe the season
    client = FakeClient(_existing((1, 10, "W"), (1, 20, "CB")))
    assert prune_player_season_stats(client, 1, []) == 0
    assert len(client.rows) == 2
