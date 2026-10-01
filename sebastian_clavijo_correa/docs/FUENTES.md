# Fuentes y procedencia de los datos

Para el enriquecimiento usé seis archivos: algunos tienen una fila por ciudad, otros por fecha o por hora. Cuatro contienen datos de Open-Meteo, Nager.Date y DANE. Los otros dos son catálogos que preparé para el ejercicio. En total se trabajó con seis formatos y tres proveedores externos.

Las respuestas originales se descargaron el 22 de septiembre de 2026, hora de Colombia, correspondiente al 23 de septiembre en UTC. Las fechas exactas de consulta, URL completas, parámetros, número de filas y huellas SHA-256 están en [`source_manifest.json`](../src/sources/source_manifest.json). El conjunto meteorológico abarca 2025; su periodo de observación es diferente de la fecha en que se descargó.

## 1. Archivos que consume el proceso

| Archivo | Filas y unidad de registro | Claves de cruce | Información que aporta |
|---|---|---|---|
| `city_geography.json` | 5 ciudades | `city` | País, identificador GeoNames y elevación del punto geográfico. |
| `calendar_2025.xlsx` | 365 fechas, una fila por día local | `local_date` | Festivo nacional, nombre y fin de semana. Se lee la hoja `calendar`. |
| `solar_daily_2025.csv` | 1.825 días-ciudad, 365 por ciudad | `city`, `local_date` | Radiación solar diaria y duración de luz y sol. |
| `municipalities.html` | 5 municipios | `city` | Códigos y nombres oficiales del municipio y departamento. Se lee la tabla `divipola`. |
| `thermal_parameters.xml` | 5 parámetros, uno por ciudad | `city` | Referencia térmica de 18 °C para una transformación ilustrativa. |
| `hour_bands.txt` | 24 horas locales | `hour` | Clasificación académica en madrugada, mañana, tarde y noche. Es un TXT delimitado por tabulaciones. |

Las claves diarias y horarias se calculan en `America/Bogota`. No se cruza directamente la fecha UTC: las últimas horas locales del 31 de diciembre de 2025 pertenecen al 1 de enero de 2026 en UTC. Cada catálogo debe tener una sola fila por clave para evitar que un cruce multiplique los registros de la base. Las definiciones de las columnas finales se encuentran en el diccionario del proyecto.

## 2. Open-Meteo y GeoNames

### Ubicación de las ciudades

