# Pruebas del enriquecimiento

**Autor:** Juan Sebastian Clavijo Correa.

Las pruebas revisan dos compromisos del proyecto: incorporar información sin cambiar las observaciones de EA2 y dejar evidencia cuando un cruce no tiene suficiente cobertura. También comprueban que las unidades, las fechas y los identificadores conserven su significado al pasar de una fuente a otra.

La mayoría de los casos utiliza tres observaciones y archivos temporales. Allí se introducen duplicados, valores inválidos o pérdidas de cobertura de forma deliberada. Que las fuentes reales hayan pasado la validación no demuestra cómo respondería el programa ante esos problemas; por eso se prueban por separado. Una sola prueba ejecuta el proceso completo con las instantáneas históricas incluidas en el repositorio.

## Cómo ejecutarlas

Desde la raíz del repositorio:

```bash
cd sebastian_clavijo_correa
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps --no-build-isolation
python -m unittest discover -s tests -v
```

Los comandos funcionan en PowerShell, Bash y el runner de GitHub Actions con Python 3.12. Las pruebas no descargan datos ni llaman a `prepare_sources.py --fetch`. Las bases que se crean para los casos artificiales y todas las salidas de integración se guardan en directorios temporales que se eliminan al terminar. La base real se abre en modo de solo lectura.

La integración real requiere `src/db/ingestion.db`, las seis fuentes preparadas y `src/sources/source_manifest.json`. Si falta alguno, `unittest` informa que ese caso fue omitido. Una ejecución con omisiones no equivale a haber comprobado la integración real.

## Casos incluidos

El archivo [test_enrichment.py](../tests/test_enrichment.py) contiene **25 pruebas**. Algunos métodos recorren varios datos defectuosos con `subTest`; esos escenarios no se cuentan como pruebas adicionales en el total que muestra `unittest`.

### Fuentes y cruces

| Prueba | Comportamiento que comprueba |
|---|---|
| `test_city_normalization_handles_accents_case_and_spacing` | Tildes, mayúsculas y espacios producen la misma clave auxiliar. |
| `test_reads_six_formats_and_preserves_leading_zero_codes` | Se leen JSON, Excel, CSV, HTML, XML y TXT; los códigos `05001` y `05` siguen siendo texto. |
| `test_original_32_columns_and_source_frames_remain_unchanged` | Se conservan exactamente las 32 columnas de entrada, su orden lógico y los DataFrames de las fuentes. |
| `test_duplicate_keys_in_each_source_stop_many_to_one_join` | Una clave repetida en cualquiera de las seis fuentes detiene el cruce. |
| `test_missing_coverage_preserves_rows_and_marks_incomplete` | La falta de datos solares conserva las filas, deja nulos y marca `INCOMPLETE`. |
| `test_matched_source_with_missing_payload_is_still_incomplete` | Encontrar la clave no basta: un atributo adicional nulo también indica información incompleta. |
| `test_late_local_hour_uses_local_date_even_when_utc_is_next_day` | Las 23:00 de Colombia se cruzan con su fecha local, aunque UTC ya indique el día siguiente. |
| `test_solar_units_convert_mj_and_seconds` | 7,2 MJ/m² equivalen a 2 kWh/m²; 43.200 y 10.800 segundos se convierten en 12 y 3 horas. |
| `test_thermal_reference_18_has_distinct_below_equal_and_above_cases` | Las temperaturas de 15, 18 y 21 °C producen diferencias de 3, 0 y 3 respecto de la referencia académica de 18 °C. |
| `test_payload_collision_cannot_overwrite_base_column` | Una fuente no puede reemplazar una columna existente en la base. |
| `test_duplicate_base_city_hour_is_rejected` | Se rechaza una observación repetida para la misma ciudad y hora. |
| `test_duplicate_source_row_is_rejected` | `source_row` no puede identificar dos observaciones distintas. |
| `test_invalid_base_temperatures_are_rejected` | Texto no numérico, infinito y temperatura ausente impiden continuar. |
| `test_calendar_fields_must_agree_with_local_time` | Hora, mes, año y zona horaria deben corresponder a la fecha local de la observación. |

