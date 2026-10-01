# Continuidad entre actividades

Autor: Juan Sebastian Clavijo Correa. Materia: Infraestructura y Arquitectura para Big Data.

| Fase | Antecedente | Incorporación en esta entrega |
|---|---|---|
| Ingesta EA1 | `actividad_1/evidencia_base_analitica/main.py`, JSON y `analytics.duckdb` | Código histórico, cinco JSON originales y copia idéntica de la base como `src/db/ingestion.db`; `src/ingestion.py` reproduce sus valores sin red |
| Limpieza EA2 | Repositorio Preprocesamiento_Limpieza_de_Datos_en_Plataforma_de_Big_Data_en_la_Nube, commit `a4b8a1a5021b58104ca92b840533eb5bbf4170ed` | `src/cleaning.py`, 13 pruebas y CSV completo de referencia |
| Enriquecimiento | Repositorio Enriquecimiento_Datos_Plataforma_Big_Data_Nube, commit `100c94708766925f9132f84ed7548b9ae6c513d0`, carpeta anterior `actividad_4` | Seis fuentes, doce respuestas originales, 25 pruebas y CSV enriquecido aprobado |
| Arquitectura y modelo | Actividad actual | Un solo proceso para las fases anteriores, SQLite con reglas de integridad, 6 pruebas nuevas, diagramas y PDF |

La copia original de DuckDB tiene SHA-256 `f376669aaed6713622ef74c4ab8d7af3362626eb59fbddb380a43e04e2587d4a`. Cambiar una extensión no cambia el motor: `ingestion.db` sigue siendo DuckDB. La nueva base SQLite se llama `analytics.sqlite`.

`cleaned.duckdb` es la base del enriquecimiento anterior, renombrada para distinguirla de EA1. Su manifiesto `base_manifest.json` registra la procedencia y la huella del archivo. `scripts/prepare_base.py` puede reconstruirla desde el CSV de EA2 y actualizar el manifiesto. El pipeline integral crea otra copia en `build/db` sin sobrescribir las bases fuente.

La consulta inicial a la API se hizo en EA1. Para repetir el proceso en GitHub Actions uso las respuestas guardadas y compruebo sus hashes. Para adquirir otro periodo se necesita una nueva versión de datos, manifiestos y referencias esperadas; no basta reemplazar una respuesta o actualizar un hash. El script histórico se conserva para consulta y no forma parte de la ejecución automática.

Los documentos de `docs/antecedentes` describen la entrega anterior y sus rutas originales. La documentación vigente es el README, el PDF, PRUEBAS.md, TRAZABILIDAD.md, DICCIONARIO_DATOS.md y FUENTES.md. Las auditorías históricas y nuevas permanecen diferenciadas.

Organicé la entrega dentro de `sebastian_clavijo_correa`, siguiendo la estructura de la actividad. El workflow también está en `.github/workflows` de la raíz para que GitHub lo ejecute. El proceso comprueba que las dos copias sean iguales.
