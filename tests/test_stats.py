from datetime import datetime, timezone

from models import Observation
from stats import render, summarize


def observation(value):
    return Observation("test", "station", 1, 2, datetime.now(timezone.utc), pm25=value)


def test_summarize_returns_statistics():
    result = summarize([observation(1), observation(3), observation(5)])
    assert result.count == 3
    assert result.mean == 3
    assert result.median == 3
    assert result.minimum == 1
    assert result.maximum == 5


def test_summarize_handles_empty_values():
    assert summarize([observation(None)]) is None
    assert "No PM2.5" in render([observation(None)])
