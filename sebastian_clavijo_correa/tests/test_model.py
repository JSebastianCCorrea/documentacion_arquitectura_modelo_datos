"""Verifica riesgos de granularidad y restricciones de la base de análisis."""

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import model


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = model.read_enriched(ROOT / "src/data/reference/enriched_full.csv")
        cls.tables = model.split_tables(cls.frame)
        cls.sql = model.schema_for(cls.tables, list(cls.frame.columns))

    def test_daily_solar_is_not_multiplied_by_hours(self):
        solar = self.tables["fact_solar_day"]
        self.assertEqual(len(solar), 1825)
        hourly_sum = self.frame["shortwave_radiation_sum_mj_m2"].sum()
        self.assertAlmostEqual(hourly_sum, 24 * solar["shortwave_radiation_sum_mj_m2"].sum(), places=6)

    def test_inconsistent_daily_value_is_rejected(self):
        changed = self.frame.copy()
        changed.loc[0, "daylight_seconds"] += 1
        with self.assertRaisesRegex(ValueError, "fact_solar_day"):
            model.split_tables(changed)

    def test_municipality_codes_remain_text(self):
        cities = self.tables["dim_city"].set_index("city")
        self.assertEqual(cities.loc["Medellin", "municipality_code"], "05001")
        self.assertEqual(cities.loc["Barranquilla", "department_code"], "08")

    def test_foreign_key_prevents_unknown_date(self):
        with sqlite3.connect(":memory:") as con:
            con.executescript(self.sql)
            row = self.tables["dim_time"].iloc[0].tolist()
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("INSERT INTO dim_time VALUES (?,?,?,?,?,?)", row)

    def test_boolean_check_and_duplicate_hour(self):
        with sqlite3.connect(":memory:") as con:
            con.executescript(self.sql)
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("INSERT INTO dim_hour VALUES (0,'madrugada',2)")
            con.execute("INSERT INTO dim_hour VALUES (0,'madrugada',1)")
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("INSERT INTO dim_hour VALUES (0,'madrugada',1)")

    def test_complete_sqlite_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = model.run(ROOT / "src/data/reference/enriched_full.csv", root / "db.sqlite",
                               root / "schema.sql", root / "audit.json")
            self.assertTrue(result["roundtrip_exact"])
            self.assertEqual(result["view_rows"], 43800)
            self.assertEqual(result["view_columns"], 63)
            self.assertEqual(result["foreign_key_violations"], 0)
            raw = pd.read_csv(ROOT / "src/data/reference/enriched_full.csv", dtype=str, keep_default_na=False)
            with closing(sqlite3.connect(root / "db.sqlite")) as con:
                recovered = pd.read_sql_query("SELECT * FROM enriched_data ORDER BY source_row", con)
            for field in raw:
                if model.sql_type(field) == "REAL":
                    self.assertEqual(raw[field].map(float).tolist(), recovered[field].tolist(), field)


if __name__ == "__main__":
    unittest.main()
