from pathlib import Path
import json

import duckdb
import numpy as np
import pandas as pd
import requests

# 1. CONFIGURACIÓN GENERAL

ROOT = Path(__file__).resolve().parent

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DATABASE_DIR = ROOT / "database"
OUTPUT_DIR = ROOT / "outputs"

for folder in [
    RAW_DIR,
    PROCESSED_DIR,
    DATABASE_DIR,
    OUTPUT_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)


API_URL = "https://archive-api.open-meteo.com/v1/archive"

# Un año es suficiente para la evidencia
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


CITIES = [
    {
        "city": "Medellin",
        "latitude": 6.2442,
        "longitude": -75.5812,
    },
    {
        "city": "Bogota",
        "latitude": 4.7110,
        "longitude": -74.0721,
    },
    {
        "city": "Cali",
        "latitude": 3.4516,
        "longitude": -76.5320,
    },
    {
        "city": "Barranquilla",
        "latitude": 10.9685,
        "longitude": -74.7813,
    },
    {
        "city": "Bucaramanga",
        "latitude": 7.1193,
        "longitude": -73.1227,
    },
]


print("=" * 70)
print("EVIDENCIA 1 - BASE DE DATOS ANALITICA")
print("=" * 70)

# 2. EXTRACCIÓN DESDE API


print("\n[1/7] Extrayendo datos meteorológicos desde Open-Meteo...")

dataframes = []

for city in CITIES:

    print(f"   -> {city['city']}")

    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "wind_speed_10m"
        ),
        "timezone": "America/Bogota",
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=120,
    )

    response.raise_for_status()

    payload = response.json()

    # Guardamos respuesta original
    raw_file = (
        RAW_DIR /
        f"{city['city'].lower()}_weather.json"
    )

    with open(
        raw_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )

    df_city = pd.DataFrame(
        payload["hourly"]
    )

    df_city["city"] = city["city"]
    df_city["latitude"] = city["latitude"]
    df_city["longitude"] = city["longitude"]

    dataframes.append(df_city)


weather = pd.concat(
    dataframes,
    ignore_index=True,
)

weather["time"] = pd.to_datetime(
    weather["time"]
)

# 3. CONTROL DE CALIDAD

print("\n[2/7] Ejecutando controles de calidad...")

weather = weather.drop_duplicates()

weather = weather.dropna(
    subset=[
        "time",
        "city",
        "temperature_2m",
    ]
)

print(
    f"   Registros meteorológicos: "
    f"{len(weather):,}"
)

print(
    f"   Ciudades: "
    f"{weather['city'].nunique()}"
)

print(
    f"   Periodo: "
    f"{weather['time'].min()} "
    f"hasta "
    f"{weather['time'].max()}"
)

# 4. GENERACIÓN DE DATOS SINTÉTICOS


print("\n[3/7] Generando consumo energético sintético...")

rng = np.random.default_rng(seed=42)

BASE_CONSUMPTION = {
    "Medellin": 110,
    "Bogota": 130,
    "Cali": 115,
    "Barranquilla": 125,
    "Bucaramanga": 100,
}

weather["hour"] = weather["time"].dt.hour

weather["base_energy"] = (
    weather["city"]
    .map(BASE_CONSUMPTION)
)


# Factor horario
weather["hour_factor"] = np.select(
    [
        weather["hour"].between(18, 21),
        weather["hour"].between(7, 9),
    ],
    [
        1.25,
        1.15,
    ],
    default=1.0,
)


# Efecto de temperatura
weather["temperature_factor"] = (
    1
    +
    np.abs(
        weather["temperature_2m"] - 22
    ) * 0.015
)


# Efecto de lluvia
weather["rain_factor"] = (
    1
    +
    weather["precipitation"]
    .fillna(0)
    * 0.005
)


# Ruido pseudoaleatorio reproducible
weather["random_factor"] = rng.normal(
    loc=1.0,
    scale=0.05,
    size=len(weather),
)


weather["energy_kwh"] = (
    weather["base_energy"]
    * weather["hour_factor"]
    * weather["temperature_factor"]
    * weather["rain_factor"]
    * weather["random_factor"]
).round(2)


weather["synthetic_energy"] = True


