from datetime import datetime, timezone

from dashboard import DashboardRenderer, DashboardSnapshot, resolve_theme
from main import KeyboardController
from models import AQIReading, Observation


def snapshot(metric="pm25"):
    observation = Observation(
        provider="PurpleAir", station="Sensor", latitude=1, longitude=2,
        timestamp=datetime(2026, 7, 18, 12, tzinfo=timezone.utc), pm25=10,
        aqi_readings=[AQIReading(53, "us_epa", "pm25", "calculated")],
    )
    return DashboardSnapshot([observation], [observation], {}, metric, None,
                             datetime(2026, 7, 18, 12, tzinfo=timezone.utc))


def test_plain_dashboard_labels_selected_metric_and_calculated_aqi():
    rendered = DashboardRenderer(30, 4).render(snapshot("aqi_us"), styled=False)
    assert "Metric: U.S. AQI" in rendered
    assert "AQI=53 US calc" in rendered
    assert "U.S. AQI history (AQI" in rendered


def test_styled_dashboard_handles_plotext_output(monkeypatch):
    class FakePlotext:
        def clear_figure(self): pass
        def plotsize(self, width, height): pass
        def title(self, value): pass
        def ylabel(self, value): pass
        def axes_color(self, value): pass
        def ticks_color(self, value): pass
        def yticks(self, ticks, labels): pass
        def plot(self, x, y, marker, color, label): pass
        def xticks(self, positions, labels): pass
        def show(self): print("fake chart")

    monkeypatch.setitem(__import__("sys").modules, "plotext", FakePlotext())
    rendered = DashboardRenderer(30, 4).render(snapshot(), styled=True)
    assert rendered is not None
    chart = DashboardRenderer(30, 4)._chart(snapshot(), styled=True)
    assert max(len(line) for line in chart.plain.splitlines()) <= 30


def test_keyboard_controller_cycles_metrics_and_quits():
    controller = KeyboardController("pm25")
    controller.handle_key("j")
    assert controller.metric == "pm10"
    controller.handle_key("k")
    assert controller.metric == "pm25"
    controller.handle_key("r")
    assert controller.wake.is_set()
    controller.handle_key("q")
    assert controller.quit is True


def test_auto_theme_uses_terminal_background_hint(monkeypatch):
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert resolve_theme("auto") == "light"
    assert resolve_theme("dark") == "dark"


def test_dashboard_dimensions_follow_terminal(monkeypatch):
    monkeypatch.setattr("dashboard.get_terminal_size", lambda fallback: (100, 40))
    assert DashboardRenderer(72, 20).dimensions() == (96, 20)


def test_aqi_summary_uses_median_and_preserves_maximum_detail():
    observations = [
        Observation("PurpleAir", "a", 1, 2, datetime.now(timezone.utc), pm25=80,
                    aqi_readings=[AQIReading(170, "us_epa", "pm25", "calculated")]),
        Observation("PurpleAir", "b", 1, 2, datetime.now(timezone.utc), pm25=80,
                    aqi_readings=[AQIReading(170, "us_epa", "pm25", "calculated")]),
        Observation("PurpleAir", "c", 1, 2, datetime.now(timezone.utc), pm25=400,
                    aqi_readings=[AQIReading(500, "us_epa", "pm25", "calculated")]),
    ]
    rendered = DashboardRenderer(30, 10)._plain_summary(
        DashboardSnapshot(observations, observations, {}, "pm25", None, datetime.now(timezone.utc)))
    assert "AQI=170 US calc (max 500)" in rendered
