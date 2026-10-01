PRAGMA foreign_keys = ON;

CREATE TABLE dim_city (
  "city_id" INTEGER NOT NULL,
  "city" TEXT NOT NULL,
  "latitude" REAL NOT NULL,
  "longitude" REAL NOT NULL,
  "country_code" TEXT NOT NULL,
  "geoname_id" INTEGER NOT NULL,
  "elevation_m" REAL NOT NULL,
  "matched_geography" INTEGER NOT NULL CHECK ("matched_geography" IN (0,1)),
  "municipality_code" TEXT NOT NULL,
  "municipality_name" TEXT NOT NULL,
  "department_code" TEXT NOT NULL,
  "department_name" TEXT NOT NULL,
  "divipola_year" INTEGER NOT NULL,
  "matched_municipalities" INTEGER NOT NULL CHECK ("matched_municipalities" IN (0,1)),
  "reference_temperature_c" REAL NOT NULL,
  "parameter_scope" TEXT NOT NULL,
  "matched_thermal" INTEGER NOT NULL CHECK ("matched_thermal" IN (0,1)),
  PRIMARY KEY (city_id),
  UNIQUE (city),
  UNIQUE (municipality_code),
  CHECK (length(municipality_code)=5 AND municipality_code NOT GLOB '*[^0-9]*'),
  CHECK (length(department_code)=2 AND department_code NOT GLOB '*[^0-9]*')
) STRICT;

CREATE TABLE dim_date (
  "local_date" TEXT NOT NULL,
  "year" INTEGER NOT NULL,
  "month" INTEGER NOT NULL,
  "day" INTEGER NOT NULL,
  "holiday_name" TEXT NOT NULL,
  "is_holiday" INTEGER NOT NULL CHECK ("is_holiday" IN (0,1)),
  "is_weekend" INTEGER NOT NULL CHECK ("is_weekend" IN (0,1)),
  "matched_calendar" INTEGER NOT NULL CHECK ("matched_calendar" IN (0,1)),
  "is_business_day" INTEGER NOT NULL CHECK ("is_business_day" IN (0,1)),
  PRIMARY KEY (local_date),
  CHECK (month BETWEEN 1 AND 12),
  CHECK (day BETWEEN 1 AND 31)
) STRICT;

CREATE TABLE dim_hour (
  "hour" INTEGER NOT NULL,
  "day_period" TEXT NOT NULL,
  "matched_hours" INTEGER NOT NULL CHECK ("matched_hours" IN (0,1)),
  PRIMARY KEY (hour),
  CHECK (hour BETWEEN 0 AND 23)
) STRICT;

CREATE TABLE dim_time (
  "time_id" INTEGER NOT NULL,
  "observation_time" TEXT NOT NULL,
  "observation_time_utc" TEXT NOT NULL,
  "local_date" TEXT NOT NULL,
  "hour" INTEGER NOT NULL,
  "timezone" TEXT NOT NULL,
  PRIMARY KEY (time_id),
  UNIQUE (observation_time),
  UNIQUE (observation_time_utc),
  UNIQUE (local_date, hour),
  FOREIGN KEY (local_date) REFERENCES dim_date(local_date),
  FOREIGN KEY (hour) REFERENCES dim_hour(hour)
) STRICT;

CREATE TABLE fact_solar_day (
  "city_id" INTEGER NOT NULL,
  "local_date" TEXT NOT NULL,
  "shortwave_radiation_sum_mj_m2" REAL NOT NULL,
  "daylight_seconds" REAL NOT NULL,
  "sunshine_seconds" REAL NOT NULL,
  "matched_solar" INTEGER NOT NULL CHECK ("matched_solar" IN (0,1)),
  "radiation_kwh_m2_day" REAL NOT NULL,
  "daylight_hours" REAL NOT NULL,
  "sunshine_hours" REAL NOT NULL,
  PRIMARY KEY (city_id, local_date),
  FOREIGN KEY (city_id) REFERENCES dim_city(city_id),
  FOREIGN KEY (local_date) REFERENCES dim_date(local_date),
  CHECK (shortwave_radiation_sum_mj_m2 >= 0),
  CHECK (sunshine_seconds BETWEEN 0 AND daylight_seconds),
  CHECK (daylight_seconds BETWEEN 0 AND 86400)
) STRICT;