# Quitamos columnas auxiliares
weather = weather.drop(
    columns=[
        "base_energy",
        "hour_factor",
        "temperature_factor",
        "rain_factor",
        "random_factor",
    ]
)

# 5. GUARDAR DATASET PROCESADO

processed_file = (
    PROCESSED_DIR /
    "weather_energy_colombia.csv"
)

weather.to_csv(
    processed_file,
    index=False,
)

print(
    f"   Dataset procesado: "
    f"{processed_file}"
)

# 6. CREAR BASE DUCKDB

print("\n[4/7] Creando base de datos DuckDB...")

db_file = (
    DATABASE_DIR /
    "analytics.duckdb"
)

con = duckdb.connect(
    str(db_file)
)

# STAGING

con.execute("""
CREATE OR REPLACE TABLE staging_weather AS

SELECT
    CAST(time AS TIMESTAMP) AS observation_time,
    city,
    latitude,
    longitude,
    temperature_2m,
    relative_humidity_2m,
    precipitation,
    wind_speed_10m,
    energy_kwh,
    synthetic_energy

FROM read_csv_auto(?);
""", [str(processed_file)])

# DIMENSIÓN CIUDAD

con.execute("""
CREATE OR REPLACE TABLE dim_city AS

SELECT
    ROW_NUMBER()
        OVER (ORDER BY city)
        AS city_id,

    city,
    latitude,
    longitude

FROM (
    SELECT DISTINCT
        city,
        latitude,
        longitude
    FROM staging_weather
);
""")

# DIMENSIÓN TIEMPO

con.execute("""
CREATE OR REPLACE TABLE dim_time AS

SELECT
    ROW_NUMBER()
        OVER (ORDER BY observation_time)
        AS time_id,

    observation_time,

    CAST(observation_time AS DATE)
        AS observation_date,

    YEAR(observation_time)
        AS year,

    MONTH(observation_time)
        AS month,

    DAY(observation_time)
        AS day,

    HOUR(observation_time)
        AS hour,

    DAYOFWEEK(observation_time)
        AS weekday

FROM (
    SELECT DISTINCT
        observation_time
    FROM staging_weather
);
""")

# TABLA DE HECHOS

con.execute("""
CREATE OR REPLACE TABLE fact_weather_energy AS

SELECT
    c.city_id,
    t.time_id,

    s.temperature_2m
        AS temperature_c,

    s.relative_humidity_2m
        AS humidity_pct,

    s.precipitation
        AS precipitation_mm,

    s.wind_speed_10m
        AS wind_speed_kmh,

    s.energy_kwh,

    s.synthetic_energy

FROM staging_weather s

JOIN dim_city c
    ON s.city = c.city

JOIN dim_time t
    ON s.observation_time =
       t.observation_time;
""")


count_fact = con.execute("""
SELECT COUNT(*)
FROM fact_weather_energy
""").fetchone()[0]

print(
    f"   Registros tabla de hechos: "
    f"{count_fact:,}"
)

print(
    f"   Base creada: {db_file}"
)

# 7. CONSULTAS ANALÍTICAS


print("\n[5/7] Ejecutando consultas analíticas...")



# CONSULTA 1
# Consumo y temperatura por ciudad


q1 = con.execute("""
SELECT
    c.city,

    ROUND(
        AVG(f.temperature_c),
        2
    ) AS avg_temperature_c,

    ROUND(
        AVG(f.energy_kwh),
        2
    ) AS avg_energy_kwh,

    ROUND(
        SUM(f.energy_kwh),
        2
    ) AS total_energy_kwh

FROM fact_weather_energy f

JOIN dim_city c
    ON f.city_id = c.city_id

GROUP BY c.city

ORDER BY total_energy_kwh DESC;
""").df()

q1.to_csv(
    OUTPUT_DIR /
    "01_resumen_ciudad.csv",
    index=False,
)



# CONSULTA 2
# Consumo promedio por hora


q2 = con.execute("""
SELECT
    t.hour,

    ROUND(
        AVG(f.energy_kwh),
        2
    ) AS avg_energy_kwh

FROM fact_weather_energy f

JOIN dim_time t
    ON f.time_id = t.time_id

GROUP BY t.hour

ORDER BY avg_energy_kwh DESC;
""").df()

