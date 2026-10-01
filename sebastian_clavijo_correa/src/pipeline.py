"""Ejecuta las tres fases y construye el modelo documentado."""

from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil
import sys

import duckdb
import pandas as pd

import cleaning
import enrichment
import ingestion
import model

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_base


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path):
    # Las salidas de CI viven en un directorio nuevo: nunca se aprueba una copia antigua.
    output.mkdir(parents=True, exist_ok=True)
    audit = output / "static/auditoria"
    audit.mkdir(parents=True, exist_ok=True)
    original = ROOT / "src/db/ingestion.db"
    original_hash = digest(original)
    replayed = output / "db/replayed.duckdb"
    replay = ingestion.run(ROOT / "src/data/raw", replayed)
    raw, _ = cleaning.extract_database(replayed)
    expected, _ = cleaning.extract_database(original)
    pd.testing.assert_frame_equal(raw, expected, check_dtype=False, check_exact=True)
    replay["equals_ea1_snapshot"] = True
    (audit / "ingestion_report.json").write_text(json.dumps(replay, indent=2), encoding="utf-8")
    (audit / "ingestion_report.txt").write_text(
        f"INGESTA REPRODUCIDA\nRespuestas archivadas de API: 5. Solicitudes HTTP nuevas: 0.\n"
        f"Filas JSON: {replay['raw_rows']}. Filas conservadas: {replay['retained_rows']}.\n"
        "Energía sintética con semilla 42. Comparación exacta con la extracción de EA1: PASS.\n",
        encoding="utf-8")
    clean_result = cleaning.run_pipeline(replayed, output / "cleaning")
    fresh_csv = output / "cleaning/xlsx/cleaned_full.csv"
    reference_csv = ROOT / "src/data/base/cleaned_full.csv"
    if digest(fresh_csv) != digest(reference_csv):
        raise ValueError("La salida limpia ya no reproduce byte a byte el CSV de EA2")
    cleaned_db = output / "db/cleaned.duckdb"
    frame = prepare_base.read_base(fresh_csv)
    # Se preservan los tipos y la precisión que ya empleaba la etapa de enriquecimiento.
    with duckdb.connect(str(cleaned_db)) as con:
        con.register("input_cleaned", frame)
        con.execute("CREATE OR REPLACE TABLE cleaned_data AS SELECT * FROM input_cleaned")
    enriched_result = enrichment.run(cleaned_db, ROOT / "src/sources", output)
    reference_enriched = ROOT / "src/data/reference/enriched_full.csv"
    if digest(output / "data/enriched_full.csv") != digest(reference_enriched):
        raise ValueError("El enriquecimiento difiere del CSV aprobado en la entrega anterior")
    model_result = model.run(output / "data/enriched_full.csv", output / "db/analytics.sqlite",
                             output / "sql/schema.sql", audit / "model_validation.json")
    if digest(original) != original_hash:
        raise ValueError("Se modificó la instantánea de EA1")
    summary = {"status": "PASS", "execution_utc": datetime.now(timezone.utc).isoformat(),
               "ingestion_equals_ea1": True, "cleaning_equals_ea2_bytes": True,
               "enrichment_equals_previous_bytes": True, "ea1_sha256": original_hash,
               "cleaned_csv_sha256": digest(fresh_csv), "enriched_csv_sha256": digest(output / "data/enriched_full.csv"),
               "rows": enriched_result["rows_after"], "columns": enriched_result["columns_after"],
               "sqlite_roundtrip_exact": model_result["roundtrip_exact"],
               "sqlite_sha256": digest(output / "db/analytics.sqlite")}
    (audit / "pipeline_validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (audit / "pipeline_report.txt").write_text(
        "INTEGRACIÓN COMPLETA\n" + "\n".join(f"{key}: {value}" for key, value in summary.items()) + "\n",
        encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output_dir), indent=2))
        return 0
    except Exception as error:
        print(f"La integración se detuvo: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
