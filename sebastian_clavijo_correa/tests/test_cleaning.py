"""Casos pequeños para revisar las decisiones de limpieza y muestreo.

Los registros se crean en memoria; estas pruebas no abren ni modifican la base de EA1.
"""

import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from src.cleaning import clean_frame, representative_sample

CITY_DATA = {
    "Bogota": (2, 4.7110, -74.0721),
    "Medellin": (5, 6.2442, -75.5812),
    "Cali": (4, 3.4516, -76.5320),
}


def record(hour=0, city="Bogota", month=1, **changes):
    """Crea una hora válida y permite cambiar los campos necesarios para cada caso."""
    city_id, latitude, longitude = CITY_DATA[city]
    stamp = pd.Timestamp(year=2025, month=month, day=1) + pd.Timedelta(hours=hour)
    row = {
        "city_id": city_id,
        "time_id": int((stamp - pd.Timestamp("2025-01-01")).total_seconds() // 3600) + 1,
        "observation_time": stamp.strftime("%Y-%m-%d %H:%M:%S"),
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "temperature_c": 20.0,
        "humidity_pct": 80,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 5.0,
        "energy_kwh": 120.0,
        "synthetic_energy": True,
    }
    row.update(changes)
    return row


class CleaningTests(unittest.TestCase):
    def assert_reconciliation(self, raw, cleaned, rejected, metrics):
        """Cada fila de entrada debe quedar limpia, rechazada o contada como duplicado."""
        removed = metrics["operations"]["exact_duplicates_removed"]
        self.assertEqual(len(raw), len(cleaned) + len(rejected) + removed)
        self.assertEqual(metrics["before"]["rows"], len(raw))
        self.assertEqual(metrics["after"]["rows"], len(cleaned))
        self.assertEqual(metrics["operations"]["rows_rejected"], len(rejected))
        if len(rejected):
            self.assertIn("source_row", rejected.columns)
            self.assertIn("rejection_reason", rejected.columns)
            self.assertTrue(rejected["rejection_reason"].astype(str).str.len().gt(0).all())

    def test_canonical_types_local_hour_and_input_preservation(self):
        """Normalizar nombres y tipos debe conservar la hora local y el DataFrame recibido."""
        row = record(7)
        row.update(
            city="  Bogotá  ",
            latitude="4.7110",
            longitude="-74.0721",
            temperature_c="20.5",
            humidity_pct="80",
            precipitation_mm="1.2",
            wind_speed_kmh="5.5",
            energy_kwh="120.50",
            synthetic_energy="true",
            city_id="2",
            time_id="8",
        )
        raw = pd.DataFrame([row, record(8)])
        before = raw.copy(deep=True)
        cleaned, rejected, metrics = clean_frame(raw)
        assert_frame_equal(raw, before)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(set(cleaned["city"]), {"Bogota"})
        first = cleaned.loc[cleaned["hour"].eq(7)].iloc[0]
        self.assertEqual(first["temperature_c"], 20.5)
        self.assertEqual(first["energy_kwh"], 120.5)
        self.assertEqual(first["year"], 2025)
        self.assertEqual(first["month"], 1)
        self.assertAlmostEqual(first["humidity_fraction"], 0.8)
        self.assertAlmostEqual(first["precipitation_log1p"], np.log1p(1.2))
        self.assertTrue(bool(first["synthetic_energy"]))
        for col in [
            "latitude",
            "longitude",
            "temperature_c",
            "humidity_pct",
            "precipitation_mm",
            "wind_speed_kmh",
            "energy_kwh",
        ]:
            self.assertTrue(pd.api.types.is_numeric_dtype(cleaned[col]), col)
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_exact_duplicates_removed_after_canonicalization(self):
        """Un cambio de espacios o de formato numérico no crea una observación distinta."""
        one = record(0)
        duplicate = dict(one, city=" Bogotá ", temperature_c="20.0", synthetic_energy="true")
        raw = pd.DataFrame([one, duplicate, record(1)])
        cleaned, rejected, metrics = clean_frame(raw)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(metrics["operations"]["exact_duplicates_removed"], 1)
        self.assertFalse(cleaned.duplicated(["city", "observation_time"]).any())
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_conflicting_natural_key_rejects_every_variant(self):
        """Ante dos valores distintos para la misma ciudad y hora, no se elige uno al azar."""
        raw = pd.DataFrame([record(0, energy_kwh=110), record(0, energy_kwh=170), record(1)])
        cleaned, rejected, metrics = clean_frame(raw)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(rejected), 2)
        self.assertEqual(int(cleaned.iloc[0]["hour"]), 1)
        self.assertEqual(metrics["operations"]["exact_duplicates_removed"], 0)
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_distinct_invalid_values_do_not_become_false_duplicates(self):
        """Dos valores inválidos distintos siguen siendo un conflicto después de convertirlos."""
        for field, first, second in [("humidity_pct", 150, 200), ("temperature_c", "foo", "bar")]:
            with self.subTest(field=field, first=first, second=second):
                raw = pd.DataFrame(
                    [record(0, **{field: first}), record(0, **{field: second}), record(1)]
                )
                original = raw.copy(deep=True)
                cleaned, rejected, metrics = clean_frame(raw)
                self.assertEqual(len(cleaned), 1)
                self.assertEqual(len(rejected), 2)
                self.assertEqual(int(cleaned.iloc[0]["hour"]), 1)
                self.assertEqual(metrics["operations"]["exact_duplicates_removed"], 0)
                self.assertEqual(metrics["operations"]["conflicting_key_rows"], 2)
                self.assertEqual(set(rejected[field].tolist()), {first, second})
                self.assert_reconciliation(raw, cleaned, rejected, metrics)
                assert_frame_equal(raw, original)

    def test_invalid_required_identifiers_and_metadata_are_rejected(self):
        """Una fila sin identidad, fecha o procedencia válida debe quedar en rechazos."""
        invalid_cases = [
            ("observation_time", "not-a-date"),
            ("city", None),
            ("city", "Ciudad desconocida"),
            ("latitude", 200),
            ("longitude", -200),
            ("city_id", None),
            ("time_id", "not-an-id"),
            ("synthetic_energy", None),
            ("synthetic_energy", "quizas"),
        ]
        for field, value in invalid_cases:
            with self.subTest(field=field, value=value):
                invalid_row = record(1)
                invalid_row[field] = value
                raw = pd.DataFrame([record(0), invalid_row])
                cleaned, rejected, metrics = clean_frame(raw)
                self.assertEqual(len(cleaned), 1)
                self.assertEqual(len(rejected), 1)
                self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_medians_are_calculated_within_city_and_month(self):
        """La mediana no debe mezclar observaciones de otra ciudad o de otro mes."""
        raw = pd.DataFrame(
            [
                record(0, temperature_c=10, humidity_pct=60, wind_speed_kmh=2, energy_kwh=100),
                record(1, temperature_c=30, humidity_pct=100, wind_speed_kmh=8, energy_kwh=200),
                record(
                    2, temperature_c=None, humidity_pct=None, wind_speed_kmh=None, energy_kwh=None
                ),
                record(0, city="Medellin", temperature_c=35, energy_kwh=900),
                record(0, month=2, temperature_c=40, energy_kwh=800),
            ]
        )
        cleaned, rejected, metrics = clean_frame(raw)
        self.assertEqual(len(rejected), 0)
        filled = cleaned.loc[
            (cleaned["city"] == "Bogota") & (cleaned["month"] == 1) & (cleaned["hour"] == 2)
        ].iloc[0]
        for field, value in {
            "temperature_c": 20,
            "humidity_pct": 80,
            "wind_speed_kmh": 5,
            "energy_kwh": 150,
        }.items():
            self.assertAlmostEqual(filled[field], value)
            self.assertIn(field, str(filled["imputed_fields"]).split("|"))
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_invalid_or_nonfinite_metrics_use_the_same_imputation_rules(self):
        """Los valores fuera de dominio usan la misma regla que un dato faltante."""
        cases = [
            ("temperature_c", "invalid", 10, 30, 20),
            ("temperature_c", np.inf, 10, 30, 20),
            ("humidity_pct", 150, 60, 100, 80),
            ("wind_speed_kmh", -2, 2, 8, 5),
            ("energy_kwh", -5, 100, 200, 150),
        ]
        for field, invalid, a, b, expected in cases:
            with self.subTest(field=field, invalid=invalid):
                raw = pd.DataFrame(
                    [
                        record(0, **{field: a}),
                        record(1, **{field: b}),
                        record(2, **{field: invalid}),
                    ]
                )
                cleaned, rejected, metrics = clean_frame(raw)
                self.assertEqual(len(rejected), 0)
                filled = cleaned.loc[cleaned["hour"].eq(2)].iloc[0]
                self.assertAlmostEqual(filled[field], expected)
                self.assertIn(field, str(filled["imputed_fields"]).split("|"))
                self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_missing_donor_does_not_fall_back_to_other_city_or_month(self):
        """Sin valores válidos en su grupo, se rechaza la fila en vez de tomar otra mediana."""
        raw = pd.DataFrame(
            [
                record(0, temperature_c=None),
                record(0, month=2, temperature_c=30),
                record(0, city="Medellin", temperature_c=25),
            ]
        )
        cleaned, rejected, metrics = clean_frame(raw)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(rejected), 1)
        self.assertFalse(((cleaned["city"] == "Bogota") & (cleaned["month"] == 1)).any())
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_precipitation_unknown_is_not_replaced_with_zero_or_median(self):
        """Una precipitación desconocida no permite afirmar que no llovió."""
        for value in [None, "bad", -1, np.inf]:
            with self.subTest(value=value):
                raw = pd.DataFrame(
                    [
                        record(0, precipitation_mm=0),
                        record(1, precipitation_mm=2),
                        record(2, precipitation_mm=value),
                    ]
                )
                cleaned, rejected, metrics = clean_frame(raw)
                self.assertEqual(len(cleaned), 2)
                self.assertEqual(len(rejected), 1)
                self.assertEqual(sorted(cleaned["precipitation_mm"].tolist()), [0, 2])
                self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_physically_valid_iqr_outlier_is_kept_and_flagged(self):
        """Una temperatura poco habitual se señala sin borrar un valor físicamente válido."""
        temperatures = [18, 19, 20, 21, 22, 23, 24, 25, 26, 45]
        raw = pd.DataFrame([record(i, temperature_c=t) for i, t in enumerate(temperatures)])
        cleaned, rejected, metrics = clean_frame(raw)
        self.assertEqual(len(cleaned), len(raw))
        self.assertEqual(len(rejected), 0)
        hot = cleaned.loc[cleaned["hour"].eq(9)].iloc[0]
        self.assertEqual(hot["temperature_c"], 45)
        self.assertTrue(bool(hot["is_outlier"]))
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_constant_series_does_not_produce_nonfinite_scaled_values(self):
        """Un grupo constante no debe producir infinitos al escalar sus valores."""
        raw = pd.DataFrame([record(i) for i in range(5)])
        cleaned, rejected, metrics = clean_frame(raw)
        self.assertEqual(len(rejected), 0)
        for col in [
            "temperature_zscore",
            "energy_zscore",
            "humidity_fraction",
            "precipitation_log1p",
        ]:
            self.assertTrue(np.isfinite(cleaned[col].astype(float)).all(), col)
        self.assertFalse(cleaned["is_outlier"].any())
        self.assert_reconciliation(raw, cleaned, rejected, metrics)

    def test_cleaning_repeated_on_same_input_is_deterministic(self):
        """Repetir la limpieza sobre la misma entrada debe producir el mismo resultado."""
        raw = pd.DataFrame([record(i, temperature_c=18 + i) for i in range(6)])
        before = raw.copy(deep=True)
        cleaned_a, rejected_a, _ = clean_frame(raw)
        cleaned_b, rejected_b, _ = clean_frame(raw)
        assert_frame_equal(cleaned_a, cleaned_b)
        assert_frame_equal(rejected_a, rejected_b)
        assert_frame_equal(raw, before)


