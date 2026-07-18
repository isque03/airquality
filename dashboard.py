import io
import os
import re
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta
from shutil import get_terminal_size
from statistics import median

from history import build_metric_series, downsample_series, render_ascii_plot
from models import Observation, metric_value

METRICS = ("aqi_us", "aqi_european", "aqi_china", "pm25", "pm10", "ozone", "no2", "co", "so2")
METRIC_LABELS = {
    "aqi_us": "U.S. AQI", "aqi_european": "European AQI", "aqi_china": "China AQI",
    "pm25": "PM2.5", "pm10": "PM10", "ozone": "Ozone", "no2": "NO₂", "co": "CO", "so2": "SO₂",
}
THEME_COLORS = {
    "dark": {
        "border": ("cyan", "green", "blue"),
        "header": ("bold cyan", "bold blue"),
        "status_ok": "green", "status_error": "red", "axis": "white",
        "series": {"AirNow": "yellow", "IQAir": "blue", "Open-Meteo": "cyan",
                    "OpenAQ v3": "green", "PurpleAir": "magenta", "Overall": "white"},
    },
    "light": {
        "border": ("dark_cyan", "dark_green", "dark_blue"),
        "header": ("bold dark_cyan", "bold dark_blue"),
        "status_ok": "dark_green", "status_error": "dark_red", "axis": "dark_gray",
        "series": {"AirNow": "dark_yellow", "IQAir": "dark_blue", "Open-Meteo": "dark_cyan",
                    "OpenAQ v3": "dark_green", "PurpleAir": "dark_magenta", "Overall": "dark_gray"},
    },
}


def resolve_theme(theme: str) -> str:
    if theme in THEME_COLORS:
        return theme
    if theme == "auto":
        background = os.getenv("COLORFGBG", "").rsplit(";", 1)[-1]
        return "light" if background in {"7", "15"} else "dark"
    return "dark"


@dataclass(frozen=True)
class DashboardSnapshot:
    observations: list[Observation]
    history: list[Observation]
    errors: dict[str, Exception]
    metric: str
    alert: str | None
    polled_at: datetime