CREATE TABLE fact_hourly (
  "source_row" INTEGER NOT NULL,
  "city_id" INTEGER NOT NULL,
  "time_id" INTEGER NOT NULL,
  "temperature_c" REAL NOT NULL,
  "humidity_pct" REAL NOT NULL,
  "precipitation_mm" REAL NOT NULL,
  "wind_speed_kmh" REAL NOT NULL,
  "energy_kwh" REAL NOT NULL,
  "synthetic_energy" INTEGER NOT NULL CHECK ("synthetic_energy" IN (0,1)),
  "imputed_fields" TEXT NOT NULL,
  "quality_status" TEXT NOT NULL,
  "is_outlier" INTEGER NOT NULL CHECK ("is_outlier" IN (0,1)),
  "outlier_fields" TEXT NOT NULL,
  "outlier_temperature_c" INTEGER NOT NULL CHECK ("outlier_temperature_c" IN (0,1)),
  "outlier_humidity_pct" INTEGER NOT NULL CHECK ("outlier_humidity_pct" IN (0,1)),
  "outlier_precipitation_mm" INTEGER NOT NULL CHECK ("outlier_precipitation_mm" IN (0,1)),
  "outlier_wind_speed_kmh" INTEGER NOT NULL CHECK ("outlier_wind_speed_kmh" IN (0,1)),
  "outlier_energy_kwh" INTEGER NOT NULL CHECK ("outlier_energy_kwh" IN (0,1)),
  "temperature_zscore" REAL NOT NULL,
  "energy_zscore" REAL NOT NULL,
  "humidity_fraction" REAL NOT NULL,
  "precipitation_log1p" REAL NOT NULL,
  "degrees_above_reference_c" REAL NOT NULL,
  "degrees_below_reference_c" REAL NOT NULL,
  "enrichment_status" TEXT NOT NULL,
  PRIMARY KEY (source_row),
  UNIQUE (city_id, time_id),
  FOREIGN KEY (city_id) REFERENCES dim_city(city_id),
  FOREIGN KEY (time_id) REFERENCES dim_time(time_id),
  CHECK (humidity_pct BETWEEN 0 AND 100),
  CHECK (energy_kwh >= 0),
  CHECK (precipitation_mm >= 0),
  CHECK (wind_speed_kmh >= 0)
) STRICT;

CREATE INDEX idx_hourly_time ON fact_hourly(time_id);

CREATE INDEX idx_solar_date ON fact_solar_day(local_date);

CREATE VIEW enriched_data AS SELECT
  c."city_id" AS "city_id",
  t."time_id" AS "time_id",
  t."observation_time" AS "observation_time",
  c."city" AS "city",
  c."latitude" AS "latitude",
  c."longitude" AS "longitude",
  f."temperature_c" AS "temperature_c",
  f."humidity_pct" AS "humidity_pct",
  f."precipitation_mm" AS "precipitation_mm",
  f."wind_speed_kmh" AS "wind_speed_kmh",
  f."energy_kwh" AS "energy_kwh",
  f."synthetic_energy" AS "synthetic_energy",
  f."source_row" AS "source_row",
  d."year" AS "year",
  d."month" AS "month",
  d."day" AS "day",
  h."hour" AS "hour",
  f."imputed_fields" AS "imputed_fields",
  f."quality_status" AS "quality_status",
  f."is_outlier" AS "is_outlier",
  f."outlier_fields" AS "outlier_fields",
  f."outlier_temperature_c" AS "outlier_temperature_c",
  f."outlier_humidity_pct" AS "outlier_humidity_pct",
  f."outlier_precipitation_mm" AS "outlier_precipitation_mm",
  f."outlier_wind_speed_kmh" AS "outlier_wind_speed_kmh",
  f."outlier_energy_kwh" AS "outlier_energy_kwh",
  f."temperature_zscore" AS "temperature_zscore",
  f."energy_zscore" AS "energy_zscore",
  f."humidity_fraction" AS "humidity_fraction",
  f."precipitation_log1p" AS "precipitation_log1p",
  t."timezone" AS "timezone",
  t."observation_time_utc" AS "observation_time_utc",
  d."local_date" AS "local_date",
  c."country_code" AS "country_code",
  c."geoname_id" AS "geoname_id",
  c."elevation_m" AS "elevation_m",
  c."matched_geography" AS "matched_geography",
  d."holiday_name" AS "holiday_name",
  d."is_holiday" AS "is_holiday",
  d."is_weekend" AS "is_weekend",
  d."matched_calendar" AS "matched_calendar",
  s."shortwave_radiation_sum_mj_m2" AS "shortwave_radiation_sum_mj_m2",
  s."daylight_seconds" AS "daylight_seconds",
  s."sunshine_seconds" AS "sunshine_seconds",
  s."matched_solar" AS "matched_solar",
  c."municipality_code" AS "municipality_code",
  c."municipality_name" AS "municipality_name",
  c."department_code" AS "department_code",
  c."department_name" AS "department_name",
  c."divipola_year" AS "divipola_year",
  c."matched_municipalities" AS "matched_municipalities",
  c."reference_temperature_c" AS "reference_temperature_c",
  c."parameter_scope" AS "parameter_scope",
  c."matched_thermal" AS "matched_thermal",
  h."day_period" AS "day_period",
  h."matched_hours" AS "matched_hours",
  s."radiation_kwh_m2_day" AS "radiation_kwh_m2_day",
  s."daylight_hours" AS "daylight_hours",
  s."sunshine_hours" AS "sunshine_hours",
  f."degrees_above_reference_c" AS "degrees_above_reference_c",
  f."degrees_below_reference_c" AS "degrees_below_reference_c",
  d."is_business_day" AS "is_business_day",
  f."enrichment_status" AS "enrichment_status"
FROM fact_hourly f
JOIN dim_city c ON c.city_id=f.city_id
JOIN dim_time t ON t.time_id=f.time_id
JOIN dim_date d ON d.local_date=t.local_date
JOIN dim_hour h ON h.hour=t.hour
JOIN fact_solar_day s ON s.city_id=f.city_id AND s.local_date=t.local_date;
