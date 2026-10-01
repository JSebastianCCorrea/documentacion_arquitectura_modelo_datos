# Comprobaciones de la integración

Se ejecutaron 44 pruebas locales el 30 de septiembre de 2026 (America/Bogota): 13 heredadas de limpieza, 25 de enriquecimiento y 6 nuevas del modelo. El registro está en `src/static/auditoria/tests.log`. La ejecución remota se registra por separado en ENTREGA.md.

## Qué se comprobó

- El replay de los cinco JSON de EA1 reconstruye exactamente los valores obtenidos al consultar `src/db/ingestion.db`.
- El CSV limpio nuevo coincide byte a byte con el aprobado en EA2. SHA-256: `e61e5770af3c2b895eedf0f1e5c1f2a2c2acb7825b68dc25969d39824b3894d6`.
- El CSV enriquecido nuevo coincide byte a byte con el antecedente. SHA-256: `f5698168dfe2821965284afa065c777bfc98af73bb78de7a046f0460f2fd3619`.
- Los cruces preservan 43.800 filas y las 32 columnas heredadas; el resultado tiene 63 columnas y la muestra 1.200 filas.
- La vista SQLite reconstruye exactamente las 2.759.400 celdas del CSV final después de convertir booleanos a 0/1. Esta representación explícita no modifica su significado.
- `PRAGMA integrity_check` devuelve `ok`; `foreign_key_check` no devuelve filas.
- Las pruebas del modelo rechazan una fecha sin padre, una hora duplicada, un booleano fuera de 0/1 y valores solares inconsistentes para una ciudad-fecha.
- Los códigos `05001` y `08` conservan sus ceros iniciales. La radiación diaria se almacena en 1.825 filas, separada de las 43.800 observaciones horarias.

## Repetición

Desde `sebastian_clavijo_correa` y con las dependencias instaladas:

```bash
python -m unittest discover -s tests -v
python src/pipeline.py --output-dir build
```

El directorio `build` no está versionado. `pipeline_validation.json` describe la corrida nueva; los reportes dentro de `src/static/auditoria` documentan la instantánea entregada. Los sellos UTC del registro pueden corresponder al día siguiente de la fecha local colombiana.

No se ejecutó un benchmark distribuido, una prueba de usuarios concurrentes ni entrenamiento predictivo. Las pruebas demuestran consistencia del lote y contratos, no disponibilidad continua ni rendimiento a escala productiva.
