# Metodología de enriquecimiento

## 1. Pregunta de trabajo y alcance

La base de EA2 organiza temperatura, humedad, precipitación, viento y energía sintética por ciudad y hora. Para comparar sus patrones entre fechas y lugares hacen falta atributos que permitan distinguir calendario, ubicación y condiciones solares. Esta actividad incorpora ese contexto y conserva un registro de cómo se obtuvo cada variable.

El trabajo se concentra en integración, control de calidad y generación de evidencias. El volumen de 43.800 filas cabe en memoria y permite usar Pandas. DuckDB representa el almacenamiento analítico de una plataforma cloud simulada; GitHub Actions aporta una ejecución automatizada en un runner. No se evalúan escalabilidad distribuida, ahorro energético o calidad de un modelo predictivo.

## 2. Recuperación de la base de EA2

Se utiliza el archivo completo `cleaned_full.csv`, no la muestra de 1.200 filas. La copia incluida mantiene el SHA-256 `e61e5770af3c2b895eedf0f1e5c1f2a2c2acb7825b68dc25969d39824b3894d6`. El [manifiesto de la base](../src/db/base_manifest.json) identifica el repositorio de origen y el commit `a4b8a1a5021b58104ca92b840533eb5bbf4170ed`.

`prepare_base.py` carga las 32 columnas en la tabla `cleaned_data` de una nueva base DuckDB. Interpreta explícitamente números, booleanos y fechas; conserva los textos vacíos de auditoría. Después compara todos los valores del CSV con la tabla y verifica que el archivo de origen permanezca intacto. La reconstrucción trabaja con la copia incluida en este proyecto.

La granularidad es una ciudad y una hora local. Cada una de las cinco ciudades tiene 8.760 registros entre el 1 de enero y el 31 de diciembre de 2025. El enriquecimiento lee la base en modo de solo lectura y vuelve a comprobar su hash al finalizar.

## 3. Selección y preparación de fuentes

Se preparan seis entradas en JSON, XLSX, CSV, HTML, XML y TXT. Cuatro contienen datos externos: geografía, calendario, variables solares y clasificación territorial. Provienen de Open-Meteo/GeoNames, Nager.Date y DANE. Las otras dos son catálogos propios de parámetros térmicos y franjas horarias.

Las respuestas originales de las APIs se guardan en `src/sources/raw/`. `prepare_sources.py` puede reconstruir los formatos de integración a partir de esas respuestas sin una nueva consulta. El manifiesto registra URLs, consulta UTC, licencias, hashes y transformaciones; [FUENTES.md](FUENTES.md) desarrolla la atribución.

| Fuente | Decisión de preparación |
|---|---|
| Geografía | Seleccionar la coincidencia de Colombia cercana a la coordenada de EA2; conservar identificador y elevación del punto GeoNames |
| Calendario | Expandir a 365 fechas y agrupar festividades que coinciden: 18 registros originales corresponden a 17 fechas festivas |
| Solar | Consultar todo 2025 con `models=era5` y `America/Bogota`; preservar las unidades y metadatos de rejilla |
| DIVIPOLA | Preparar HTML a partir de JSON oficial; mantener códigos como texto y el año de cada registro |
| Parámetros térmicos | Fijar 18 °C como referencia ilustrativa común, identificada como elaboración académica |
| Franjas horarias | Clasificar 00–05, 06–11, 12–17 y 18–23 como madrugada, mañana, tarde y noche |

La conversión a formatos distintos permite demostrar su lectura e integración, pero no crea proveedores independientes. El catálogo térmico tampoco aporta una medición nueva.

## 4. Validación y cruce

Antes de integrar, se validan los hashes de las seis fuentes, sus columnas requeridas y la unicidad de sus claves. Se comprueban códigos territoriales, horas de 0 a 23, valores numéricos finitos, magnitudes solares no negativas y duraciones coherentes. La base debe tener clave ciudad–hora única y componentes temporales compatibles con `America/Bogota`.

