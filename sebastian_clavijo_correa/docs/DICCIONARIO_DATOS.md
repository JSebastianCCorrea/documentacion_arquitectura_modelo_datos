# Diccionario de datos

## 1. Unidad de observación y tipos

El conjunto enriquecido contiene **43.800 filas y 63 columnas**. Cada fila representa una ciudad y una hora local de 2025. La clave natural es `(city, observation_time)`; `source_row` permite seguir la fila hasta la salida de EA2.

Los tipos de las tablas siguientes son lógicos. El CSV no almacena un esquema: al importarlo deben conservarse los códigos como texto y las fechas con su zona. En DuckDB, las fechas de entrada son `TIMESTAMPTZ`. El pipeline convierte la observación a `America/Bogota` antes de obtener la fecha local.

## 2. Columnas originales conservadas: 32

Estas columnas proceden de EA2. El enriquecimiento verifica que todos sus valores permanezcan iguales.

| Columna | Tipo / unidad | Significado |
|---|---|---|
| `city_id` | Entero | Identificador dimensional local de EA1; no es un código DANE |
| `time_id` | Entero | Identificador de la hora en la dimensión temporal de EA1 |
| `observation_time` | Fecha y hora con zona | Instante de la observación, presentado en `America/Bogota` |
| `city` | Texto | Barranquilla, Bogota, Bucaramanga, Cali o Medellin, con la escritura de EA2 |
| `latitude` | Decimal / grados | Latitud solicitada en la extracción original |
| `longitude` | Decimal / grados | Longitud solicitada en la extracción original |
| `temperature_c` | Decimal / °C | Temperatura meteorológica horaria de EA1 |
| `humidity_pct` | Decimal / % | Humedad relativa horaria |
| `precipitation_mm` | Decimal / mm | Precipitación del intervalo horario |
| `wind_speed_kmh` | Decimal / km/h | Velocidad del viento horaria |
| `energy_kwh` | Decimal / kWh | Valor energético sintético generado en EA1; no es una medición |
| `synthetic_energy` | Booleano | Identifica la energía sintética; verdadero en las 43.800 filas |
| `source_row` | Entero | Identificador de fila asignado por el proceso de EA2 |
| `year` | Entero | Año local: 2025 |
| `month` | Entero | Mes local: 1 a 12 |
| `day` | Entero | Día local del mes |
| `hour` | Entero | Hora local: 0 a 23 |
| `imputed_fields` | Texto | Campos imputados por EA2, separados por `\|`; vacío significa ninguno |
| `quality_status` | Texto | Estado de calidad de EA2; `VALID` en esta base |
| `is_outlier` | Booleano | Alguna variable quedó marcada como atípica por EA2 |
| `outlier_fields` | Texto | Variables señaladas, separadas por `\|`; vacío significa ninguna |
| `outlier_temperature_c` | Booleano | Marca IQR de temperatura |
| `outlier_humidity_pct` | Booleano | Marca IQR de humedad |
| `outlier_precipitation_mm` | Booleano | Marca IQR de precipitación |
| `outlier_wind_speed_kmh` | Booleano | Marca IQR de viento |
| `outlier_energy_kwh` | Booleano | Marca IQR de energía sintética |
| `temperature_zscore` | Decimal / sin unidad | Escalado de temperatura heredado de EA2, calculado por ciudad con todo 2025 |
| `energy_zscore` | Decimal / sin unidad | Escalado de energía heredado de EA2, calculado por ciudad con todo 2025 |
| `humidity_fraction` | Decimal / fracción | `humidity_pct / 100` |
| `precipitation_log1p` | Decimal / transformación | `ln(1 + precipitation_mm)` sobre el valor numérico en mm |
| `timezone` | Texto | `America/Bogota` |
| `observation_time_utc` | Fecha y hora UTC | El mismo instante de `observation_time`, expresado en UTC |

Las marcas de atípicos heredadas usan 1,5 veces el rango intercuartílico por ciudad; cuando IQR es cero se omite esa detección. Se mantienen 6.240 filas con alguna marca, sin borrar ni recortar sus valores. Estas marcas describen una regla estadística, no un error confirmado.

## 3. Columnas incorporadas: 31

Los identificadores de procedencia de esta tabla corresponden a `sources[].id` en [source_manifest.json](../src/sources/source_manifest.json).

