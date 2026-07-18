from config import CONFIG
from models import AQIReading, Observation
from providers.base import Provider, request_json
from providers.openmeteo import parse_timestamp


class IQAirProvider(Provider):
    name = "IQAir"

    def __init__(self, client, config=CONFIG):
        super().__init__(client)
        self.config = config

    async def fetch(self):
        if not self.config.iqair_key:
            return []
        payload = await request_json(
            self.client, "GET", "https://api.airvisual.com/v2/nearest_city",
            params={"lat": self.config.latitude, "lon": self.config.longitude, "key": self.config.iqair_key},
        )
        return [_observation(payload["data"])] if payload.get("status") == "success" else []


def _observation(data):
    coordinates = data.get("location", {}).get("coordinates", [0, 0])
    pollution = data.get("current", {}).get("pollution", {})
    values = pollution.get("p2", {})
    readings = _aqi_readings(pollution)
    return Observation(provider="IQAir", station=data.get("city", "Nearest city"),
                       latitude=coordinates[1], longitude=coordinates[0],
                       timestamp=parse_timestamp(pollution["ts"]), pm25=values.get("conc"),
                       aqi=pollution.get("aqius"), aqi_readings=readings, raw=data)


def _aqi_readings(pollution):
    readings = []
    if pollution.get("aqius") is not None:
        readings.append(AQIReading(pollution["aqius"], "us_epa"))
    if pollution.get("aqicn") is not None:
        readings.append(AQIReading(pollution["aqicn"], "china"))
    return readings
