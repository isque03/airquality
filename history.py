from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from statistics import median

from models import Observation, metric_value
from stats import valid_pm25


@dataclass(frozen=True)
class HistoryPoint:
    timestamp: datetime
    value: float


class ObservationHistory:
    def __init__(self, retention_hours: float = 24):
        self.retention_hours = retention_hours
        self._points: list[HistoryPoint] = []

    @property
    def points(self) -> tuple[HistoryPoint, ...]:
        return tuple(self._points)

    def add(self, observations: list[Observation], timestamp: datetime | None = None):
        valid = valid_pm25(observations)
        if not valid:
            return None
        point = HistoryPoint(timestamp or datetime.now(timezone.utc), median(item.pm25 for item in valid))
        self._points.append(point)
        self._points = [item for item in self._points
                        if (point.timestamp - item.timestamp).total_seconds() <= self.retention_hours * 3600]
        return point


def render_ascii_plot(series: dict[str, tuple[HistoryPoint, ...]] | tuple[HistoryPoint, ...], width: int = 72,
                      height: int = 10, color: bool = False) -> str:
    if isinstance(series, tuple):
        series = {"overall": series}
    if not series:
        return "PM2.5 history (last 24 hours)\nNo history available yet."
    values = {name: _bucket(points, width) for name, points in series.items() if points}
    all_values = [value for points in values.values() for value in points]
    if not all_values:
        return "PM2.5 history (last 24 hours)\nNo history available yet."
    low, high = min(all_values), max(all_values)
    low, high = (max(0, low - 1), high + 1) if low == high else (low, high)
    rows = _render_rows(values, low, high, height, color)
    plot_width = max(len(points) for points in values.values())
    axis, times = _render_time_axis([point for points in series.values() for point in points], plot_width)
    labels = " ".join(f"{name[:12]}={_marker(index, color)}" for index, name in enumerate(values))
    title = _paint("PM2.5 history (µg/m³, last 24 hours)", "96", color)
    return "\n".join([title, *rows, axis, times, f"Legend: {labels}"])


def _render_rows(series, low: float, high: float, height: int, color: bool) -> list[str]:
    rows = []
    for row in range(height):
        threshold = high - (high - low) * row / max(1, height - 1)
        chars = [" "] * max(len(points) for points in series.values())
        for index, (name, points) in enumerate(series.items()):
            marker = _marker(index, color)
            for column, value in enumerate(points):
                if value >= threshold and value < threshold + (high - low) / max(1, height):
                    chars[column] = marker
        rows.append(f"{_paint(f'{threshold:6.1f}', '90', color)} |{''.join(chars)}")
    return rows


def _bucket(points: tuple[HistoryPoint, ...], width: int) -> list[float]:
    if len(points) <= width:
        return [point.value for point in points]
    return [median(point.value for point in points[index * len(points) // width:max(index + 1, (index + 1) * len(points) // width)])
            for index in range(width)]


def _render_time_axis(points: list[HistoryPoint], width: int) -> tuple[str, str]:
    start, end = min(point.timestamp for point in points), max(point.timestamp for point in points)
    axis = "       +" + "-" * width
    labels = f"       {start.astimezone().strftime('%H:%M')}"
    labels += " " * max(1, width - 10)
    labels += end.astimezone().strftime("%H:%M")
    return axis, labels


def _marker(index: int, color: bool) -> str:
    marker = "*+x#%@"[index % 6]
    return _paint(marker, ("95", "92", "96", "91", "94", "93")[index % 6], color)


def _paint(value: str, code: str, color: bool) -> str:
    return f"\033[{code}m{value}\033[0m" if color else value


def build_series(observations: list[Observation]) -> dict[str, tuple[HistoryPoint, ...]]:
    return build_metric_series(observations, "pm25")


def build_metric_series(observations: list[Observation], metric: str) -> dict[str, tuple[HistoryPoint, ...]]:
    grouped: dict[tuple[str, str], list[Observation]] = {}
    overall: dict[str, list[Observation]] = {}
    for observation in observations:
        value = metric_value(observation, metric)
        if value is None or not isfinite(value) or value < 0:
            continue
        timestamp = observation.timestamp.astimezone(timezone.utc).replace(second=0, microsecond=0)
        grouped.setdefault((observation.provider, timestamp.isoformat()), []).append(observation)
        overall.setdefault(timestamp.isoformat(), []).append(observation)
    provider_points: dict[str, list[HistoryPoint]] = {}
    for (provider, timestamp), values in grouped.items():
        provider_points.setdefault(provider, []).append(
            HistoryPoint(datetime.fromisoformat(timestamp), median(metric_value(item, metric) for item in values)))
    provider_points["Overall"] = [
        HistoryPoint(datetime.fromisoformat(timestamp), median(metric_value(item, metric) for item in values))
        for timestamp, values in overall.items()
    ]
    return {provider: tuple(sorted(points, key=lambda point: point.timestamp))
            for provider, points in provider_points.items()}


def downsample_series(series: dict[str, tuple[HistoryPoint, ...]], max_points: int):
    return {name: _downsample_points(points, max_points) for name, points in series.items()}


def _downsample_points(points: tuple[HistoryPoint, ...], max_points: int):
    if len(points) <= max_points:
        return points
    start, end = points[0].timestamp, points[-1].timestamp
    span = max((end - start).total_seconds(), 1)
    buckets: dict[int, list[HistoryPoint]] = {}
    for point in points:
        index = min(max_points - 1, int((point.timestamp - start).total_seconds() / span * max_points))
        buckets.setdefault(index, []).append(point)
    result = [HistoryPoint(items[len(items) // 2].timestamp, median(item.value for item in items))
              for _, items in sorted(buckets.items())]
    result[0] = points[0]
    result[-1] = points[-1]
    return tuple(result)
