import re
from datetime import datetime, timedelta, timezone
from math import nan

from alerts import AlertMonitor
from history import build_series, render_ascii_plot
from models import Observation
from stats import summarize
from storage import ObservationRepository


def observation(provider="test", value=10, timestamp=None):
    return Observation(provider, "station", 1, 2, timestamp or datetime.now(timezone.utc), pm25=value)


def test_repository_round_trips_and_prunes(tmp_path):
    repository = ObservationRepository(str(tmp_path / "air.db"))
    try:
        repository.save([observation(value=12)])
        assert repository.since(24)[0].pm25 == 12
        old = observation(value=1, timestamp=datetime.now(timezone.utc) - timedelta(hours=25))
        repository.save([old])
        repository.prune(24)
        assert [item.pm25 for item in repository.since(24)] == [12]
    finally:
        repository.close()


def test_statistics_reject_invalid_values():
    result = summarize([observation(value=-1), observation(value=nan), observation(value=20)])
    assert result.count == 1
    assert result.median == 20


def test_provider_series_and_chart_have_legend():
    timestamp = datetime(2026, 7, 18, tzinfo=timezone.utc)
    series = build_series([observation("AirNow", 10, timestamp), observation("PurpleAir", 20, timestamp)])
    chart = render_ascii_plot(series, width=20, height=4)
    assert set(series) == {"AirNow", "PurpleAir", "Overall"}
    assert "Legend:" in chart
    assert "AirNow" in chart
    assert re.search(r"\d{2}:\d{2}", chart)


def test_alert_triggers_on_crossing_and_respects_cooldown():
    now = datetime.now(timezone.utc)
    monitor = AlertMonitor(35, cooldown_seconds=3600)
    assert monitor.evaluate([observation(value=40)], now) is not None
    assert monitor.evaluate([observation(value=40)], now + timedelta(minutes=5)) is None
    assert monitor.evaluate([observation(value=20)], now + timedelta(minutes=6)) is None
    assert monitor.evaluate([observation(value=40)], now + timedelta(minutes=7)) is not None
