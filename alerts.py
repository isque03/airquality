from datetime import datetime, timedelta, timezone

from models import Observation
from stats import summarize


class AlertMonitor:
    def __init__(self, threshold: float | None, cooldown_seconds: float):
        self.threshold = threshold
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self._last_alert: datetime | None = None
        self._was_above = False

    def evaluate(self, observations: list[Observation], now: datetime | None = None) -> str | None:
        if self.threshold is None:
            return None
        summary = summarize(observations)
        if summary is None:
            return None
        current = now or datetime.now(timezone.utc)
        above = summary.median >= self.threshold
        crossing = above and not self._was_above
        cooled_down = self._last_alert is None or current - self._last_alert >= self.cooldown
        self._was_above = above
        if not (above and (crossing or cooled_down)):
            return None
        self._last_alert = current
        return f"ALERT PM2.5 median={summary.median:.2f} exceeds {self.threshold:.2f} µg/m³"