| Columna | Tipo / unidad | Definición y procedencia |
|---|---|---|
| `local_date` | Fecha | Fecha de la observación en Colombia; derivada de `observation_time` |
| `country_code` | Texto | Código de país, `CO`; `city_geography` |
| `geoname_id` | Entero lógico | Identificador del punto en GeoNames; `city_geography` |
| `elevation_m` | Decimal / m | Elevación del punto geográfico retornado; `city_geography` |
| `matched_geography` | Booleano | La ciudad encontró correspondencia en el catálogo geográfico |
| `holiday_name` | Texto | Nombre de festividad o `No festivo`; nombres coincidentes agrupados; `calendar` |
| `is_holiday` | Booleano | La fecha figura como festiva en el calendario; `calendar` |
| `is_weekend` | Booleano | La fecha es sábado o domingo; `calendar` |
| `matched_calendar` | Booleano | La fecha encontró correspondencia en el calendario |
| `shortwave_radiation_sum_mj_m2` | Decimal / MJ/m²/día | Radiación de onda corta acumulada diaria; `solar_daily` |
| `daylight_seconds` | Decimal / s | Duración diaria de luz; `solar_daily` |
| `sunshine_seconds` | Decimal / s | Duración diaria de sol informada por la fuente; `solar_daily` |
| `matched_solar` | Booleano | La combinación ciudad–fecha encontró correspondencia solar |
| `municipality_code` | Texto de 5 dígitos | Código DIVIPOLA municipal; `municipalities` |
| `municipality_name` | Texto | Nombre municipal informado por DANE; `municipalities` |
| `department_code` | Texto de 2 dígitos | Código departamental; `municipalities` |
| `department_name` | Texto | Nombre departamental informado por DANE; `municipalities` |
| `divipola_year` | Entero lógico | Año del registro `MPIO_NANO`, conservado de la fuente; `municipalities` |
| `matched_municipalities` | Booleano | La ciudad encontró correspondencia DIVIPOLA |
| `reference_temperature_c` | Decimal / °C | Referencia ilustrativa de 18 °C; `thermal_parameters` |
| `parameter_scope` | Texto | `academic_illustration`; `thermal_parameters` |
| `matched_thermal` | Booleano | La ciudad encontró referencia térmica |
| `day_period` | Texto | `madrugada`, `manana`, `tarde` o `noche`; `hour_bands` |
| `matched_hours` | Booleano | La hora encontró clasificación en el catálogo |
| `radiation_kwh_m2_day` | Decimal / kWh/m²/día | `shortwave_radiation_sum_mj_m2 / 3.6` |
| `daylight_hours` | Decimal / h | `daylight_seconds / 3600` |
| `sunshine_hours` | Decimal / h | `sunshine_seconds / 3600` |
| `degrees_above_reference_c` | Decimal / °C | `max(temperature_c - reference_temperature_c, 0)` |
| `degrees_below_reference_c` | Decimal / °C | `max(reference_temperature_c - temperature_c, 0)` |
| `is_business_day` | Booleano | Fecha que no es festiva ni fin de semana según `calendar` |
| `enrichment_status` | Texto | `COMPLETE` cuando los seis cruces tienen correspondencia y sus campos están presentes; `INCOMPLETE` en otro caso |

Las diferencias térmicas se calculan sobre cada temperatura horaria. No son grados-día acumulados ni indicadores calibrados de consumo o confort. Las magnitudes solares diarias se repiten en las 24 horas de cada ciudad y fecha: deben deduplicarse a esa granularidad antes de sumar valores diarios.

### Correspondencia territorial

| `city_id` local | `city` | `municipality_code` | `department_code` | `divipola_year` |
|---:|---|---|---|---:|
| 1 | Barranquilla | `08001` | `08` | 2025 |
| 2 | Bogota | `11001` | `11` | 2025 |
| 3 | Bucaramanga | `68001` | `68` | 2024 |
| 4 | Cali | `76001` | `76` | 2025 |
| 5 | Medellin | `05001` | `05` | 2025 |

El año de Bucaramanga es el valor del registro recibido, aunque el servicio consultado se denomine DIVIPOLA MGN 2025. La elevación de GeoNames tampoco representa un promedio municipal o la altura de la celda meteorológica; las coordenadas de esa celda constan en el manifiesto de fuentes.

## 4. Valores ausentes y formatos de salida

Una falta de correspondencia no elimina la fila. Los campos externos y derivados que dependan de ella quedan ausentes y el estado pasa a `INCOMPLETE`. Una clave encontrada puede contener un valor ausente: `matched_* = True` confirma la unión, no la completitud de todo su contenido. No se imputan mediciones adicionales durante el enriquecimiento.

En la entrada, `imputed_fields` y `outlier_fields` admiten texto vacío con significado válido. Debe evitarse convertirlo automáticamente en nulo. El CSV exporta booleanos como `True`/`False` y las fechas horarias en ISO 8601 con desplazamiento. En Excel, las fechas son celdas sin zona: `observation_time` muestra la hora de Colombia y `observation_time_utc` la UTC; sus nombres y `timezone` permiten distinguirlas. Los códigos territoriales se mantienen como texto.

## 5. Cobertura de la muestra

[sample_coverage.csv](../src/static/auditoria/sample_coverage.csv) y la hoja `Cobertura` del Excel tienen seis campos:

| Campo | Significado |
|---|---|
| `city`, `year`, `month` | Identifican el estrato |
| `population_rows` | Número de horas del estrato en la base completa |
| `sample_rows` | Número de filas seleccionadas, máximo 20 |
| `sample_weight` | `population_rows / sample_rows`; peso de expansión de cada fila del estrato |

La muestra guardada contiene 1.200 filas, seleccionadas con semilla 42. Un promedio global sin pesos asignaría la misma participación a meses de distinta duración. El conjunto completo evita esa necesidad para el análisis descriptivo del año.
