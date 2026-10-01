"""Vuelve a generar los datos de EA1 usando los JSON guardados."""

from pathlib import Path
import argparse
import hashlib
import json

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CITIES = [
    ("Medellin", 6.2442, -75.5812, 110),
    ("Bogota", 4.7110, -74.0721, 130),
    ("Cali", 3.4516, -76.5320, 115),
    ("Barranquilla", 10.9685, -74.7813, 125),
    ("Bucaramanga", 7.1193, -73.1227, 100),
]


def run(raw_directory: Path, database: Path) -> dict:
    manifest = json.loads((raw_directory / "manifest.json").read_text(encoding="utf-8"))
    frames = []
    for city, latitude, longitude, _ in CITIES:
        filename = f"{city.lower()}_weather.json"
        path = raw_directory / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[filename]:
            raise ValueError(f"La respuesta de EA1 cambió: {filename}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["timezone"] != "America/Bogota":
            raise ValueError("La respuesta no usa la zona horaria de EA1")
        frame = pd.DataFrame(payload["hourly"])
        frame = frame.assign(city=city, latitude=latitude, longitude=longitude)
        frames.append(frame)
    weather = pd.concat(frames, ignore_index=True)
    before = len(weather)
    weather["time"] = pd.to_datetime(weather["time"], errors="raise")
    weather = weather.drop_duplicates().dropna(subset=["time", "city", "temperature_2m"])
    # Mantengo el orden de EA1 para obtener los mismos valores de energía simulada.
    rng = np.random.default_rng(42)
    hours = weather["time"].dt.hour
    base = weather["city"].map({city: value for city, _, _, value in CITIES})
    factor = np.select([hours.between(18, 21), hours.between(7, 9)], [1.25, 1.15], default=1.0)
    temperature = 1 + (weather["temperature_2m"] - 22).abs() * 0.015
    rain = 1 + weather["precipitation"].fillna(0) * 0.005
    weather["energy_kwh"] = (
        base * factor * temperature * rain * rng.normal(1, 0.05, len(weather))
    ).round(2)
    weather["synthetic_energy"] = True
    if len(weather) != 43800 or weather.duplicated(["city", "time"]).any():
        raise ValueError("La instantánea no contiene las 43.800 horas ciudad esperadas")
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        con.register("input_weather", weather)
        con.execute("""CREATE OR REPLACE TABLE staging_weather AS
            SELECT time::TIMESTAMP observation_time, city, latitude, longitude,
            temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m,
            energy_kwh, synthetic_energy FROM input_weather""")
        con.execute("""CREATE OR REPLACE TABLE dim_city AS
            SELECT row_number() OVER (ORDER BY city) city_id, * FROM
            (SELECT DISTINCT city, latitude, longitude FROM staging_weather)""")
        con.execute("""CREATE OR REPLACE TABLE dim_time AS
            SELECT row_number() OVER (ORDER BY observation_time) time_id,
            observation_time, observation_time::DATE observation_date,
            year(observation_time) AS year, month(observation_time) AS month,
            day(observation_time) AS day, hour(observation_time) AS hour,
            dayofweek(observation_time) AS weekday FROM
            (SELECT DISTINCT observation_time FROM staging_weather)""")
        con.execute("""CREATE OR REPLACE TABLE fact_weather_energy AS
            SELECT c.city_id, t.time_id, s.temperature_2m temperature_c,
            s.relative_humidity_2m humidity_pct, s.precipitation precipitation_mm,
            s.wind_speed_10m wind_speed_kmh, s.energy_kwh, s.synthetic_energy
            FROM staging_weather s JOIN dim_city c ON s.city=c.city
            JOIN dim_time t ON s.observation_time=t.observation_time""")
        counts = {
            table: con.sql(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ["staging_weather", "dim_city", "dim_time", "fact_weather_energy"]
        }
    return {
        "mode": "replay_archived_api_responses",
        "raw_rows": before,
        "retained_rows": len(weather),
        "tables": counts,
        "raw_sha256": manifest,
        "live_api_called": False,
        "synthetic_energy_seed": 42,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "src/data/raw")
    parser.add_argument("--db", type=Path, default=ROOT / "src/db/replayed.duckdb")
    args = parser.parse_args()
    print(json.dumps(run(args.raw, args.db), indent=2))