q2.to_csv(
    OUTPUT_DIR /
    "02_consumo_hora.csv",
    index=False,
)

# CONSULTA 3
# Evolución mensual


q3 = con.execute("""
SELECT
    c.city,
    t.month,

    ROUND(
        AVG(f.temperature_c),
        2
    ) AS avg_temperature_c,

    ROUND(
        SUM(f.energy_kwh),
        2
    ) AS total_energy_kwh

FROM fact_weather_energy f

JOIN dim_city c
    ON f.city_id = c.city_id

JOIN dim_time t
    ON f.time_id = t.time_id

GROUP BY
    c.city,
    t.month

ORDER BY
    c.city,
    t.month;
""").df()

q3.to_csv(
    OUTPUT_DIR /
    "03_resumen_mensual.csv",
    index=False,
)

# CONSULTA 4
# Correlación temperatura / consumo


q4 = con.execute("""
SELECT
    c.city,

    ROUND(
        CORR(
            f.temperature_c,
            f.energy_kwh
        ),
        4
    ) AS correlation_temperature_energy

FROM fact_weather_energy f

JOIN dim_city c
    ON f.city_id = c.city_id

GROUP BY c.city

ORDER BY c.city;
""").df()

q4.to_csv(
    OUTPUT_DIR /
    "04_correlacion.csv",
    index=False,
)

# 8. MOSTRAR RESULTADOS


print("\n[6/7] RESULTADO POR CIUDAD")
print("-" * 70)

print(
    q1.to_string(index=False)
)


print("\nHORAS CON MAYOR CONSUMO PROMEDIO")
print("-" * 70)

print(
    q2.head(5).to_string(index=False)
)


print("\nCORRELACIÓN TEMPERATURA / CONSUMO")
print("-" * 70)

print(
    q4.to_string(index=False)
)

# 9. CREAR REPORTE BASE EN MARKDOWN


print("\n[7/7] Generando reporte base...")


top_city = q1.iloc[0]["city"]

top_hour = int(
    q2.iloc[0]["hour"]
)


