# Comprobaciones de la integración

Se ejecutaron 44 pruebas locales el 30 de septiembre de 2026 (America/Bogota): 13 heredadas de limpieza, 25 de enriquecimiento y 6 nuevas del modelo. El registro está en `src/static/auditoria/tests.log`. La ejecución remota se registra por separado en ENTREGA.md.

## Qué se comprobó

- La lectura de los cinco JSON guardados de EA1 reconstruye exactamente los valores obtenidos al consultar `src/db/ingestion.db`.
- El CSV limpio nuevo coincide byte a byte con el aprobado en EA2. SHA-256: `e61e5770af3c2b895eedf0f1e5c1f2a2c2acb7825b68dc25969d39824b3894d6`.
- El CSV enriquecido nuevo coincide byte a byte con el antecedente. SHA-256: `f5698168dfe2821965284afa065c777bfc98af73bb78de7a046f0460f2fd3619`.
- Los cruces conservan 43.800 filas y las 32 columnas heredadas; el resultado tiene 63 columnas y la muestra 1.200 filas.
- La vista SQLite reconstruye exactamente las 2.759.400 celdas del CSV final después de convertir booleanos a 0/1. En SQLite, 1 representa verdadero y 0 representa falso.
- `PRAGMA integrity_check` devuelve `ok`; `foreign_key_check` no devuelve filas.
- Las pruebas del modelo rechazan una fecha sin padre, una hora duplicada, un booleano fuera de 0/1 y valores solares inconsistentes para una ciudad-fecha.
- Los códigos `05001` y `08` conservan sus ceros iniciales. La radiación diaria se almacena en 1.825 filas, separada de las 43.800 observaciones horarias.

## Cómo repetir las comprobaciones

Desde `sebastian_clavijo_correa` y con las dependencias instaladas:

```bash
python -m unittest discover -s tests -v
python src/pipeline.py --output-dir build
```

La carpeta `build` está excluida de Git. Su archivo `pipeline_validation.json` contiene el resultado de la nueva ejecución. Los reportes de `src/static/auditoria` corresponden a la entrega guardada en el repositorio. Como los registros usan UTC, algunas fechas pueden aparecer como el día siguiente frente a la hora de Colombia.

Estas pruebas revisan las reglas y la consistencia de los datos del proyecto. Queda pendiente medir el rendimiento con datos distribuidos o con varios usuarios a la vez. Tampoco se entrenaron modelos de predicción.

## Comprobación después de revisar la redacción

El 30 de septiembre de 2026 volví a ejecutar las 44 pruebas y el proceso completo después de ajustar el texto y el formato del código. Todas las pruebas pasaron. Los CSV limpio y enriquecido conservan sus hashes, y la vista SQLite devuelve los mismos valores.

También comparé la estructura del código Python con la versión anterior, dejando por fuera los comentarios y las cadenas de documentación. La lógica del procesamiento y de las pruebas se mantiene. Las 14 páginas del PDF se revisaron visualmente.

Los registros de esta revisión están en `src/static/auditoria/tests_style.log`, `style_pipeline_validation.json` y `style_revision.json`.
