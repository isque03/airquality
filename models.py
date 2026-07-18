from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Measurement:
    value: float
    units: str
    averaging_period: str | None = None


@dataclass(frozen=True, slots=True)
class AQIReading:
    value: float
    scale: str
    pollutant: str | None = None
    kind: str = "overall"
    averaging_period: str | None = None


@dataclass(slots=True)
class Observation:
    provider: str
    station: str
    latitude: float
    longitude: float
    timestamp: datetime
    pm25: float | None = None
    pm10: float | None = None
    ozone: float | None = None
    no2: float | None = None
    co: float | None = None
    so2: float | None = None
    aqi: int | None = None
    units: str = "µg/m³"
    measurement_units: dict[str, str] = field(default_factory=dict)
    averaging_periods: dict[str, str] = field(default_factory=dict)
    aqi_readings: list[AQIReading] = field(default_factory=list)
    sensor_id: str | None = None
    source_type: str = "measured"
    indoor: bool | None = None
    raw: dict | None = None

    def measurements(self) -> dict[str, Measurement]:
        values = {"pm25": self.pm25, "pm10": self.pm10, "ozone": self.ozone,
                  "no2": self.no2, "co": self.co, "so2": self.so2}
        return {metric: Measurement(value, self.measurement_units.get(metric, self.units),
                                    self.averaging_periods.get(metric))
                for metric, value in values.items() if value is not None}

    def aqi_for(self, scale: str) -> list[AQIReading]:
        return [reading for reading in self.aqi_readings if reading.scale == scale]


def metric_value(observation: Observation, metric: str) -> float | None:
    if metric == "aqi_us":
        values = [reading.value for reading in observation.aqi_for("us_epa")]
        return max(values) if values else None
    if metric == "aqi_european":
        values = [reading.value for reading in observation.aqi_for("european")]
        return max(values) if values else None
    if metric == "aqi_china":
        values = [reading.value for reading in observation.aqi_for("china")]
        return max(values) if values else None
    return getattr(observation, metric, None)