report = f"""
# Evidencia de aprendizaje 1
## Creación de una base de datos analítica

### 1. Introducción

El presente proyecto desarrolla una base de datos analítica
orientada al análisis de información meteorológica y datos
sintéticos de consumo energético para cinco ciudades de
Colombia: Medellín, Bogotá, Cali, Barranquilla y Bucaramanga.

La solución integra información meteorológica obtenida mediante
la API pública Open-Meteo y una variable sintética de consumo
energético construida mediante Python.

---

## 2. Descripción del problema

Para organizaciones del sector energético resulta importante
analizar información histórica que permita estudiar la relación
entre variables ambientales, patrones temporales y demanda de
energía.

La problemática seleccionada consiste en construir un entorno
analítico que permita almacenar y consultar información
meteorológica horaria y simular escenarios de consumo
energético en diferentes ciudades colombianas.

---

## 3. Objetivo general

Diseñar e implementar una base de datos analítica para almacenar
y analizar información meteorológica y datos sintéticos de
consumo energético utilizando Python, una API pública y DuckDB.

---

## 4. Objetivos específicos

- Consumir información meteorológica desde una API REST.
- Almacenar los datos originales para garantizar trazabilidad.
- Limpiar y transformar la información mediante Python.
- Generar datos sintéticos de consumo energético.
- Diseñar un modelo dimensional de datos.
- Implementar la solución utilizando DuckDB.
- Ejecutar consultas SQL orientadas al análisis de los datos.

---

## 5. Datos disponibles

La información meteorológica fue obtenida de Open-Meteo.

Variables utilizadas:

- Fecha y hora.
- Ciudad.
- Latitud.
- Longitud.
- Temperatura.
- Humedad relativa.
- Precipitación.
- Velocidad del viento.

Adicionalmente se generó la variable `energy_kwh`, que representa
un consumo energético sintético.

El conjunto final contiene {len(weather):,} registros.

Los datos sintéticos no representan mediciones reales de consumo.
Fueron creados exclusivamente con fines académicos.

---

## 6. Solución propuesta

Se utilizó el siguiente stack tecnológico:

- Visual Studio Code como entorno de desarrollo.
- Python 3.12.
- Requests para consumo de API.
- Pandas para procesamiento.
- NumPy para generación de datos sintéticos.
- DuckDB como SGBD analítico.
- SQL para consultas analíticas.

DuckDB fue seleccionado debido a que permite realizar consultas
analíticas mediante SQL sin requerir un servidor de base de datos
ejecutándose permanentemente.

---

## 7. Arquitectura

Open-Meteo API
        |
        v
Python / Requests
        |
        v
JSON RAW
        |
        v
Pandas
        |
        v
CSV procesado
        |
        v
DuckDB
        |
        +-- dim_city
        |
        +-- dim_time
        |
        +-- fact_weather_energy
        |
        v
Consultas SQL
        |
        v
Resultados analíticos

---

## 8. Modelo de datos

La solución utiliza un esquema dimensional tipo estrella.

### dim_city

Contiene:

- city_id
- city
- latitude
- longitude

### dim_time

Contiene:

- time_id
- observation_time
- observation_date
- year
- month
- day
- hour
- weekday

### fact_weather_energy

Contiene las métricas:

- temperature_c
- humidity_pct
- precipitation_mm
- wind_speed_kmh
- energy_kwh
- synthetic_energy

y las claves:

- city_id
- time_id

---

## 9. Metodología

La metodología desarrollada corresponde a un pipeline ETL.

### Extracción

Se realizaron solicitudes HTTP a Open-Meteo para obtener
información meteorológica histórica.

Las respuestas originales fueron almacenadas en formato JSON.

### Transformación

Los datos fueron convertidos a DataFrames mediante Pandas.

Se realizaron controles de:

- duplicados;
- valores nulos;
- tipos de datos;
- fechas.

Posteriormente se generó la variable de consumo energético
sintético.

### Carga

Los datos procesados fueron cargados en DuckDB.

Inicialmente fueron almacenados en una tabla staging y
posteriormente transformados en un modelo dimensional.

---

## 10. Resultados

La tabla de hechos contiene {count_fact:,} observaciones.

La ciudad con mayor consumo energético total dentro del modelo
sintético fue:

**{top_city}**

La hora con mayor consumo energético promedio fue:

**{top_hour}:00**

### Resumen por ciudad

{q1.to_markdown(index=False)}

### Correlación entre temperatura y consumo

{q4.to_markdown(index=False)}

---

## 11. Conclusiones

La implementación permitió construir correctamente una base de
datos analítica utilizando información proveniente de una fuente
externa y datos sintéticos.

DuckDB permitió implementar un entorno SQL analítico sin la
necesidad de instalar o administrar un servidor tradicional como
MySQL.

La separación de la información en dimensiones y una tabla de
hechos facilita consultas agregadas por ciudad y tiempo.

La generación de consumo sintético permitió simular patrones de
demanda y comprobar el funcionamiento del modelo sin presentar
información artificial como si correspondiera a mediciones reales.

Finalmente, el ejercicio demuestra cómo una arquitectura sencilla
de extracción, transformación, almacenamiento y análisis puede
servir como base para soluciones de mayor escala.

---

## 12. Bibliografía

Institución Universitaria Digital de Antioquia. (2026).
*Infraestructura y Arquitectura para Big Data*.

DuckDB. (2026). *DuckDB Documentation*.

Open-Meteo. (2026). *Historical Weather API*.

Python Software Foundation. (2026). *Python Documentation*.

---

## 13. Anexos

Como anexos del proyecto se incluyen:

- Código fuente `main.py`.
- Archivos JSON originales.
- Dataset procesado.
- Base de datos `analytics.duckdb`.
- Resultados de consultas en formato CSV.

"""


report_file = (
    OUTPUT_DIR /
    "reporte_base.md"
)

with open(
    report_file,
    "w",
    encoding="utf-8",
) as file:

    file.write(report)


print(
    f"   Reporte generado: {report_file}"
)


con.close()


print("\n" + "=" * 70)
print("PROCESO FINALIZADO CORRECTAMENTE")
print("=" * 70)

print("\nArchivos importantes:")

print(
    f"Base de datos: {db_file}"
)

print(
    f"Dataset: {processed_file}"
)

print(
    f"Reporte: {report_file}"
)