import asyncio

from config import CONFIG
from models import Observation
from providers.base import Provider, request_json
from providers.openmeteo import parse_timestamp


class OpenAQProvider(Provider):
    name = "OpenAQ v3"

    def __init__(self, client, config=CONFIG):
        super().__init__(client)
        self.config = config

    async def fetch(self):
        if not self.config.openaq_key:
            return []
        locations = await request_json(
            self.client, "GET", "https://api.openaq.org/v3/locations",
            params={"coordinates": f"{self.config.latitude},{self.config.longitude}",
                    "radius": self.config.radius_km * 1000, "limit": 10},
            headers={"X-API-Key": self.config.openaq_key},
        )
        results = await asyncio.gather(*(self._fetch_location(item) for item in locations.get("results", [])))
        return [observation for group in results for observation in group]

    async def _fetch_location(self, location):
        payload = await request_json(
            self.client, "GET", f"https://api.openaq.org/v3/locations/{location['id']}/latest",
            headers={"X-API-Key": self.config.openaq_key},
        )
        return _observations(self.name, location, payload.get("results", []))


def _observations(provider, location, measurements):
    parameters = {
        sensor.get("id"): sensor.get("parameter", {}).get("name", "")
        for sensor in location.get("sensors", [])
    }
    grouped = {}
    for item in measurements:
        key = item.get("locationsId", location["id"])
        current = grouped.setdefault(key, Observation(
            provider=provider, station=location.get("name", str(key)),
            latitude=location.get("coordinates", {}).get("latitude") or 0,
            longitude=location.get("coordinates", {}).get("longitude") or 0,
            timestamp=parse_timestamp(item["datetime"]["utc"]), sensor_id=str(item.get("sensorsId", "")) or None, raw=item,
        ))
        name = item.get("parameter", {}).get("name") or parameters.get(item.get("sensorsId"), "")
        name = name.lower()
        value = item.get("value")
        if name in {"pm25", "pm2.5"}: current.pm25 = value
        elif name == "pm10": current.pm10 = value
        elif name == "o3": current.ozone = value
        elif name == "no2": current.no2 = value
        elif name == "co": current.co = value
        elif name == "so2": current.so2 = value
    return list(grouped.values())
