"""Tests for lens-grouping robustness: JSON mode, string IDs, retry to N runs."""

import json

from pub_dialogue.access import AccessStage
from pub_dialogue.address import AddressStage

GOOD = json.dumps({"framing_lenses": [
    {"name": "A", "description": "d", "suggested_clusters": ["0", 1]},
    {"name": "B", "description": "d", "suggested_clusters": [2, 3]},
]})


class FlakyClient:
    """Returns broken JSON on the calls listed in ``fail_on``."""

    def __init__(self, fail_on=()):
        self.calls = 0
        self.fail_on = set(fail_on)
        self.kwargs = []

    def complete(self, messages, **kwargs):
        self.calls += 1
        self.kwargs.append(kwargs)
        if self.calls in self.fail_on:
            return '{"framing_lenses": [ truncated'
        return GOOD


def _run(client, n_runs=5):
    stage = AddressStage(access=AccessStage())
    exemplars = {i: {"size": 5} for i in range(4)}
    return stage.generate_lens_grouping_multi(exemplars, {}, 4, "concern", client, n_runs=n_runs)


def test_failed_runs_are_retried_until_n_succeed():
    client = FlakyClient(fail_on={2, 4})
    _head, info = _run(client)
    assert info["n_runs"] == 5
    assert client.calls == 7


def test_json_mode_requested_and_ids_coerced_to_int():
    client = FlakyClient()
    head, _ = _run(client, n_runs=1)
    assert client.kwargs[0]["response_format"] == {"type": "json_object"}
    assert head["framing_lenses"][0]["suggested_clusters"] == [0, 1]


def test_gives_up_after_twice_n_attempts():
    client = FlakyClient(fail_on=set(range(2, 100)))
    _head, info = _run(client, n_runs=3)
    assert client.calls == 6
    assert info["n_runs"] == 1
