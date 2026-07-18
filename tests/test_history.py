from datetime import datetime, timedelta, timezone

from history import (HistoryPoint, ObservationHistory, downsample_series,
                     render_ascii_plot)
from models import Observation


def observation(value):
    return Observation("test", "station", 1, 2, datetime.now(timezone.utc), pm25=value)


def test_history_keeps_only_recent_points():
    history = ObservationHistory(retention_hours=24)
    start = datetime(2026, 7, 18, tzinfo=timezone.utc)
    history.add([observation(10)], start)
    history.add([observation(20)], start + timedelta(hours=25))
    assert [point.value for point in history.points] == [20]


def test_history_aggregates_pm25_and_skips_empty_polls():
    history = ObservationHistory()
    assert history.add([observation(None)]) is None
    point = history.add([observation(10), observation(20)])
    assert point.value == 15


def test_ascii_plot_renders_scale_and_points():
    points = (HistoryPoint(datetime.now(timezone.utc), 10), HistoryPoint(datetime.now(timezone.utc), 20))
    chart = render_ascii_plot(points, width=10, height=4)
    assert "PM2.5 history" in chart
    assert "*" in chart


def test_downsample_series_preserves_time_range():
    start = datetime(2026, 7, 18, tzinfo=timezone.utc)
    points = tuple(HistoryPoint(start + timedelta(minutes=index), index) for index in range(100))
    result = downsample_series({"PurpleAir": points}, 10)["PurpleAir"]
    assert len(result) <= 10
    assert result[0].timestamp == points[0].timestamp
    assert result[-1].timestamp == points[-1].timestamp