class RepresentativeSampleTests(unittest.TestCase):
    def test_stratification_small_groups_determinism_and_no_input_mutation(self):
        """La muestra respeta cada grupo y se puede repetir con la misma semilla."""
        rows = [
            record(hour, city=city, month=month)
            for city in ["Bogota", "Medellin"]
            for month in [1, 2]
            for hour in range(30)
        ]
        rows += [record(hour, city="Cali", month=1) for hour in range(7)]
        cleaned, rejected, _ = clean_frame(pd.DataFrame(rows))
        self.assertEqual(len(rejected), 0)
        before = cleaned.copy(deep=True)
        sample = representative_sample(cleaned, per_group=20, seed=42)
        repeated = representative_sample(cleaned, per_group=20, seed=42)
        assert_frame_equal(sample, repeated)
        assert_frame_equal(cleaned, before)
        counts = sample.groupby(["city", "year", "month"]).size().to_dict()
        self.assertEqual(
            counts,
            {
                ("Bogota", 2025, 1): 20,
                ("Bogota", 2025, 2): 20,
                ("Medellin", 2025, 1): 20,
                ("Medellin", 2025, 2): 20,
                ("Cali", 2025, 1): 7,
            },
        )
        keys = ["city", "observation_time"]
        self.assertFalse(sample.duplicated(keys).any())
        self.assertTrue(
            set(map(tuple, sample[keys].to_numpy())).issubset(
                set(map(tuple, cleaned[keys].to_numpy()))
            )
        )
        assert_frame_equal(
            sample.reset_index(drop=True), sample.sort_values(keys).reset_index(drop=True)
        )
        other_seed = representative_sample(cleaned, per_group=20, seed=43)
        self.assertFalse(
            sample[keys].reset_index(drop=True).equals(other_seed[keys].reset_index(drop=True))
        )


if __name__ == "__main__":
    unittest.main()
