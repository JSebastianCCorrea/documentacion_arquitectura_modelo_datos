# Arquitectura y modelo de datos

**Juan Sebastian Clavijo Correa · Infraestructura y Arquitectura para Big Data · IUDigital**

El proyecto reúne la ingesta meteorológica, la limpieza y el enriquecimiento del curso. El documento principal es [docs/arquitectura_modelo.pdf](docs/arquitectura_modelo.pdf). Explica la arquitectura, sus dos diagramas, todas las tablas y tipos del modelo, la automatización y las limitaciones.

Hay 43.800 observaciones de 2025 para cinco ciudades. El conjunto limpio tiene 32 columnas y el enriquecido 63. `energy_kwh` es sintética: no representa consumo medido. La nube se simula con archivos locales y ejecución en GitHub Actions; no se despliegan servicios AWS ni un clúster Spark.

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

La cadena completa reproduce los cinco JSON de EA1, limpia, enriquece y materializa SQLite. No consulta nuevamente las APIs. Genera salidas nuevas en `build/`, que no está versionado:

| Ruta en build | Contenido |
|---|---|
| `db/replayed.duckdb` | Ingesta reconstruida y contrastada con EA1 |
| `cleaning/xlsx/cleaned_full.csv` | CSV limpio nuevo, idéntico al aprobado en EA2 |
| `cleaning/static/auditoria/` | Reporte de limpieza, perfiles y rechazos |
| `db/cleaned.duckdb` | Entrada tipada para enriquecimiento |
| `data/enriched_full.csv` | Las 43.800 filas y 63 columnas |
| `xlsx/enriched_data.csv` y `.xlsx` | Muestra de 1.200 filas |
| `db/analytics.sqlite` | Modelo de seis tablas y una vista |
| `sql/schema.sql` | DDL ejecutado |
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

El workflow activo está además en `.github/workflows/bigdata.yml` de la raíz del repositorio, como exige GitHub. CI comprueba que ambas copias coincidan.

## 4. Modelo y decisiones

- **Ingesta:** JSON de Open-Meteo, Pandas y energía sintética con NumPy (semilla 42). DuckDB organiza staging, ciudad, tiempo y hechos; se compara con EA1.
- **Limpieza:** claves, duplicados, nulos, tipos, rangos y atípicos. En esta entrada no hubo imputaciones ni eliminaciones; se conservaron 6.240 filas señaladas como atípicas.
- **Enriquecimiento:** seis LEFT JOIN muchos-a-uno aportan geografía, calendario, radiación y catálogos; conservan todas las filas y las 32 columnas originales.
- **SQLite:** `dim_city`, `dim_date`, `dim_hour`, `dim_time`, `fact_solar_day` y `fact_hourly`. `enriched_data` reconstruye las 63 columnas. PK, FK, UNIQUE, NOT NULL y CHECK protegen el modelo.

Los valores solares diarios se repiten en el CSV horario: para sumar radiación consulta `fact_solar_day`. [src/sql/consultas.sql](src/sql/consultas.sql) contiene ejemplos. Los archivos `.drawio` de [diagramas](docs/diagramas) se abren en diagrams.net.

## 5. GitHub Actions

Se activa con push, pull_request o workflow_dispatch. Instala dependencias, ejecuta 44 pruebas y genera el lote completo desde cero en `build/`. Una discrepancia de fuentes, claves o resultados detiene la ejecución. No necesita secretos ni credenciales cloud.

El artefacto `arquitectura-modelo-<run_id>-<intento>` conserva datos nuevos, bases, logs, auditorías, SQL, PDF y diagramas durante 30 días. Los reportes versionados en `src/static/auditoria` corresponden a la entrega local. El enlace de la ejecución remota verificada está en [ENTREGA.md](docs/ENTREGA.md).

## 6. Trazabilidad y límites

[TRAZABILIDAD.md](docs/TRAZABILIDAD.md) identifica commits, archivos y huellas de los antecedentes. `ingestion.db` sigue siendo DuckDB porque conserva EA1; `analytics.sqlite` añade el modelo solicitado. La extensión no cambia el motor. PySpark se analiza como alternativa futura; no se utiliza.

Los z-scores y marcas IQR usan todo 2025: antes de modelar, divide por tiempo y ajusta transformaciones solo con entrenamiento. La radiación diaria completa no está disponible al inicio de ese día. La referencia térmica de 18 °C y las franjas horarias son académicas. Procedencia y licencias: [FUENTES.md](docs/FUENTES.md). Pruebas y alcance: [PRUEBAS.md](docs/PRUEBAS.md).

## 7. Regenerar el PDF

```bash
python -m pip install reportlab==5.0.1
python scripts/build_document.py
```

La fuente del documento es `scripts/build_document.py`; el catálogo físico se obtiene de `src/static/auditoria/model_validation.json`. Tras cualquier cambio revisa visualmente las páginas. El comando no realiza una entrega en el aula.
