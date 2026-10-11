"""Tests for clean_phrase and its use in extract_phrases (leading list markers)."""

import sys
import types

import pandas as pd
import pytest

from pub_dialogue import address


@pytest.mark.parametrize("raw, expected", [
    ("- impact on natural ecosystems", "impact on natural ecosystems"),
    ("  -  irreversible consequences ", "irreversible consequences"),
    ("• lack of oversight", "lack of oversight"),
    ("* fear of job losses", "fear of job losses"),
    ("– distrust of companies", "distrust of companies"),
    ("1. data misuse", "data misuse"),
    ("12) loss of control", "loss of control"),
    ("loss of control", "loss of control"),
    # Numbers and hyphens that are part of the phrase are kept
    ("2.5 degree warming risks", "2.5 degree warming risks"),
    ("5G health worries", "5G health worries"),
    ("long-term safety risks", "long-term safety risks"),
    ("-", ""),
])
def test_clean_phrase(raw, expected):
    assert address.clean_phrase(raw) == expected


def test_extract_phrases_strips_markers_and_sentinels(monkeypatch):
    # extract_phrases imports litellm for its retry wrapper; stub it so the
    # test runs with or without litellm installed.
    fake = types.SimpleNamespace(RateLimitError=type("RateLimitError", (Exception,), {}))
    monkeypatch.setitem(sys.modules, "litellm", fake)

    class Client:
        def complete(self, messages, **kwargs):
            return "- privacy worries\n• job losses\n-\n- NO_CONCERN\n3. unequal access"

    row = (0, pd.Series({"chunk_id": "c0", "text": "Some paragraph."}))
    result = address.extract_phrases(row, "concern", Client(), tech_words=[])
    assert result.raw_phrases == ["privacy worries", "job losses", "unequal access"]
    assert result.retained_phrases == ["privacy worries", "job losses", "unequal access"]