### Validación de archivos

| Prueba | Comportamiento que comprueba |
|---|---|
| `test_normalization_cannot_hide_duplicate_city_keys` | Dos nombres que se vuelven iguales después de normalizarlos no pueden pasar como ciudades distintas. |
| `test_invalid_solar_values_and_durations_are_rejected` | Se rechazan texto, infinito, radiación negativa, duración de luz superior a un día y tiempo de sol superior al de luz. |
| `test_hash_mismatch_stops_run_before_writing_outputs` | Alterar una fuente sin actualizar su procedencia detiene la ejecución antes de crear resultados. |
| `test_manifest_must_identify_every_required_source` | El manifiesto debe incluir las seis fuentes utilizadas. |
| `test_municipality_and_department_codes_must_correspond` | El prefijo del código municipal tiene que coincidir con el código departamental. |
| `test_unknown_calendar_boolean_is_rejected` | Un valor desconocido no se interpreta silenciosamente como festivo o día ordinario. |

### Muestreo y salidas

| Prueba | Comportamiento que comprueba |
|---|---|
| `test_60_strata_have_20_reproducible_observations_each` | Cinco ciudades y doce meses producen 60 estratos con 20 filas cada uno; la semilla repite la selección y otra semilla la cambia. |
| `test_small_group_is_kept_in_full_with_weight_one` | Un grupo menor de 20 filas se conserva completo y recibe peso 1. |
| `test_nonpositive_quota_is_rejected` | La cuota de muestreo debe ser positiva. |
| `test_small_run_preserves_database_and_exports_equivalent_csv_excel` | Un recorrido completo con tres filas genera auditoría y manifiesto, conserva el hash de la base y exporta la misma muestra a CSV y Excel. |
| `test_real_historical_sources_preserve_all_rows_and_sample_contract` | La ejecución con los archivos reales conserva 43.800 filas y 32 columnas originales, produce la muestra de 1.200 filas y mantiene la procedencia histórica. |

La comparación CSV–Excel revisa todas las celdas de la muestra. Reconoce las diferencias de representación del formato: Excel guarda fechas sin zona, mientras el CSV incluye el desplazamiento horario; la columna `timezone` conserva `America/Bogota`. Las fechas se comparan en su zona correspondiente, los booleanos por su valor y los códigos como cadenas. Para números se admite una tolerancia de serialización de hasta `max(1e-10, abs(valor) × 1e-12)`.

En la integración real también se comprueba que las observaciones sean de 2025 y que el registro DIVIPOLA de Bucaramanga conserve el año 2024 de la fuente. No se cambia ese año por el nombre del servicio MGN 2025. Los hashes de la base y de los archivos preparados se comparan antes y después de ejecutar el proceso.

## Resultado comprobado

El **22 de septiembre de 2026**, la ejecución local con Python 3.12 y las dependencias fijadas en requirements.txt completó **25 pruebas en 14,162 segundos**, con resultado `OK`, sin fallos, errores ni pruebas omitidas. La integración real estuvo incluida. La muestra tuvo 60 estratos, 20 registros por estrato y ninguna fila marcada como incompleta en las fuentes revisadas.

En GitHub Actions se ejecuta el mismo comando y su salida se conserva en `src/static/auditoria/tests.log`, dentro del artefacto de evidencias. El historial posterior debe consultarse en [Actions del repositorio](https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube/actions); el resultado local anterior no acredita por sí solo una ejecución remota.

El **23 de septiembre de 2026**, la [ejecución remota 35820741385](https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube/actions/runs/35820741385) completó también las 25 pruebas, el enriquecimiento, la verificación de salidas y la publicación del artefacto. Corresponde al commit `28f7c01364346cd07c77be610698cd370e65e31a`.

## Alcance de la comprobación

Estas pruebas validan contratos concretos de lectura, integración, muestreo y exportación. No prueban que los datos meteorológicos representen una medición municipal, que la referencia térmica describa confort real ni que el enriquecimiento mejore una predicción. Tampoco convierten la energía sintética de EA1 en una medición. Esas limitaciones siguen vigentes aunque la suite termine correctamente.
