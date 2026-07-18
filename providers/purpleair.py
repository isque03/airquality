from datetime import datetime, timezone

from aqi import pm25_us_aqi
from config import CONFIG
from models import AQIReading, Observation
from providers.base import Provider, request_json


class PurpleAirProvider(Provider):
    name = "PurpleAir"

    def __init__(self, client, config=CONFIG):
        super().__init__(client)
        self.config = config

    async def fetch(self):
        if not self.config.purpleair_key:
            return []
        delta = self.config.radius_km / 111
        fields = "sensor_index,name,latitude,longitude,pm2.5_atm,pm2.5_10minute,last_seen"
        payload = await request_json(
            self.client, "GET", "https://api.purpleair.com/v1/sensors",
            params={"fields": fields, "nwlat": self.config.latitude + delta,
                    "nwlng": self.config.longitude - delta, "selat": self.config.latitude - delta,
                    "selng": self.config.longitude + delta},
            headers={"X-API-Key": self.config.purpleair_key},
        )
        return [_observation(row, payload["fields"]) for row in payload.get("data", [])]


def _observation(row, fields):
    data = dict(zip(fields, row))
    pm25 = data.get("pm2.5_atm") or data.get("pm2.5_10minute")
    aqi = pm25_us_aqi(pm25)
    aqi_readings = ([AQIReading(value=aqi, scale="us_epa", pollutant="pm25",
                                kind="calculated", averaging_period="10-minute")]
                     if aqi is not None else [])
    return Observation(provider="PurpleAir", station=data.get("name", "Unknown"),
                       latitude=data["latitude"], longitude=data["longitude"],
                       timestamp=datetime.fromtimestamp(data["last_seen"], tz=timezone.utc),
                       pm25=pm25, aqi_readings=aqi_readings,
                       sensor_id=str(data.get("sensor_index", "")) or None, raw=data)