class DashboardRenderer:
    def __init__(self, width: int, height: int, theme: str = "auto"):
        self.width = width
        self.height = height
        self.theme = resolve_theme(theme)

    def dimensions(self) -> tuple[int, int]:
        columns, lines = get_terminal_size(fallback=(self.width, self.height + 18))
        width = min(120, max(40, columns - 4))
        height = min(20, max(10, lines - 18))
        return width, height

    def render(self, snapshot: DashboardSnapshot, styled: bool = True):
        if not styled:
            return self._plain(snapshot)
        try:
            from rich.console import Group
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text
        except ImportError:
            return self._plain(snapshot)
        chart = self._chart(snapshot, styled)
        title = f"AIR QUALITY  •  {snapshot.polled_at.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}"
        colors = THEME_COLORS[self.theme]
        borders = colors["border"]
        return Group(Panel(self._summary(snapshot, Table), title=title, border_style=borders[0]),
                     Panel(chart, title=f"{METRIC_LABELS[snapshot.metric]}  [j/k or ←/→ to change]", border_style=borders[1]),
                     Panel(self._health(snapshot, Table), title="Provider health", border_style=borders[2]))

    def _summary(self, snapshot, table_type):
        table = table_type(show_header=True, header_style=THEME_COLORS[self.theme]["header"][0])
        for column in ("Provider", "Stations", "PM2.5", "PM10", "O₃", "NO₂", "CO", "SO₂", "AQI"):
            table.add_column(column)
        providers = sorted({item.provider for item in snapshot.observations})
        for provider in providers:
            values = [item for item in snapshot.observations if item.provider == provider]
            table.add_row(provider, str(len(values)), *[_median(values, metric) for metric in
                          ("pm25", "pm10", "ozone", "no2", "co", "so2")], _aqi_text(values))
        if not providers:
            table.add_row("No observations", *(["-"] * 8))
        return table

    def _health(self, snapshot, table_type):
        colors = THEME_COLORS[self.theme]
        table = table_type(show_header=True, header_style=colors["header"][1])
        table.add_column("Provider")
        table.add_column("Status")
        table.add_column("Results")
        for provider in sorted(set(snapshot.errors) | {item.provider for item in snapshot.observations}):
            error = snapshot.errors.get(provider)
            count = sum(item.provider == provider for item in snapshot.observations)
            status = f"[{colors['status_error']}]ERROR {type(error).__name__}[/{colors['status_error']}]" if error else f"[{colors['status_ok']}]OK[/{colors['status_ok']}]"
            table.add_row(provider, status, str(count))
        return table

    def _chart(self, snapshot, styled):
        series = build_metric_series(snapshot.history, snapshot.metric)
        width, height = self.dimensions()
        try:
            import plotext as plt
            from rich.text import Text
        except ImportError:
            chart = render_ascii_plot(series, width, height, styled)
            return chart.replace("PM2.5 history", f"{METRIC_LABELS[snapshot.metric]} history", 1)
        points = {name: values for name, values in
                  downsample_series(series, max(20, width - 12)).items() if values}
        if not points:
            return "No data for this metric in the selected history window."
        plt.clear_figure()
        plt.plotsize(width, height)
        plt.title(METRIC_LABELS[snapshot.metric])
        plt.ylabel("AQI" if snapshot.metric.startswith("aqi_") else "µg/m³")
        axis_color = THEME_COLORS[self.theme]["axis"]
        plt.axes_color(axis_color)
        plt.ticks_color(axis_color)
        all_values = [point.value for values in points.values() for point in values]
        all_points = [point for values in points.values() for point in values]
        origin = min(point.timestamp for point in all_points)
        low, high = min(all_values), max(all_values)
        if low == high:
            low, high = low - 1, high + 1
        y_ticks = [low + (high - low) * index / 5 for index in range(6)]
        plt.yticks(y_ticks, [f"{value:.1f}" for value in y_ticks])
        for name, values in points.items():
            series_colors = THEME_COLORS[self.theme]["series"]
            segments = _chart_segments(values)
            for segment_index, segment in enumerate(segments):
                x = [_relative_minutes(point, origin) for point in segment]
                plt.plot(x, [point.value for point in segment], marker="dot",
                         color=series_colors.get(name, axis_color),
                         label=name if segment_index == 0 else None)
        axis_points = points.get("Overall") or next(iter(points.values()))
        tick_points = axis_points[::max(1, len(axis_points) // 5)]
        plt.xticks([_relative_minutes(point, origin) for point in tick_points],
                   [point.timestamp.astimezone().strftime("%H:%M") for point in tick_points])
        output = io.StringIO()
        with redirect_stdout(output):
            plt.show()
        return Text.from_ansi(_strip_plotext_background(output.getvalue()))

    def _plain(self, snapshot):
        width, height = self.dimensions()
        chart = render_ascii_plot(build_metric_series(snapshot.history, snapshot.metric), width, height, False)
        chart = chart.replace("PM2.5 history", f"{METRIC_LABELS[snapshot.metric]} history", 1)
        if snapshot.metric.startswith("aqi_"):
            chart = chart.replace("(µg/m³,", "(AQI,", 1)
        return self._plain_summary(snapshot) + "\n" + chart

    def _plain_summary(self, snapshot):
        lines = [f"AIR QUALITY {snapshot.polled_at.isoformat()}", f"Metric: {METRIC_LABELS[snapshot.metric]}"]
        for provider in sorted({item.provider for item in snapshot.observations}):
            values = [item for item in snapshot.observations if item.provider == provider]
            lines.append(f"{provider}: PM2.5={_median(values, 'pm25')} AQI={_aqi_text(values)}")
        return "\n".join(lines)


def _median(observations: list[Observation], metric: str) -> str:
    values = [metric_value(item, metric) for item in observations]
    values = [value for value in values if value is not None]
    return f"{median(values):.1f}" if values else "-"


def _relative_minutes(point, origin) -> float:
    return (point.timestamp - origin).total_seconds() / 60


def _strip_plotext_background(output: str) -> str:
    return re.sub(r"\x1b\[(?:48;5;\d+|49)m", "", output)


def _chart_segments(points):
    if len(points) < 2:
        return [points]
    span = points[-1].timestamp - points[0].timestamp
    max_gap = max(span / max(len(points), 1) * 4, timedelta(hours=2))
    segments = [[points[0]]]
    for point in points[1:]:
        if point.timestamp - segments[-1][-1].timestamp > max_gap:
            segments.append([point])
        else:
            segments[-1].append(point)
    return segments


def _aqi_text(observations: list[Observation]) -> str:
    readings = [reading for item in observations for reading in item.aqi_for("us_epa")]
    if not readings:
        return "-"
    values = [reading.value for reading in readings]
    representative, maximum = median(values), max(values)
    suffix = " calc" if all(reading.kind == "calculated" for reading in readings) else ""
    detail = f" (max {maximum:.0f})" if maximum > representative else ""
    return f"{representative:.0f} US{suffix}{detail}"
