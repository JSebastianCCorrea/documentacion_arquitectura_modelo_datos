"""Crea la base DuckDB del enriquecimiento a partir del CSV completo de EA2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "src/data/base/cleaned_full.csv"
DATABASE_PATH = ROOT / "src/db/cleaned.duckdb"
MANIFEST_PATH = ROOT / "src/db/base_manifest.json"
SOURCE_REPOSITORY = "https://github.com/JSebastianCCorrea/Preprocesamiento_Limpieza_de_Datos_en_Plataforma_de_Big_Data_en_la_Nube"
SOURCE_REPOSITORY_PATH = "sebastian_clavijo_correa/src/xlsx/cleaned_full.csv"

INTEGER_COLUMNS = ["city_id", "time_id", "source_row", "year", "month", "day", "hour"]
FLOAT_COLUMNS = [
    "latitude",
    "longitude",
    "temperature_c",
    "humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "energy_kwh",
    "temperature_zscore",
    "energy_zscore",
    "humidity_fraction",
    "precipitation_log1p",
]
BOOLEAN_COLUMNS = [
    "synthetic_energy",
    "is_outlier",
    "outlier_temperature_c",
    "outlier_humidity_pct",
    "outlier_precipitation_mm",
    "outlier_wind_speed_kmh",
    "outlier_energy_kwh",
]
TIME_COLUMNS = ["observation_time", "observation_time_utc"]
TEXT_COLUMNS = ["city", "imputed_fields", "quality_status", "outlier_fields", "timezone"]
COLUMN_ORDER = [
    "city_id",
    "time_id",
    "observation_time",
    "city",
    "latitude",
    "longitude",
    "temperature_c",
    "humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "energy_kwh",
    "synthetic_energy",
    "source_row",
    "year",
    "month",
    "day",
    "hour",
    "imputed_fields",
    "quality_status",
    "is_outlier",
    "outlier_fields",
    "outlier_temperature_c",
    "outlier_humidity_pct",
    "outlier_precipitation_mm",
    "outlier_wind_speed_kmh",
    "outlier_energy_kwh",
    "temperature_zscore",
    "energy_zscore",
    "humidity_fraction",
    "precipitation_log1p",
    "timezone",
    "observation_time_utc",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_base(path: Path) -> pd.DataFrame:
    # Un texto vacío indica que la fila no tiene marcas de calidad.
    frame = pd.read_csv(path, keep_default_na=False, dtype="string", encoding="utf-8")
    if frame.columns.tolist() != COLUMN_ORDER:
        raise ValueError("El CSV no tiene las 32 columnas esperadas de EA2, en su orden original")
    for column in INTEGER_COLUMNS:
        values = pd.to_numeric(frame[column], errors="raise")
        if not (values % 1 == 0).all():
            raise ValueError(f"Valores no enteros en {column}")
        frame[column] = values.astype("int64")
    for column in FLOAT_COLUMNS:
        # Uso float() para conservar el valor decimal que quedó guardado en el CSV.
        frame[column] = frame[column].map(float).astype("float64")
        if not np.isfinite(frame[column]).all():
            raise ValueError(f"Valores no finitos en {column}")
    for column in BOOLEAN_COLUMNS:
        if not frame[column].isin(["True", "False"]).all():
            raise ValueError(f"Valores booleanos inválidos en {column}")
        frame[column] = frame[column].map({"True": True, "False": False}).astype(bool)
    for column in TIME_COLUMNS:
        frame[column] = pd.to_datetime(frame[column], utc=True, errors="raise")
    frame["observation_time"] = frame["observation_time"].dt.tz_convert("America/Bogota")
    if not frame["observation_time"].dt.tz_convert("UTC").equals(frame["observation_time_utc"]):
        raise ValueError("Las horas local y UTC no representan los mismos instantes")
    if not frame["timezone"].eq("America/Bogota").all():
        raise ValueError("La zona horaria declarada no coincide con la base EA2")
    if len(frame) != 43800 or frame.duplicated(["city", "observation_time"]).any():
        raise ValueError("El volumen o la clave ciudad/hora difieren de EA2")
    if not frame["synthetic_energy"].all():
        raise ValueError("Se perdió la identificación de la energía sintética")
    return frame


def database_type(column: str) -> str:
    if column in INTEGER_COLUMNS:
        return "BIGINT"
    if column in FLOAT_COLUMNS:
        return "DOUBLE"
    if column in BOOLEAN_COLUMNS:
        return "BOOLEAN"
    if column in TIME_COLUMNS:
        return "TIMESTAMPTZ"
    return "VARCHAR"


def confirm_equal(expected: pd.DataFrame, observed: pd.DataFrame) -> None:
    left = expected.sort_values("source_row").reset_index(drop=True)
    right = observed.sort_values("source_row").reset_index(drop=True)
    if left.columns.tolist() != right.columns.tolist() or len(left) != len(right):
        raise ValueError("La base reconstruida cambió las filas o columnas del CSV")
    for column in COLUMN_ORDER:
        if column in TIME_COLUMNS:
            matches = (
                pd.to_datetime(left[column], utc=True) == pd.to_datetime(right[column], utc=True)
            ).all()
        elif column in TEXT_COLUMNS:
            matches = (left[column].astype(str) == right[column].astype(str)).all()
        else:
            matches = np.array_equal(left[column].to_numpy(), right[column].to_numpy())
        if not matches:
            raise ValueError(f"La lectura de DuckDB difiere del CSV en {column}")


def prepare_base(expected_sha256: str | None = None, ea2_commit: str | None = None) -> dict:
    previous = (
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    )
    expected_sha256 = expected_sha256 or previous.get("source", {}).get("sha256")
    ea2_commit = ea2_commit or previous.get("source", {}).get("commit")
    if not expected_sha256 or not ea2_commit:
        raise ValueError("La primera preparación requiere --expected-sha256 y --ea2-commit")
    actual_hash = sha256(CSV_PATH)
    if actual_hash != expected_sha256:
        raise ValueError("La copia del CSV no coincide con la huella del origen EA2")
    frame = read_base(CSV_PATH)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prepare_base_", dir=DATABASE_PATH.parent) as temporary:
        temporary_root = Path(temporary).resolve()
        if temporary_root.parent != DATABASE_PATH.parent.resolve():
            raise RuntimeError("El directorio temporal salió de src/db")
        temporary_database = temporary_root / "ingestion.db"
        with duckdb.connect(str(temporary_database)) as connection:
            connection.execute("SET TimeZone='America/Bogota'")
            connection.register("base_input", frame)
            expressions = ", ".join(
                f'CAST("{column}" AS {database_type(column)}) AS "{column}"'
                for column in COLUMN_ORDER
            )
            connection.execute(f"CREATE TABLE cleaned_data AS SELECT {expressions} FROM base_input")
            connection.execute(
                "CREATE UNIQUE INDEX city_hour ON cleaned_data(city, observation_time)"
            )
            schema = [
                {"column": row[0], "type": row[1]}
                for row in connection.execute("DESCRIBE cleaned_data").fetchall()
            ]
            round_trip = connection.execute("SELECT * FROM cleaned_data ORDER BY source_row").df()
            confirm_equal(frame, round_trip)
            connection.execute("CHECKPOINT")
        if sha256(CSV_PATH) != actual_hash:
            raise RuntimeError("El CSV cambió durante la preparación")
        os.replace(temporary_database, DATABASE_PATH)
    manifest = {
        "dataset": "Salida completa y limpia de EA2 para el enriquecimiento",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": ea2_commit,
            "repository_path": SOURCE_REPOSITORY_PATH,
            "sha256": actual_hash,
        },
        "csv": {
            "path": CSV_PATH.relative_to(ROOT).as_posix(),
            "bytes": CSV_PATH.stat().st_size,
            "sha256": actual_hash,
            "rows": len(frame),
            "columns": COLUMN_ORDER,
        },
        "database": {
            "path": DATABASE_PATH.relative_to(ROOT).as_posix(),
            "engine": "DuckDB",
            "table": "cleaned_data",
            "bytes": DATABASE_PATH.stat().st_size,
            "sha256": sha256(DATABASE_PATH),
            "schema": schema,
        },
        "semantics": {
            "grain": "Una ciudad y una hora local de 2025",
            "key": ["city", "observation_time"],
            "timezone": "America/Bogota",
            "timestamp_storage": "TIMESTAMPTZ conserva el instante; timezone conserva la zona local",
            "city_id": "Clave dimensional local de EA1, no código DANE o DIVIPOLA",
            "weather": "Open-Meteo Historical Weather API; la extracción EA1 no fijó models",
            "energy_kwh": "Variable sintética de EA1 con semilla 42; no consumo eléctrico medido",
            "empty_text_fields": ["imputed_fields", "outlier_fields"],
        },
        "validation": {
            "csv_sha256_matches_ea2": True,
            "csv_unchanged": True,
            "rows": len(frame),
            "columns": len(frame.columns),
            "duplicate_city_hour": 0,
            "csv_database_values_equal": True,
            "comparison": "Todos los valores: números y booleanos exactos; fechas por instante UTC; textos incluyendo vacíos",
        },
        "build": {"duckdb": duckdb.__version__, "pandas": pd.__version__, "numpy": np.__version__},
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-sha256", help="Huella del CSV original; se reutiliza el manifiesto si existe"
    )
    parser.add_argument(
        "--ea2-commit",
        help="Commit que contiene el CSV de origen; se reutiliza el manifiesto si existe",
    )
    args = parser.parse_args()
    manifest = prepare_base(args.expected_sha256, args.ea2_commit)
    print(
        json.dumps(
            {
                "status": "PASS",
                **manifest["validation"],
                "database_sha256": manifest["database"]["sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
