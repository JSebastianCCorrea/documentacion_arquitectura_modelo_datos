"""Materializa en SQLite el conjunto enriquecido, separando las dos granularidades."""

from pathlib import Path
import argparse
import json
import sqlite3
import tempfile
import os
from contextlib import closing

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CITY = ["city_id", "city", "latitude", "longitude", "country_code", "geoname_id",
        "elevation_m", "matched_geography", "municipality_code", "municipality_name",
        "department_code", "department_name", "divipola_year", "matched_municipalities",
        "reference_temperature_c", "parameter_scope", "matched_thermal"]
DATE = ["local_date", "year", "month", "day", "holiday_name", "is_holiday",
        "is_weekend", "matched_calendar", "is_business_day"]
HOUR = ["hour", "day_period", "matched_hours"]
TIME = ["time_id", "observation_time", "observation_time_utc", "local_date", "hour", "timezone"]
SOLAR = ["city_id", "local_date", "shortwave_radiation_sum_mj_m2", "daylight_seconds",
         "sunshine_seconds", "matched_solar", "radiation_kwh_m2_day", "daylight_hours", "sunshine_hours"]
BOOL = {"synthetic_energy", "is_outlier", "is_holiday", "is_weekend", "is_business_day"}
INT = {"city_id", "time_id", "source_row", "geoname_id", "divipola_year", "year", "month", "day", "hour"}
TEXT = {"city", "observation_time", "observation_time_utc", "timezone", "local_date",
        "imputed_fields", "quality_status", "outlier_fields", "country_code", "municipality_code",
        "municipality_name", "department_code", "department_name", "parameter_scope",
        "holiday_name", "day_period", "enrichment_status"}


def is_boolean(field):
    return field in BOOL or field.startswith(("matched_", "outlier_")) and field != "outlier_fields"


def sql_type(field):
    return "TEXT" if field in TEXT else "INTEGER" if field in INT or is_boolean(field) else "REAL"


def read_enriched(path):
    frame = pd.read_csv(path, keep_default_na=False, dtype=str)
    for field in frame:
        if is_boolean(field):
            if not frame[field].isin(["True", "False"]).all():
                raise ValueError(f"Booleano inválido: {field}")
            frame[field] = frame[field].map({"True": 1, "False": 0}).astype("int64")
        elif sql_type(field) != "TEXT":
            # float() conserva el redondeo binario del decimal escrito por EA3.
            # El conversor genérico de Pandas puede variar un último bit.
            frame[field] = (frame[field].map(float) if sql_type(field) == "REAL"
                            else pd.to_numeric(frame[field], errors="raise"))
            if not np.isfinite(frame[field]).all():
                raise ValueError(f"Número no finito en {field}")
            if sql_type(field) == "INTEGER":
                if (frame[field] % 1 != 0).any():
                    raise ValueError(f"Identificador fraccionario en {field}")
                frame[field] = frame[field].astype("int64")
    if not frame["enrichment_status"].eq("COMPLETE").all():
        raise ValueError("El modelo publicado exige enriquecimiento completo; corregir cobertura antes de cargar")
    if frame.duplicated(["city_id", "time_id"]).any():
        raise ValueError("La clave ciudad-hora está repetida")
    return frame


def split_tables(frame):
    dimensions = {"dim_city": (CITY, ["city_id"]), "dim_date": (DATE, ["local_date"]),
                  "dim_hour": (HOUR, ["hour"]), "dim_time": (TIME, ["time_id"]),
                  "fact_solar_day": (SOLAR, ["city_id", "local_date"])}
    tables = {}
    for name, (fields, key) in dimensions.items():
        part = frame[fields].drop_duplicates()
        if part.duplicated(key).any():
            raise ValueError(f"{name}: atributos distintos para la misma clave {key}")
        tables[name] = part.sort_values(key)
    assigned = set(CITY + DATE + HOUR + TIME + SOLAR)
    fields = ["source_row", "city_id", "time_id"] + [f for f in frame if f not in assigned and f != "source_row"]
    tables["fact_hourly"] = frame[fields].sort_values("source_row")
    return tables


