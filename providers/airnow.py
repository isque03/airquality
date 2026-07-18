from datetime import datetime, timezone

from config import CONFIG
from models import AQIReading, Observation
from providers.base import Provider, request_json


class AirNowProvider(Provider):
    name = "AirNow"

    def __init__(self, client, config=CONFIG):
        super().__init__(client)
        self.config = config

    async def fetch(self):
        if not self.config.airnow_key:
            return []
        records = await request_json(
            self.client, "GET", "https://www.airnowapi.org/aq/observation/zipCode/current/",
            params={"format": "application/json", "zipCode": self.config.zip_code,
                    "distance": self.config.radius_km, "API_KEY": self.config.airnow_key},
        )
        return observations_from_records(self.name, records)


def observations_from_records(provider, records):
    grouped = {}
    for record in records:
        key = record.get("FullAQSCode") or record.get("SiteName", "unknown")
        observation = grouped.setdefault(key, _new_observation(provider, record))
        parameter = record.get("ParameterName", "").lower()
        value = record.get("Concentration")
        if parameter == "pm2.5": observation.pm25 = value
        elif parameter == "pm10": observation.pm10 = value
        elif parameter == "ozone": observation.ozone = value
        if record.get("AQI") is not None:
            observation.aqi = record["AQI"]
            observation.aqi_readings.append(AQIReading(record["AQI"], "us_epa", parameter, "nowcast"))
    return list(grouped.values())


def _new_observation(provider, record):
    hour = str(record.get("HourObserved", "00")).zfill(2)
    timestamp = f"{record.get('DateObserved', '')}T{hour}:00:00"
    return Observation(provider=provider, station=record.get("ReportingArea", record.get("SiteName", "Unknown")),
                       latitude=float(record.get("Latitude", 0)), longitude=float(record.get("Longitude", 0)),
                       timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
                       sensor_id=str(record.get("FullAQSCode", "")) or None, raw=record)
