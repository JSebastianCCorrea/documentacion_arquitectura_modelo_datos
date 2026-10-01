# Arquitectura y modelo de datos

**Juan Sebastian Clavijo Correa · Infraestructura y Arquitectura para Big Data · IUDigital**

En este proyecto reuní la ingesta de datos del clima, la limpieza y el enriquecimiento que trabajé durante el curso. En [docs/arquitectura_modelo.pdf](docs/arquitectura_modelo.pdf) explico el recorrido de los datos, las tablas del modelo y la automatización. El documento incluye los diagramas de arquitectura y de relaciones.

La base contiene 43.800 observaciones de cinco ciudades durante 2025. Después de la limpieza quedan 32 columnas, y con el enriquecimiento pasan a ser 63. `energy_kwh` es una variable simulada para la actividad. Para representar el entorno de nube uso archivos locales y GitHub Actions; no se han desplegado servicios AWS ni un clúster Spark.

## 1. Clonar e instalar

Requiere Python 3.12. SQLite está incluido con Python; se necesita versión 3.37 o posterior para tablas STRICT.

```bash
git clone https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos.git
cd documentacion_arquitectura_modelo_datos/sebastian_clavijo_correa
python -m venv .venv
```

Activa el entorno con `.venv\Scripts\Activate.ps1` en PowerShell o `source .venv/bin/activate` en Linux/macOS. Después:

```bash
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps --no-build-isolation
python -m unittest discover -s tests -v
python src/pipeline.py --output-dir build
```

El proceso completo vuelve a leer los cinco JSON guardados de EA1, limpia los datos, los enriquece y crea la base SQLite. Trabaja sin volver a consultar las API. Las nuevas salidas quedan en `build/`, una carpeta que Git no incluye:

| Ruta en build | Contenido |
|---|---|
| `db/replayed.duckdb` | Ingesta generada de nuevo y comparada con EA1 |
| `cleaning/xlsx/cleaned_full.csv` | CSV limpio nuevo, idéntico al aprobado en EA2 |
| `cleaning/static/auditoria/` | Reporte de limpieza, perfiles y rechazos |
| `db/cleaned.duckdb` | Datos limpios con los tipos que necesita el enriquecimiento |
| `data/enriched_full.csv` | Las 43.800 filas y 63 columnas |
| `xlsx/enriched_data.csv` y `.xlsx` | Muestra de 1.200 filas |
| `db/analytics.sqlite` | Modelo de seis tablas y una vista |
| `sql/schema.sql` | Instrucciones SQL usadas para crear el modelo |
| `static/auditoria/` | Informes de ingesta, enriquecimiento y validaciones |

## 2. Ejecutar solo enriquecimiento

La base limpia y las fuentes ya están incluidas:

```bash
python src/enrichment.py
python scripts/verify_outputs.py
```

Estos comandos escriben en `src/data`, `src/xlsx` y `src/static/auditoria`. Para reconstruir el modelo tras cambiar el enriquecimiento:

```bash
python src/model.py
```

Si necesitas reconstruir `src/db/cleaned.duckdb` desde el CSV aprobado de EA2, ejecuta `python scripts/prepare_base.py`; actualiza también su manifiesto.

## 3. Estructura académica

```text
sebastian_clavijo_correa/
├── setup.py
├── requirements.txt
├── README.md
├── .github/workflows/bigdata.yml
├── src/
│   ├── ingestion.py
│   ├── cleaning.py
│   ├── enrichment.py
│   ├── model.py
│   ├── pipeline.py
│   ├── db/
│   │   ├── ingestion.db          # DuckDB original de EA1
│   │   ├── cleaned.duckdb        # Entrada limpia del enriquecimiento
│   │   └── analytics.sqlite      # Modelo final SQLite
│   ├── data/                    # JSON originales, CSV y referencias
│   ├── sources/                 # JSON, XLSX, CSV, XML, HTML y TXT
│   ├── xlsx/                    # Datos limpios y enriquecidos
│   ├── sql/                     # Esquema y consultas
│   └── static/auditoria/         # Evidencias de las fases y del modelo
├── docs/
│   ├── arquitectura_modelo.pdf
│   ├── diagramas/               # PDF vectorial y .drawio editables
│   ├── DICCIONARIO_DATOS.md
│   ├── FUENTES.md
│   ├── TRAZABILIDAD.md
│   ├── PRUEBAS.md
│   ├── ENTREGA.md
│   └── antecedentes/
├── scripts/
└── tests/
```

