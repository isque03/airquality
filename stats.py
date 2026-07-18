from dataclasses import dataclass
from math import isfinite
from statistics import mean, median, quantiles, stdev

from models import Observation


@dataclass(frozen=True)
class Statistics:
    count: int
    mean: float
    median: float
    standard_deviation: float | None
    minimum: float
    maximum: float
    p10: float
    p90: float


def valid_pm25(observations: list[Observation]) -> list[Observation]:
    return [item for item in observations if _valid_value(item.pm25)]


def summarize(observations: list[Observation]) -> Statistics | None:
    values = [item.pm25 for item in valid_pm25(observations)]
    if not values:
        return None
    percentiles = quantiles(values, n=10, method="inclusive") if len(values) > 1 else [values[0]] * 9
    return Statistics(len(values), mean(values), median(values), stdev(values) if len(values) > 1 else None,
                      min(values), max(values), percentiles[0], percentiles[8])


def by_provider(observations: list[Observation]) -> dict[str, Statistics]:
    grouped: dict[str, list[Observation]] = {}
    for observation in valid_pm25(observations):
        grouped.setdefault(observation.provider, []).append(observation)
    return {provider: summary for provider, values in grouped.items() if (summary := summarize(values))}


def render(observations: list[Observation]) -> str:
    summary = summarize(observations)
    if summary is None:
        return "No PM2.5 observations available."
    lines = ["PM2.5 Summary", f"Samples  : {summary.count}", f"Mean     : {summary.mean:.2f}",
             f"Median   : {summary.median:.2f}", f"P10-P90  : {summary.p10:.2f}-{summary.p90:.2f}"]
    if summary.standard_deviation is not None:
        lines.append(f"Std Dev  : {summary.standard_deviation:.2f}")
    lines.extend([f"Min/Max  : {summary.minimum:.2f}/{summary.maximum:.2f}", "", "By provider:"])
    lines.extend(f"{provider:15}median={value.median:.2f} samples={value.count}"
                 for provider, value in sorted(by_provider(observations).items()))
    return "\n".join(lines)


def _valid_value(value: float | None) -> bool:
    return value is not None and isfinite(value) and value >= 0
