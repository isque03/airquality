"""Air-quality index calculations based on published EPA breakpoints."""

from math import isfinite

# PM2.5 breakpoints for the U.S. AQI. Concentrations are in µg/m³ and are
# truncated to one decimal place before interpolation, as specified by EPA.
_PM25_BREAKPOINTS = (
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
)


def pm25_us_aqi(concentration: float | None) -> int | None:
    """Calculate a concentration-based U.S. AQI for PM2.5.

    The caller is responsible for supplying an averaging period appropriate
    for the use case. PurpleAir's live sensor value is a short-term proxy,
    so its result is labeled as calculated rather than provider-reported.
    """
    if concentration is None or not isfinite(concentration) or concentration < 0:
        return None
    truncated = min(int(concentration * 10), 5000) / 10
    for low_concentration, high_concentration, low_aqi, high_aqi in _PM25_BREAKPOINTS:
        if truncated <= high_concentration:
            result = ((high_aqi - low_aqi) * (truncated - low_concentration)
                      / (high_concentration - low_concentration) + low_aqi)
            return round(result)
    return 500