GitHub ejecuta el workflow que está en `.github/workflows/bigdata.yml`, en la raíz del repositorio. Dejé la copia interior para cumplir la estructura de la actividad. La ejecución automática comprueba que las dos sean iguales.

## 4. Cómo organicé el proceso

- **Ingesta:** leo los JSON de Open-Meteo y repito la energía simulada con NumPy y semilla 42. DuckDB organiza las tablas de entrada, ciudad, tiempo y mediciones. El resultado se compara con EA1.
- **Limpieza:** claves, duplicados, nulos, tipos, rangos y atípicos. En esta entrada no hubo imputaciones ni eliminaciones; se conservaron 6.240 filas señaladas como atípicas.
- **Enriquecimiento:** hago seis cruces LEFT JOIN de muchos registros a una clave de referencia. Agregan geografía, calendario, radiación y catálogos, conservando las filas y las 32 columnas originales.
- **SQLite:** `dim_city`, `dim_date`, `dim_hour`, `dim_time`, `fact_solar_day` y `fact_hourly`. `enriched_data` reconstruye las 63 columnas. PK, FK, UNIQUE, NOT NULL y CHECK protegen el modelo.

Los valores solares diarios se repiten en el CSV horario: para sumar radiación consulta `fact_solar_day`. [src/sql/consultas.sql](src/sql/consultas.sql) contiene ejemplos. Los archivos `.drawio` de [diagramas](docs/diagramas) se abren en diagrams.net.

## 5. GitHub Actions

GitHub Actions se activa al subir cambios (`push`), abrir una solicitud de cambios (`pull_request`) o iniciarlo manualmente (`workflow_dispatch`). Instala las dependencias, ejecuta 44 pruebas y genera todos los resultados en `build/`. Si una fuente, una clave o un resultado no coincide con lo esperado, el proceso se detiene. Para esta ejecución no hacen falta credenciales de nube.

El paquete de resultados, llamado `arquitectura-modelo-<run_id>-<intento>`, guarda los datos nuevos, las bases, los registros de ejecución, el SQL, el PDF y los diagramas durante 30 días. En `src/static/auditoria` están los reportes de la entrega local. La ejecución de GitHub que se revisó está enlazada en [ENTREGA.md](docs/ENTREGA.md).

## 6. Trazabilidad y límites

En [TRAZABILIDAD.md](docs/TRAZABILIDAD.md) dejé los commits, archivos y hashes de las actividades anteriores. `ingestion.db` conserva la base DuckDB de EA1, mientras `analytics.sqlite` contiene el modelo de esta entrega. PySpark queda como una opción si aumenta el volumen de datos; no se utiliza en el proceso actual.

Los z-scores y las marcas IQR se calcularon con todo 2025. Para un modelo predictivo habría que separar los datos por tiempo y calcular las transformaciones solo con entrenamiento. También se debe revisar cuándo está disponible la radiación del día completo antes de usarla para predecir. La referencia de 18 °C y las franjas horarias se definieron para el ejercicio. Los detalles están en [FUENTES.md](docs/FUENTES.md) y [PRUEBAS.md](docs/PRUEBAS.md).

## 7. Regenerar el PDF

```bash
python -m pip install reportlab==5.0.1
python scripts/build_document.py
```

El texto y el formato del documento están en `scripts/build_document.py`. Las tablas se construyen con la información de `src/static/auditoria/model_validation.json` y las descripciones del diccionario. Después de cambiar el texto, conviene abrir el PDF y revisar todas las páginas.
