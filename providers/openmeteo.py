from datetime import datetime, timezone

from config import CONFIG
from models import AQIReading, Observation
from providers.base import Provider, request_json


class OpenMeteoProvider(Provider):
    name = "Open-Meteo"

    def __init__(self, client, config=CONFIG):
        super().__init__(client)
        self.config = config

    async def fetch(self):
        payload = await request_json(
            self.client, "GET", "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                "latitude": self.config.latitude, "longitude": self.config.longitude,
                "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,sulphur_dioxide,us_aqi,european_aqi",
            },
        )
        values = payload["current"]
        aqi_readings = _aqi_readings(values)
        return [Observation(
            provider=self.name, station="Forecast Model",
            latitude=self.config.latitude, longitude=self.config.longitude,
            timestamp=parse_timestamp(values["time"]), pm25=values.get("pm2_5"),
            pm10=values.get("pm10"), ozone=values.get("ozone"), source_type="modeled",
            no2=values.get("nitrogen_dioxide"), co=values.get("carbon_monoxide"),
            so2=values.get("sulphur_dioxide"), aqi_readings=aqi_readings, raw=values,
        )]


def _aqi_readings(values):
    readings = []
    if values.get("us_aqi") is not None:
        readings.append(AQIReading(values["us_aqi"], "us_epa"))
    if values.get("european_aqi") is not None:
        readings.append(AQIReading(values["european_aqi"], "european"))
    return readings


def parse_timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
