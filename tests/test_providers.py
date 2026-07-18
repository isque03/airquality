from aqi import pm25_us_aqi
from providers.airnow import observations_from_records
from providers.openaq import _observations
from providers.purpleair import _observation


def test_airnow_groups_pollutants_into_one_station():
    records = [
        {"FullAQSCode": "1", "ReportingArea": "Town", "Latitude": 1, "Longitude": 2,
         "DateObserved": "2026-07-18", "HourObserved": 10, "ParameterName": "PM2.5", "Concentration": 8, "AQI": 34},
        {"FullAQSCode": "1", "ReportingArea": "Town", "Latitude": 1, "Longitude": 2,
         "DateObserved": "2026-07-18", "HourObserved": 10, "ParameterName": "Ozone", "Concentration": 2, "AQI": 20},
    ]
    result = observations_from_records("AirNow", records)
    assert len(result) == 1
    assert result[0].pm25 == 8
    assert result[0].ozone == 2
    assert result[0].aqi == 20


def test_openaq_uses_sensor_metadata_when_latest_omits_parameter():
    location = {"id": 7, "name": "Station", "coordinates": {"latitude": 1, "longitude": 2},
                "sensors": [{"id": 9, "parameter": {"name": "pm25"}}]}
    result = _observations("OpenAQ v3", location, [{"locationsId": 7, "sensorsId": 9,
             "datetime": {"utc": "2026-07-18T10:00:00Z"}, "value": 12}])
    assert result[0].pm25 == 12


def test_purpleair_decodes_columnar_sensor_response():
    result = _observation([7, "Sensor", 1, 2, 10, 11, 1_750_000_000],
                          ["sensor_index", "name", "latitude", "longitude", "pm2.5_atm", "pm2.5_10minute", "last_seen"])
    assert result.station == "Sensor"
    assert result.pm25 == 10
    assert result.aqi_for("us_epa")[0].kind == "calculated"
    assert result.aqi_for("us_epa")[0].value == 53


def test_pm25_us_aqi_uses_epa_breakpoint_interpolation():
    assert pm25_us_aqi(0) == 0
    assert pm25_us_aqi(9.0) == 50
    assert pm25_us_aqi(9.1) == 51
    assert pm25_us_aqi(35.4) == 100
    assert pm25_us_aqi(500) == 500
    assert pm25_us_aqi(-1) is None