Se consultó la [API de geocodificación de Open-Meteo](https://open-meteo.com/en/docs/geocoding-api), cuyos datos de localización proceden de [GeoNames](https://www.geonames.org/export/). La consulta filtra Colombia. Cuando aparecen lugares con el mismo nombre, el script elige la coincidencia más cercana a las coordenadas usadas en la Actividad 2. El nombre Santiago de Cali se corresponde explícitamente con `Cali` en la base.

Se conservan `country_code`, `geoname_id` y `elevation_m`. Este último describe el punto devuelto por el geocodificador. No es la elevación promedio del municipio ni la elevación del punto de rejilla meteorológica. Por ejemplo, la respuesta guardada informa 758 metros para el punto de Cali; el valor se conserva con su significado y procedencia. La población recibida en algunas respuestas no se integra porque la API no indica su fecha de referencia.

### Variables solares

La [API histórica de Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) se consultó para las cinco ciudades, del 1 de enero al 31 de diciembre de 2025, con `models=era5` y `timezone=America/Bogota`. Los datos provienen de reanálisis en una rejilla. No deben presentarse como mediciones de una estación instalada en cada ciudad.

Las variables originales `shortwave_radiation_sum`, `daylight_duration` y `sunshine_duration` se renombran para que las unidades queden visibles: MJ/m² y segundos. Las coordenadas solicitadas y las devueltas por la rejilla se guardan en `solar_grid_metadata` dentro del manifiesto. No son necesariamente iguales. La consulta de enriquecimiento fija ERA5; la extracción original de la Actividad 1 no fijó el modelo. Por esa diferencia no se asume que ambas etapas usen el mismo producto meteorológico. Se conservan los datos del clima que ya estaban en la base limpia.

Estos son **agregados del día completo**. Sirven para describir lo ocurrido, pero no estaban disponibles al comenzar ese día. Si en una actividad posterior se pronostica demanda, usarlos para predecir las primeras horas del mismo día introduciría información del futuro. Haría falta excluirlos, rezagarlos según la disponibilidad real del proveedor o utilizar pronósticos emitidos antes del momento de predicción. El enriquecimiento por sí solo no resuelve esa decisión de modelado.

**Uso y atribución.** Open-Meteo ofrece sus datos de API bajo [CC BY 4.0](https://open-meteo.com/en/licence). Se mantiene el crédito a Open-Meteo, GeoNames y, para ERA5, ECMWF/Copernicus Climate Change Service. Se documentan los cambios de formato y de nombres de columna. La licencia de los datos es distinta de la licencia AGPL del código de Open-Meteo y de las condiciones de acceso a su servicio.

## 3. Calendario de Nager.Date

Se guardó la respuesta de [festivos públicos de Colombia en 2025](https://date.nager.at/api/v3/PublicHolidays/2025/CO). El script conserva las festividades nacionales de tipo `Public` y prepara un calendario de 365 días.

La respuesta contiene **18 festividades en 17 fechas diferentes**. El 30 de junio coinciden Sagrado Corazón y San Pedro y San Pablo. Se guardan ambos nombres en la misma fila, separados por punto y coma; no se crean dos filas para esa fecha. Las fechas restantes se marcan como `No festivo`. `is_weekend` se calcula a partir del día de la semana y puede coexistir con `is_holiday`.

Es un calendario comunitario. No representa horarios de trabajo, tarifas eléctricas ni excepciones por sector económico. Los nombres de festividades conservan el contenido de la respuesta. Cualquier aplicación normativa requeriría contrastar el calendario con la autoridad competente.

**Uso.** Los [términos del servicio](https://nagerholidays.com/legal/termsofservice) permiten proyectos privados o sin ánimo de lucro; para fines comerciales requieren patrocinio activo y prohíben usar la información para operar un portal propio de festivos. Esta actividad usa una copia pequeña como variable de contexto de un proyecto académico. La licencia MIT del repositorio Nager.Date corresponde al software y no se presenta como una licencia general de todos los datos de la API.

## 4. Municipios y departamentos del DANE

La fuente es el servicio oficial [DIVIPOLA MGN 2025, capa Municipio 317](https://portalgis.dane.gov.co/mparcgis/rest/services/Divipola/Serv_DIVIPOLA_MGN_2025/FeatureServer/317). La consulta solicita cinco códigos: `08001`, `11001`, `68001`, `76001` y `05001`. La respuesta JSON original permanece en el repositorio. A partir de ella se prepara la tabla HTML exigida por la actividad. Por tanto, el HTML es una adaptación del proyecto y no una página descargada como tal del DANE.

Los códigos se tratan como texto para conservar sus ceros iniciales. `city_id` pertenece al sistema local de la Actividad 1 y no es un código DIVIPOLA. La asociación explícita entre ambas nomenclaturas evita esa confusión.

Aunque el nombre del servicio indica MGN 2025, su campo `MPIO_NANO` devuelve **2024 para Bucaramanga** y 2025 para las otras cuatro ciudades. El proyecto conserva ese valor en `divipola_year`; no lo cambia por el año del servicio ni lo interpreta como fecha de descarga.

**Uso y atribución.** El [Geoportal DANE](https://geoportal.dane.gov.co/acerca-del-geoportal/licencia-y-condiciones-de-uso/) publica sus condiciones de descarga, adaptación y atribución bajo Creative Commons, con referencia a CC BY 4.0. Se conserva el crédito: Departamento Administrativo Nacional de Estadística - DANE, [www.dane.gov.co](https://www.dane.gov.co). Los cambios aplicados son selección de filas, equivalencia de nombres, renombramiento de campos y conversión a HTML.

## 5. Catálogos elaborados para el ejercicio

`thermal_parameters.xml` asigna 18 °C a cada ciudad y lo identifica mediante `parameter_scope=academic_illustration`. Es una referencia elegida para demostrar un cruce y calcular diferencias térmicas. No es una norma, una medición ni un umbral de confort calibrado. La diferencia respecto de esa referencia no prueba consumo energético ni una relación causal.

`hour_bands.txt` clasifica las horas locales de 00 a 05 como `madrugada`, de 06 a 11 como `manana`, de 12 a 17 como `tarde` y de 18 a 23 como `noche`. Son intervalos definidos para la actividad. No se presentan como franjas tarifarias ni como una clasificación oficial de demanda.

Ambos catálogos se elaboraron para este proyecto. En el manifiesto aparecen como `type=authored_catalog`; al ser archivos propios, no tienen una URL ni una fecha de consulta externa.

## 6. Respuestas originales y reproducción

La carpeta `src/sources/raw/` contiene **12 respuestas originales**:

- Cinco consultas de geocodificación, una por ciudad.
- Cinco consultas de variables solares, una por ciudad.
- Una consulta de festivos de Colombia.
- Una consulta de los cinco municipios del DANE.

`retrieval_manifest.json` es un archivo de metadatos adicional, no una decimotercera fuente. Registra la URL solicitada, la URL de respuesta, el estado HTTP, la fecha UTC y la huella de cada respuesta. El manifiesto principal agrega las huellas de los seis archivos preparados. Las respuestas se conservaron sin reescribir su contenido.

Desde `sebastian_clavijo_correa`, después de instalar las dependencias del proyecto:

```bash
# Reconstruir usando solo las respuestas incluidas en el repositorio.
python scripts/prepare_sources.py

# Consultar las APIs nuevamente y reemplazar las respuestas y fuentes preparadas.
python scripts/prepare_sources.py --fetch
```

La primera opción no accede a Internet. Antes de preparar los archivos, comprueba las huellas de las respuestas originales. La segunda opción es una actualización explícita: puede devolver datos distintos, fallar si un proveedor cambia su API y modifica el manifiesto. Después de actualizar, se deben ejecutar nuevamente el enriquecimiento y las pruebas y revisar las diferencias antes de publicar cambios. GitHub Actions usa las fuentes incluidas en el repositorio y no ejecuta `--fetch`.

Las huellas de los archivos preparados pueden comprobarse con:

```bash
python -c "import hashlib,json; from pathlib import Path; p=Path('src/sources'); m=json.loads((p/'source_manifest.json').read_text(encoding='utf-8')); assert all(hashlib.sha256((p/s['path']).read_bytes()).hexdigest()==s['sha256'] for s in m['sources']); print('Huellas correctas')"
```

Se comprobó la reconstrucción bloqueando las llamadas de red durante la prueba. Los seis archivos preparados conservaron sus huellas. En el XLSX se fijan las fechas internas del contenedor para evitar cambios de hash causados únicamente por la hora de guardado; esas fechas técnicas no sustituyen las fechas reales de consulta del manifiesto. La comparación binaria corresponde a las dependencias utilizadas en esta entrega. Un cambio de versión de una biblioteca puede modificar la serialización sin cambiar los datos, por lo que también deben revisarse filas, claves, tipos y valores.
