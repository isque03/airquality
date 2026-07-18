import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from models import AQIReading, Observation


class ObservationRepository:
    def __init__(self, database_path: str):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()
        self._migrate_schema()

    def save(self, observations: list[Observation]):
        rows = [_to_row(observation) for observation in observations]
        self.connection.executemany(
            """INSERT INTO observations
            (provider, station, sensor_id, timestamp, latitude, longitude, pm25, pm10,
             ozone, no2, co, so2, aqi, units, measurement_units_json, averaging_periods_json,
             aqi_readings_json, source_type, indoor, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        self.connection.commit()

    def since(self, hours: float) -> list[Observation]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = self.connection.execute(
            "SELECT * FROM observations WHERE timestamp >= ? ORDER BY timestamp",
            (cutoff.isoformat(),),
        ).fetchall()
        return [_from_row(row) for row in rows]

    def prune(self, hours: float):
        """Explicitly remove old data when an operator requests cleanup."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        self.connection.execute("DELETE FROM observations WHERE timestamp < ?", (cutoff.isoformat(),))
        self.connection.commit()

    def close(self):
        self.connection.close()

    def _create_schema(self):
        self.connection.executescript(
            """CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL,
                station TEXT NOT NULL,
                sensor_id TEXT,
                timestamp TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                pm25 REAL, pm10 REAL, ozone REAL, no2 REAL, co REAL, so2 REAL,
                aqi INTEGER, units TEXT NOT NULL, source_type TEXT NOT NULL,
                indoor INTEGER, raw_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_observations_provider_time
                ON observations(provider, timestamp);"""
        )
        self.connection.commit()

    def _migrate_schema(self):
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(observations)")}
        for name, definition in (
            ("measurement_units_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("averaging_periods_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("aqi_readings_json", "TEXT NOT NULL DEFAULT '[]'"),
        ):
            if name not in columns:
                self.connection.execute(f"ALTER TABLE observations ADD COLUMN {name} {definition}")
        self.connection.commit()


def _to_row(item: Observation):
    aqi_readings = [asdict(reading) for reading in item.aqi_readings]
    return (item.provider, item.station, item.sensor_id, item.timestamp.isoformat(), item.latitude,
            item.longitude, item.pm25, item.pm10, item.ozone, item.no2, item.co, item.so2,
            item.aqi, item.units, json.dumps(item.measurement_units), json.dumps(item.averaging_periods),
            json.dumps(aqi_readings), item.source_type, item.indoor, json.dumps(item.raw or {}))


def _from_row(row: sqlite3.Row) -> Observation:
    return Observation(
        provider=row["provider"], station=row["station"], latitude=row["latitude"],
        longitude=row["longitude"], timestamp=datetime.fromisoformat(row["timestamp"]),
        pm25=row["pm25"], pm10=row["pm10"], ozone=row["ozone"], no2=row["no2"],
        co=row["co"], so2=row["so2"], aqi=row["aqi"], units=row["units"],
        measurement_units=json.loads(row["measurement_units_json"] or "{}"),
        averaging_periods=json.loads(row["averaging_periods_json"] or "{}"),
        aqi_readings=[AQIReading(**reading) for reading in json.loads(row["aqi_readings_json"] or "[]")],
        sensor_id=row["sensor_id"], source_type=row["source_type"], indoor=row["indoor"],
        raw=json.loads(row["raw_json"] or "{}"),
    )