def schema_for(tables, columns):
    constraints = {
        "dim_city": ["PRIMARY KEY (city_id)", "UNIQUE (city)", "UNIQUE (municipality_code)",
                     "CHECK (length(municipality_code)=5 AND municipality_code NOT GLOB '*[^0-9]*')",
                     "CHECK (length(department_code)=2 AND department_code NOT GLOB '*[^0-9]*')"],
        "dim_date": ["PRIMARY KEY (local_date)", "CHECK (month BETWEEN 1 AND 12)", "CHECK (day BETWEEN 1 AND 31)"],
        "dim_hour": ["PRIMARY KEY (hour)", "CHECK (hour BETWEEN 0 AND 23)"],
        "dim_time": ["PRIMARY KEY (time_id)", "UNIQUE (observation_time)", "UNIQUE (observation_time_utc)",
                     "UNIQUE (local_date, hour)", "FOREIGN KEY (local_date) REFERENCES dim_date(local_date)",
                     "FOREIGN KEY (hour) REFERENCES dim_hour(hour)"],
        "fact_solar_day": ["PRIMARY KEY (city_id, local_date)", "FOREIGN KEY (city_id) REFERENCES dim_city(city_id)",
                           "FOREIGN KEY (local_date) REFERENCES dim_date(local_date)",
                           "CHECK (shortwave_radiation_sum_mj_m2 >= 0)",
                           "CHECK (sunshine_seconds BETWEEN 0 AND daylight_seconds)",
                           "CHECK (daylight_seconds BETWEEN 0 AND 86400)"],
        "fact_hourly": ["PRIMARY KEY (source_row)", "UNIQUE (city_id, time_id)",
                        "FOREIGN KEY (city_id) REFERENCES dim_city(city_id)",
                        "FOREIGN KEY (time_id) REFERENCES dim_time(time_id)",
                        "CHECK (humidity_pct BETWEEN 0 AND 100)", "CHECK (energy_kwh >= 0)",
                        "CHECK (precipitation_mm >= 0)", "CHECK (wind_speed_kmh >= 0)"]}
    statements = ["PRAGMA foreign_keys = ON;"]
    for name, frame in tables.items():
        definitions = [f'"{f}" {sql_type(f)} NOT NULL' + (f' CHECK ("{f}" IN (0,1))' if is_boolean(f) else '') for f in frame]
        statements.append(f"CREATE TABLE {name} (\n  " + ",\n  ".join(definitions + constraints[name]) + "\n) STRICT;")
    aliases = {"dim_city": "c", "dim_date": "d", "dim_hour": "h", "dim_time": "t", "fact_solar_day": "s", "fact_hourly": "f"}
    mapping = {}
    for table, frame in tables.items():
        for field in frame:
            mapping.setdefault(field, aliases[table])
    selection = ",\n  ".join(f'{mapping[field]}."{field}" AS "{field}"' for field in columns)
    statements.append('CREATE INDEX idx_hourly_time ON fact_hourly(time_id);')
    statements.append('CREATE INDEX idx_solar_date ON fact_solar_day(local_date);')
    statements.append(f"""CREATE VIEW enriched_data AS SELECT
  {selection}
FROM fact_hourly f
JOIN dim_city c ON c.city_id=f.city_id
JOIN dim_time t ON t.time_id=f.time_id
JOIN dim_date d ON d.local_date=t.local_date
JOIN dim_hour h ON h.hour=t.hour
JOIN fact_solar_day s ON s.city_id=f.city_id AND s.local_date=t.local_date;""")
    return "\n\n".join(statements) + "\n"


def run(source: Path, database: Path, schema_path: Path, audit_path: Path):
    frame = read_enriched(source)
    tables = split_tables(frame)
    sql = schema_for(tables, list(frame.columns))
    database.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(suffix=".sqlite", dir=database.parent)
    os.close(handle)
    try:
        with closing(sqlite3.connect(temporary)) as con:
            con.executescript(sql)
            for name, data in tables.items():
                con.executemany(f"INSERT INTO {name} VALUES ({','.join('?' for _ in data.columns)})",
                                data.itertuples(index=False, name=None))
            if con.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("El modelo contiene referencias huérfanas")
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(integrity)
            recovered = pd.read_sql_query("SELECT * FROM enriched_data ORDER BY source_row", con)
            pd.testing.assert_frame_equal(frame.sort_values("source_row").reset_index(drop=True), recovered,
                                          check_dtype=False, check_exact=True)
            catalog = {name: {"rows": len(data), "columns": con.execute(f"PRAGMA table_info({name})").fetchall(),
                              "foreign_keys": con.execute(f"PRAGMA foreign_key_list({name})").fetchall()}
                       for name, data in tables.items()}
            con.commit()
        os.replace(temporary, database)
    finally:
        Path(temporary).unlink(missing_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(sql, encoding="utf-8")
    report = {"status": "PASS", "engine": "SQLite", "sqlite_version": sqlite3.sqlite_version,
              "view_rows": len(recovered), "view_columns": len(recovered.columns),
              "roundtrip_exact": True, "integrity_check": integrity, "foreign_key_violations": 0, "tables": catalog}
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "src/data/enriched_full.csv")
    parser.add_argument("--db", type=Path, default=ROOT / "src/db/analytics.sqlite")
    args = parser.parse_args()
    result = run(args.csv, args.db, ROOT / "src/sql/schema.sql", ROOT / "src/static/auditoria/model_validation.json")
    print(f"SQLite: {result['view_rows']} filas, {result['view_columns']} columnas, reconstrucción exacta.")