La clave auxiliar de ciudad elimina diferencias de tildes, mayúsculas y espacios; `city` permanece igual. La fecha diaria se deriva después de convertir la observación a la zona de Colombia. Esta secuencia evita asignar las últimas horas locales al día UTC siguiente.

Cada integración utiliza `left merge` con validación `many_to_one`. Así, la tabla base conserva sus filas y una clave duplicada en el catálogo produce un error explícito. Por fuente se cuentan registros antes y después, coincidencias, claves sin correspondencia, claves externas sin uso y celdas adicionales ausentes. No se imputan nuevos datos meteorológicos. Una fila incompleta se conserva y queda marcada para revisión.

Al concluir los seis cruces se ordena por `source_row` y se comparan las 32 columnas originales con la entrada. La comprobación exige igualdad de valores y evita que un enriquecimiento cambie silenciosamente el resultado de la limpieza.

## 5. Variables derivadas

La radiación se divide entre 3,6 para convertir MJ/m²/día a kWh/m²/día. Las duraciones solares se dividen entre 3.600 para expresarlas en horas. Se calculan diferencias no negativas respecto a la referencia térmica y una marca de lunes a viernes no festivo. El [diccionario](DICCIONARIO_DATOS.md) contiene las fórmulas y los tipos de las 63 columnas.

El estado `COMPLETE` exige correspondencia en las seis fuentes y presencia de todos sus atributos. Este control detecta integración incompleta; no implica ausencia de sesgo o exactitud absoluta de los datos.

## 6. Evidencias, muestra y automatización

El archivo completo se exporta a `src/data/enriched_full.csv`. Para facilitar la revisión se seleccionan hasta 20 filas por ciudad, año y mes, con semilla 42: en esta base son 60 estratos y 1.200 filas. La misma muestra se entrega en CSV y XLSX. La cuota asegura presencia de todos los estratos, pero no conserva automáticamente sus proporciones; `sample_coverage.csv` registra los pesos de expansión.

`enriched_report.txt` describe operaciones y limitaciones. `integration_summary.json` guarda métricas y hashes; una copia del manifiesto de fuentes acompaña cada auditoría. El workflow ejecuta pruebas, enriquecimiento y verificación después de retirar las salidas conocidas del runner, de modo que los artefactos correspondan a la ejecución actual. Además, compara el hash de la base antes y después.

La ejecución guardada conserva 43.800 filas, aumenta de 32 a 63 columnas, presenta cero duplicados ciudad–hora y cero filas incompletas. Los resultados detallados se consultan en [integration_summary.json](../src/static/auditoria/integration_summary.json). Los logs de cada ejecución automatizada permiten comprobar por separado el estado de sus pruebas y validaciones.

## 7. Condiciones para el análisis posterior

`energy_kwh` es sintética y depende parcialmente de las variables meteorológicas originales. Una asociación entre ambas puede reflejar su fórmula de generación. No debe interpretarse como respuesta observada de una red eléctrica o como evidencia causal.

Las magnitudes solares representan el día completo y se repiten en sus 24 horas. Para sumar radiación o duración diaria debe trabajarse con una fila por ciudad y fecha. Para pronosticar dentro de ese mismo día habría que usar variables disponibles en el momento del pronóstico, por ejemplo rezagos válidos, en lugar del agregado final del día.

Los z-scores de EA2 se ajustaron con todo 2025. Antes de entrenar un modelo se requiere separar temporalmente entrenamiento y evaluación y recalcular las transformaciones con datos de entrenamiento. También debe revisarse la disponibilidad temporal de cada atributo y evitar que la muestra estratificada sustituya esa partición.

La extracción meteorológica original no fijó el modelo; la nueva fuente solar fija ERA5. Ambas usan productos meteorológicos en rejilla y no acreditan observaciones de una estación urbana. La elevación GeoNames describe un punto geográfico. El calendario es una referencia comunitaria, y `is_business_day` no reemplaza reglas laborales sectoriales. Estas limitaciones acompañan el conjunto para que su reutilización conserve el contexto de la actividad.
