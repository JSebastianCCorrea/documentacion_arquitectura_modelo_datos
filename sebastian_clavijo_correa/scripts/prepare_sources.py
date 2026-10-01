"""Prepara las seis fuentes a partir de respuestas públicas guardadas en el repositorio.

La ejecución normal no usa Internet. --fetch descarga nuevas respuestas antes de
preparar los archivos y cambia las huellas del manifiesto.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT / "src" / "sources"
CITIES = {
    "Barranquilla": (10.9685, -74.7813, "08001"),
    "Bogota": (4.7110, -74.0721, "11001"),
    "Bucaramanga": (7.1193, -73.1227, "68001"),
    "Cali": (3.4516, -76.5320, "76001"),
    "Medellin": (6.2442, -75.5812, "05001"),
}
HOLIDAY_URL = "https://date.nager.at/api/v3/PublicHolidays/2025/CO"
DANE_URL = (
    "https://portalgis.dane.gov.co/mparcgis/rest/services/Divipola/"
    "Serv_DIVIPOLA_MGN_2025/FeatureServer/317/query"
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def query_url(endpoint: str, **parameters: object) -> str:
    return endpoint + "?" + urllib.parse.urlencode(parameters)


def requests_to_make() -> dict[str, str]:
    queries = {"holidays_co_2025.json": HOLIDAY_URL}
    for city, (latitude, longitude, _) in CITIES.items():
        queries[f"geocoding_{city}.json"] = query_url(
            "https://geocoding-api.open-meteo.com/v1/search",
            name=city, count=10, language="es", format="json", countryCode="CO",
        )
        queries[f"solar_{city}_2025.json"] = query_url(
            "https://archive-api.open-meteo.com/v1/archive",
            latitude=latitude, longitude=longitude,
            start_date="2025-01-01", end_date="2025-12-31",
            daily="shortwave_radiation_sum,daylight_duration,sunshine_duration",
            timezone="America/Bogota", models="era5",
        )
    codes = ",".join(f"'{value[2]}'" for value in CITIES.values())
    queries["divipola_2025.json"] = query_url(
        DANE_URL, where=f"MPIO_CDPMP IN ({codes})",
        outFields="DPTO_CCDGO,MPIO_CDPMP,MPIO_CNMBRE,DPTO_CNMBRE,MPIO_NANO",
        returnGeometry="false", f="pjson",
    )
    return queries


def fetch_snapshots(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)

    def download(item: tuple[str, str]) -> dict:
        filename, url = item
        request = urllib.request.Request(url, headers={"User-Agent": "AcademicDataIntegration/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
            final_url = response.url
            status = response.status
        payload = json.loads(data)
        if isinstance(payload, dict) and payload.get("error"):
            raise ValueError(f"La API devolvió un error: {filename}: {payload['error']}")
        destination = raw_dir / filename
        destination.write_bytes(data)
        return {
            "path": f"raw/{filename}", "source_url": url, "response_url": final_url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": status, "sha256": sha256(destination),
        }

    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(download, requests_to_make().items()))
    write_json(raw_dir / "retrieval_manifest.json", {"snapshots": records})


def load_raw(source_dir: Path) -> tuple[dict, dict]:
    raw_dir = source_dir / "raw"
    metadata_path = raw_dir / "retrieval_manifest.json"
    if not metadata_path.exists():
        raise FileNotFoundError("Faltan las respuestas guardadas. Ejecute prepare_sources.py --fetch una vez.")
    retrieval = json.loads(metadata_path.read_text(encoding="utf-8"))
    snapshots = {}
    for item in retrieval["snapshots"]:
        path = source_dir / item["path"]
        if sha256(path) != item["sha256"]:
            raise ValueError(f"La huella de la respuesta no coincide: {path.name}")
        snapshots[path.name] = json.loads(path.read_text(encoding="utf-8"))
    missing = set(requests_to_make()) - set(snapshots)
    if missing:
        raise ValueError(f"Faltan respuestas: {sorted(missing)}")
    return snapshots, retrieval


def plain_name(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)).lower()


def prepare_geography(source_dir: Path, snapshots: dict) -> None:
    records = []
    for city, (latitude, longitude, _) in CITIES.items():
        candidates = [
            row for row in snapshots[f"geocoding_{city}.json"].get("results", [])
            if row.get("country_code") == "CO"
            and row.get("feature_code") in {"PPLC", "PPLA", "PPLA2", "PPL"}
            and plain_name(row["name"]) in {plain_name(city), "santiago de cali" if city == "Cali" else plain_name(city)}
        ]
        if not candidates:
            raise ValueError(f"GeoNames no devolvió la ciudad esperada: {city}")
        # El nombre puede repetirse; la cercanía a la coordenada de EA2 resuelve el homónimo.
        selected = min(candidates, key=lambda row: (row["latitude"] - latitude) ** 2 + (row["longitude"] - longitude) ** 2)
        if (selected["latitude"] - latitude) ** 2 + (selected["longitude"] - longitude) ** 2 > 0.25:
            raise ValueError(f"El resultado de geocodificación está lejos de la ciudad de EA2: {city}")
        records.append({
            "city": city, "country_code": selected["country_code"],
            "geoname_id": selected["id"], "elevation_m": selected["elevation"],
        })
    write_json(source_dir / "city_geography.json", records)


def normalize_xlsx_archive(path: Path) -> None:
    # El contenedor ZIP lleva fechas variables aunque las celdas no cambien.
    buffer = io.BytesIO()
    with zipfile.ZipFile(path) as original, zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as stable:
        for filename in sorted(original.namelist()):
            entry = zipfile.ZipInfo(filename, date_time=(2025, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            payload = original.read(filename)
            if filename == "docProps/core.xml":
                core = ET.fromstring(payload)
                modified = core.find("{http://purl.org/dc/terms/}modified")
                if modified is not None:
                    modified.text = "2025-01-01T00:00:00Z"
                payload = ET.tostring(core, encoding="utf-8")
            stable.writestr(entry, payload)
    path.write_bytes(buffer.getvalue())


def prepare_calendar(source_dir: Path, snapshots: dict) -> tuple[int, int]:
    holidays = snapshots["holidays_co_2025.json"]
    by_date: dict[str, list[str]] = {}
    for row in holidays:
        if row["countryCode"] != "CO" or not row["date"].startswith("2025-"):
            raise ValueError("El calendario recibido no corresponde a Colombia en 2025.")
        if row.get("global") and "Public" in row.get("types", []):
            by_date.setdefault(row["date"], []).append(row["localName"])
    records = []
    for date in pd.date_range("2025-01-01", "2025-12-31"):
        names = sorted(set(by_date.get(date.strftime("%Y-%m-%d"), [])))
        records.append({
            "local_date": date.to_pydatetime(), "holiday_name": "; ".join(names) if names else "No festivo",
            "is_holiday": bool(names), "is_weekend": date.dayofweek >= 5,
        })
    frame = pd.DataFrame(records)
    path = source_dir / "calendar_2025.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
        frame.to_excel(writer, sheet_name="calendar", index=False)
        workbook = writer.book
        workbook.properties.creator = "Juan Sebastian Clavijo Correa"
        workbook.properties.created = datetime(2025, 1, 1)
        workbook.properties.modified = datetime(2025, 1, 1)
        workbook.properties.description = "Festivos públicos nacionales de Colombia 2025. Fuente: " + HOLIDAY_URL
        sheet = writer.sheets["calendar"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = "A1:D366"
        for cell in sheet[1]:
            cell.fill = PatternFill("solid", fgColor="17365D")
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(vertical="center")
        for column, width in {"A": 16, "B": 66, "C": 16, "D": 16}.items():
            sheet.column_dimensions[column].width = width
        for cell in sheet["A"][1:]:
            cell.number_format = "yyyy-mm-dd"
    normalize_xlsx_archive(path)
    return len(holidays), len(by_date)


def prepare_solar(source_dir: Path, snapshots: dict) -> dict:
    frames = []
    grids = {}
    expected_dates = pd.date_range("2025-01-01", "2025-12-31").strftime("%Y-%m-%d").tolist()
    for city, (latitude, longitude, _) in CITIES.items():
        payload = snapshots[f"solar_{city}_2025.json"]
        if payload["utc_offset_seconds"] != -18000 or payload["daily"]["time"] != expected_dates:
            raise ValueError(f"Fechas o zona horaria inesperadas en la fuente solar: {city}")
        frame = pd.DataFrame(payload["daily"]).rename(columns={
            "time": "local_date", "shortwave_radiation_sum": "shortwave_radiation_sum_mj_m2",
            "daylight_duration": "daylight_seconds", "sunshine_duration": "sunshine_seconds",
        })
        frame.insert(0, "city", city)
        frames.append(frame)
        grids[city] = {
            "requested_latitude": latitude, "requested_longitude": longitude,
            "response_latitude": payload["latitude"], "response_longitude": payload["longitude"],
            "response_elevation_m": payload["elevation"], "units": payload["daily_units"],
        }
    pd.concat(frames, ignore_index=True).to_csv(source_dir / "solar_daily_2025.csv", index=False, lineterminator="\n")
    return grids


def prepare_municipalities(source_dir: Path, snapshots: dict) -> dict:
    payload = snapshots["divipola_2025.json"]
    attributes = [feature["attributes"] for feature in payload["features"]]
    by_code = {record["MPIO_CDPMP"]: record for record in attributes}
    if len(by_code) != 5 or len(attributes) != 5:
        raise ValueError("DIVIPOLA debe devolver cinco códigos únicos.")
    records = []
    for city, (_, _, code) in CITIES.items():
        row = by_code[code]
        records.append({
            "city": city, "municipality_code": code, "municipality_name": row["MPIO_CNMBRE"],
            "department_code": row["DPTO_CCDGO"], "department_name": row["DPTO_CNMBRE"],
            "divipola_year": row["MPIO_NANO"],
        })
    table = pd.DataFrame(records).to_html(index=False, table_id="divipola", border=0)
    document = (
        '<!doctype html>\n<html lang="es"><meta charset="utf-8"><title>Municipios DIVIPOLA</title>\n'
        '<h1>Municipios de la base EA2</h1>\n'
        '<p>Tabla preparada a partir de la respuesta oficial del servicio DIVIPOLA MGN 2025. '
        'Los códigos conservan sus ceros iniciales. divipola_year reproduce MPIO_NANO de cada registro.</p>\n'
        + table + '\n<p>Fuente: Departamento Administrativo Nacional de Estadística - DANE: '
        '<a href="https://www.dane.gov.co">www.dane.gov.co</a>. '
        'Se seleccionaron cinco municipios y se adaptaron los nombres de columna. '
        '<a href="https://geoportal.dane.gov.co/acerca-del-geoportal/licencia-y-condiciones-de-uso/">'
        'Licencia y condiciones de uso</a>.</p></html>\n'
    )
    (source_dir / "municipalities.html").write_text(document, encoding="utf-8")
    return {row["city"]: row["divipola_year"] for row in records}


def prepare_authored_catalogs(source_dir: Path) -> None:
    root = ET.Element("parameters", {"purpose": "academic_illustration", "unit": "degree_Celsius"})
    for city in CITIES:
        record = ET.SubElement(root, "record")
        ET.SubElement(record, "city").text = city
        ET.SubElement(record, "reference_temperature_c").text = "18.0"
        ET.SubElement(record, "parameter_scope").text = "academic_illustration"
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(source_dir / "thermal_parameters.xml", encoding="utf-8", xml_declaration=True)
    rows = [{"hour": hour, "day_period": (
        "madrugada" if hour < 6 else "manana" if hour < 12 else "tarde" if hour < 18 else "noche"
    )} for hour in range(24)]
    pd.DataFrame(rows).to_csv(source_dir / "hour_bands.txt", sep="\t", index=False, lineterminator="\n")


def build_manifest(source_dir: Path, retrieval: dict, holidays: tuple, grids: dict, divipola_years: dict) -> None:
    snapshots = retrieval["snapshots"]
    retrieved = max(row["retrieved_at_utc"] for row in snapshots)

    def source(identifier, filename, rows, keys, provider, raw_names, license_text, license_url, notes, columns):
        raw_items = [item for item in snapshots if Path(item["path"]).name in raw_names]
        return {
            "id": identifier, "format": Path(filename).suffix[1:].upper(), "path": filename,
            "sha256": sha256(source_dir / filename), "rows": rows, "keys": keys, "columns": columns,
            "provider": provider, "type": "external_data" if raw_items else "authored_catalog",
            "source_urls": [item["source_url"] for item in raw_items],
            "retrieved_at_utc": max((item["retrieved_at_utc"] for item in raw_items), default=None),
            "license": license_text, "license_url": license_url, "notes": notes,
            "raw_paths": [item["path"] for item in raw_items],
        }

    sources = [
        source("city_geography", "city_geography.json", 5, ["city"], "Open-Meteo / GeoNames",
               [f"geocoding_{city}.json" for city in CITIES], "CC BY 4.0 (API Open-Meteo); atribución GeoNames",
               "https://open-meteo.com/en/licence",
               ["Elevación del punto geográfico de GeoNames, no del centro de rejilla meteorológica ni promedio municipal.",
                "Se escoge la coincidencia homónima de Colombia más cercana a la coordenada solicitada en EA2.",
                "Se excluye población porque la respuesta no indica la fecha de referencia de esa cifra."],
               ["city", "country_code", "geoname_id", "elevation_m"]),
        source("calendar", "calendar_2025.xlsx", 365, ["local_date"], "Nager.Date",
               ["holidays_co_2025.json"], "API para proyectos privados o sin ánimo de lucro; comercial requiere patrocinio. MIT corresponde al software, no equivale a licencia general de los datos.",
               "https://nagerholidays.com/legal/termsofservice",
               [f"La respuesta contiene {holidays[0]} festividades nacionales en {holidays[1]} fechas distintas. Se agrupan los nombres que coinciden en una fecha.",
                "Calendario completo de 365 fechas locales. is_weekend se deriva del calendario gregoriano; una fecha sin festividad se marca No festivo.",
                "Hoja calendar. No representa tarifas eléctricas, jornadas laborales ni excepciones sectoriales. API comunitaria, no autoridad normativa."],
               ["local_date", "holiday_name", "is_holiday", "is_weekend"]),
        source("solar_daily", "solar_daily_2025.csv", 1825, ["city", "local_date"], "Open-Meteo / ERA5 (ECMWF, Copernicus C3S)",
               [f"solar_{city}_2025.json" for city in CITIES], "CC BY 4.0 (API Open-Meteo)",
               "https://open-meteo.com/en/licence",
               ["Modelo era5 fijado. Datos de reanálisis en rejilla, no observaciones de una estación urbana.",
                "Agregados del día completo en America/Bogota. Solo uso retrospectivo: no están disponibles al comenzar el día y pueden producir fuga temporal en pronósticos.",
                "Se añaden variables solares. No se sustituyen las variables de EA2, cuyo modelo original no fue fijado.",
                "Radiación: MJ/m² por día. Duración de luz y sol: segundos. Valores ausentes permanecen ausentes."],
               ["city", "local_date", "shortwave_radiation_sum_mj_m2", "daylight_seconds", "sunshine_seconds"]),
        source("municipalities", "municipalities.html", 5, ["city"], "Departamento Administrativo Nacional de Estadística (DANE)",
               ["divipola_2025.json"], "CC BY 4.0, condiciones de uso del Geoportal DANE",
               "https://geoportal.dane.gov.co/acerca-del-geoportal/licencia-y-condiciones-de-uso/",
               ["HTML preparado para la actividad a partir del JSON oficial. No se presenta como una página HTML descargada del DANE.",
                "Códigos DIVIPOLA son texto y no equivalen a city_id local. Correspondencia revisada para las cinco ciudades.",
                "El servicio se denomina MGN 2025; MPIO_NANO de Bucaramanga indica 2024. Se conserva ese año sin imputarlo."],
               ["city", "municipality_code", "municipality_name", "department_code", "department_name", "divipola_year"]),
        source("thermal_parameters", "thermal_parameters.xml", 5, ["city"], "Elaboración propia para la actividad académica", [],
               "Catálogo original incluido con el proyecto académico", None,
               ["Referencia de 18 °C fijada de manera ilustrativa para las cinco ciudades.",
                "No es una norma, medición ni umbral calibrado de confort. Las diferencias térmicas derivadas no prueban consumo o causalidad."],
               ["city", "reference_temperature_c", "parameter_scope"]),
        source("hour_bands", "hour_bands.txt", 24, ["hour"], "Elaboración propia para la actividad académica", [],
               "Catálogo original incluido con el proyecto académico", None,
               ["TSV UTF-8 con clasificación propia: 00–05 madrugada, 06–11 mañana, 12–17 tarde y 18–23 noche.",
                "Se usa la hora local de America/Bogota. No es una franja tarifaria ni clasificación oficial de demanda."],
               ["hour", "day_period"]),
    ]
    write_json(source_dir / "source_manifest.json", {
        "schema_version": 1, "source_snapshot_date_utc": retrieved,
        "period": {"start": "2025-01-01", "end": "2025-12-31", "timezone": "America/Bogota"},
        "prepared_by": "scripts/prepare_sources.py", "network_required_for_pipeline": False,
        "sources": sources, "raw_snapshots": snapshots,
        "solar_grid_metadata": grids, "divipola_record_years": divipola_years,
        "external_provider_count": 3, "authored_catalog_count": 2,
        "reproduction": "python scripts/prepare_sources.py usa snapshots locales. --fetch vuelve a consultar las APIs y cambia el manifiesto.",
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Consultar las APIs y reemplazar las respuestas guardadas.")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    args = parser.parse_args()
    args.source_dir.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        fetch_snapshots(args.source_dir / "raw")
    snapshots, retrieval = load_raw(args.source_dir)
    prepare_geography(args.source_dir, snapshots)
    holidays = prepare_calendar(args.source_dir, snapshots)
    grids = prepare_solar(args.source_dir, snapshots)
    years = prepare_municipalities(args.source_dir, snapshots)
    prepare_authored_catalogs(args.source_dir)
    build_manifest(args.source_dir, retrieval, holidays, grids, years)
    print("Se prepararon seis fuentes: JSON 5 filas, XLSX 365, CSV 1825, HTML 5, XML 5 y TXT 24.")
    print(f"Festividades: {holidays[0]} registros de origen, {holidays[1]} fechas distintas.")


if __name__ == "__main__":
    main()
