"""Genera el informe y sus diagramas a partir del modelo ya verificado."""

from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
W, H = 595.28, 841.89
M = 48
WIDTH = W - M * 2
NAVY = colors.HexColor("#19344B")
TEAL = colors.HexColor("#176B72")
PALE = colors.HexColor("#EDF4F6")
TEXT = colors.HexColor("#243746")
BODY = ParagraphStyle(
    "body",
    fontName="Helvetica",
    fontSize=10.4,
    leading=15,
    textColor=TEXT,
    alignment=TA_JUSTIFY,
    spaceAfter=9,
)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.4, leading=11, alignment=0)
CELL = ParagraphStyle("cell", parent=SMALL, fontSize=8, leading=10)
HEAD = ParagraphStyle(
    "head",
    parent=BODY,
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=17,
    textColor=NAVY,
    alignment=0,
)
TITLE = ParagraphStyle("title", parent=HEAD, fontSize=22, leading=27)


class Report:
    def __init__(self, path):
        self.pdf = canvas.Canvas(str(path), pagesize=(W, H))
        self.pdf.setTitle("Arquitectura y modelo de datos del proyecto integrador")
        self.pdf.setAuthor("Juan Sebastian Clavijo Correa")
        self.page = 0
        self.y = H - M
        self.transcript = []

    def new(self, title, subtitle=""):
        if self.page:
            self.pdf.showPage()
        self.page += 1
        self.y = H - M
        c = self.pdf
        c.setFillColor(TEAL)
        c.rect(M, H - 30, WIDTH, 3, fill=1, stroke=0)
        c.setFont("Helvetica", 8)
        c.setFillColor(TEXT)
        c.drawString(M, 25, "INFRA BIG DATA  /  JUAN SEBASTIAN CLAVIJO CORREA")
        c.drawRightString(W - M, 25, str(self.page))
        self.para(title, TITLE)
        if subtitle:
            self.para(subtitle, SMALL)
        self.y -= 8

    def para(self, text, style=BODY):
        item = Paragraph(text, style)
        _, height = item.wrap(WIDTH, 720)
        if self.y - height < 47:
            raise ValueError(f"Página {self.page} desbordada: {text[:70]}")
        item.drawOn(self.pdf, M, self.y - height)
        self.y -= height + style.spaceAfter
        self.transcript.append(re.sub("<[^>]+>", "", text))

    def sub(self, text):
        self.para(text, HEAD)

    def table(self, rows, widths=None):
        data = [[Paragraph(escape(str(v)), CELL) for v in row] for row in rows]
        t = Table(data, colWidths=widths or [WIDTH / len(rows[0])] * len(rows[0]))
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PALE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.7, TEAL),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#D1DDE1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        _, height = t.wrap(WIDTH, 700)
        if self.y - height < 47:
            raise ValueError(f"Tabla desbordada en página {self.page}")
        t.drawOn(self.pdf, M, self.y - height)
        self.y -= height + 12

    def diagram(self, kind, height):
        self.pdf.saveState()
        self.pdf.translate(M, self.y - height)
        draw_diagram(self.pdf, kind)
        self.pdf.restoreState()
        self.y -= height + 12


def diagram_data(kind):
    if kind == "arquitectura":
        nodes = [
            (
                "api",
                8,
                286,
                150,
                65,
                "API Open-Meteo",
                "Extracción histórica EA1|5 JSON horarios de 2025",
            ),
            (
                "raw",
                174,
                286,
                150,
                65,
                "Respuestas archivadas",
                "JSON + SHA-256|Replay sin red en CI",
            ),
            ("ing", 340, 286, 150, 65, "ingestion.py", "Pandas + NumPy|Energía sintética / DuckDB"),
            (
                "clean",
                340,
                173,
                150,
                70,
                "cleaning.py",
                "Hechos + dimensiones|32 columnas / auditoría",
            ),
            (
                "enrich",
                174,
                173,
                150,
                70,
                "enrichment.py",
                "6 cruces LEFT N:1|63 columnas / auditoría",
            ),
            (
                "source",
                8,
                173,
                150,
                70,
                "Fuentes complementarias",
                "JSON, XLSX, CSV|XML, HTML, TXT",
            ),
            (
                "sql",
                174,
                58,
                150,
                70,
                "model.py + SQLite",
                "6 tablas con PK / FK|Vista enriched_data",
            ),
            (
                "out",
                340,
                58,
                150,
                70,
                "Evidencias",
                "CSV y XLSX / 1.200 filas|PDF, SQL, logs y artefacto",
            ),
        ]
        edges = [
            ("api", "raw"),
            ("raw", "ing"),
            ("ing", "clean"),
            ("clean", "enrich"),
            ("source", "enrich"),
            ("enrich", "sql"),
            ("sql", "out"),
        ]
    else:
        nodes = [
            ("city", 8, 302, 200, 75, "dim_city  /  5", "PK city_id|Ciudad, coordenadas, DIVIPOLA"),
            ("date", 289, 302, 200, 75, "dim_date  /  365", "PK local_date|Calendario y festivos"),
            (
                "solar",
                8,
                164,
                200,
                90,
                "fact_solar_day  /  1.825",
                "PK (city_id, local_date)|FK ciudad y fecha|Radiación y duración del día",
            ),
            (
                "time",
                289,
                164,
                200,
                90,
                "dim_time  /  8.760",
                "PK time_id|FK local_date, hour|Instantes local y UTC",
            ),
            (
                "fact",
                8,
                23,
                200,
                90,
                "fact_hourly  /  43.800",
                "PK source_row|FK city_id, time_id|UNIQUE (city_id, time_id)",
            ),
            ("hour", 289, 23, 200, 90, "dim_hour  /  24", "PK hour|Franja horaria"),
        ]
        edges = [
            ("city", "solar"),
            ("date", "time"),
            ("hour", "time"),
            ("time", "fact"),
            ("city", "fact"),
            ("date", "solar"),
        ]
    return nodes, edges


def draw_diagram(c, kind):
    nodes, edges = diagram_data(kind)
    lookup = {n[0]: n for n in nodes}

    def arrow(points, label=""):
        c.setStrokeColor(TEAL)
        c.setLineWidth(1.1)
        p = c.beginPath()
        p.moveTo(*points[0])
        for pt in points[1:]:
            p.lineTo(*pt)
        c.drawPath(p)
        import math

        x, y = points[-1]
        a = math.atan2(y - points[-2][1], x - points[-2][0])
        size = 5
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x - size * math.cos(a - 0.5), y - size * math.sin(a - 0.5))
        p.lineTo(x - size * math.cos(a + 0.5), y - size * math.sin(a + 0.5))
        p.close()
        c.setFillColor(TEAL)
        c.drawPath(p, fill=1)
        if label:
            c.setFont("Helvetica", 8)
            c.drawString(points[0][0] + 4, points[0][1] - 14, label)

    for a, b in edges:
        _, x, y, w, h, *_ = lookup[a]
        _, xx, yy, ww, hh, *_ = lookup[b]
        if kind == "er" and a == "city" and b == "fact":
            points = [(x, y + h / 2), (0, y + h / 2), (0, yy + hh / 2), (xx, yy + hh / 2)]
        elif kind == "er" and a == "date" and b == "solar":
            points = [(x, y + h / 2), (247, y + h / 2), (247, yy + hh / 2), (xx + ww, yy + hh / 2)]
        elif kind == "er" and a == "time" and b == "fact":
            points = [(x, y + 12), (255, y + 12), (255, yy + hh / 2), (xx + ww, yy + hh / 2)]
        elif abs(y - yy) < 10:
            points = (
                [(x + w, y + h / 2), (xx, yy + hh / 2)]
                if xx > x
                else [(x, y + h / 2), (xx + ww, yy + hh / 2)]
            )
        elif yy < y:
            points = [(x + w / 2, y), (xx + ww / 2, yy + hh)]
        else:
            points = [(x + w / 2, y + h), (xx + ww / 2, yy)]
        arrow(points)
    for _, x, y, w, h, title, body in nodes:
        c.setFillColor(PALE)
        c.setStrokeColor(TEAL)
        c.roundRect(x, y, w, h, 5, fill=1)
        c.setFont("Helvetica-Bold", 9.1)
        c.setFillColor(NAVY)
        c.drawString(x + 8, y + h - 17, title)
        c.setFont("Helvetica", 8.4)
        for i, line in enumerate(body.split("|")):
            c.drawString(x + 8, y + h - 33 - i * 12, line)
    if kind == "er":
        c.setFillColor(TEAL)
        c.setFont("Helvetica", 8)
        for x, y in [(113, 280), (395, 280), (395, 137), (260, 145), (5, 132), (226, 276)]:
            c.drawString(x, y, "1:N")
    if kind == "arquitectura":
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 8.4)
        c.drawString(
            8,
            20,
            "GitHub Actions ejecuta la cadena en un runner y conserva los resultados durante 30 días.",
        )


def save_diagrams():
    directory = DOCS / "diagramas"
    directory.mkdir(exist_ok=True)
    for kind, height in [("arquitectura", 365), ("er", 390)]:
        cv = canvas.Canvas(str(directory / f"{kind}.pdf"), pagesize=(WIDTH, height))
        draw_diagram(cv, kind)
        cv.save()
        nodes, edges = diagram_data(kind)
        mx = ET.Element("mxfile", host="app.diagrams.net")
        dia = ET.SubElement(mx, "diagram", name=kind)
        graph = ET.SubElement(dia, "mxGraphModel")
        root = ET.SubElement(graph, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        for ident, x, y, w, h, title, body in nodes:
            node = ET.SubElement(
                root,
                "mxCell",
                id=ident,
                value=title + "\n" + body.replace("|", "\n"),
                style="rounded=1;whiteSpace=wrap;html=0;fillColor=#EDF4F6;strokeColor=#176B72;",
                vertex="1",
                parent="1",
            )
            ET.SubElement(
                node,
                "mxGeometry",
                x=str(x * 2),
                y=str((height - y - h) * 2),
                width=str(w * 2),
                height=str(h * 2),
                attrib={"as": "geometry"},
            )
        for i, (a, b) in enumerate(edges):
            node = ET.SubElement(
                root,
                "mxCell",
                id="e" + str(i),
                source=a,
                target=b,
                value="1:N" if kind == "er" else "",
                edge="1",
                parent="1",
                style="edgeStyle=orthogonalEdgeStyle;endArrow=block;html=0;",
            )
            ET.SubElement(node, "mxGeometry", relative="1", attrib={"as": "geometry"})
        ET.ElementTree(mx).write(
            directory / f"{kind}.drawio", encoding="utf-8", xml_declaration=True
        )


def field_descriptions():
    result = {}
    for line in (DOCS / "DICCIONARIO_DATOS.md").read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| `([^`]+)` \| (.*?) \| (.*?) \|", line)
        if match:
            result[match[1]] = match[3].replace("`", "").replace("\\", "")
    return result


def build():
    catalog = json.loads(
        (ROOT / "src/static/auditoria/model_validation.json").read_text(encoding="utf-8")
    )
    save_diagrams()
    r = Report(DOCS / "arquitectura_modelo.pdf")
    r.new(
        "Arquitectura y modelo de datos", "Proyecto integrador | Documentación técnica y académica"
    )
    r.y -= 55
    r.para("Meteorología y energía sintética en cinco ciudades de Colombia", TITLE)
    r.y -= 20
    r.para("<b>Juan Sebastian Clavijo Correa</b>")
    r.para(
        "Institución Universitaria Digital de Antioquia<br/>Infraestructura y Arquitectura para Big Data<br/>30 de septiembre de 2026"
    )
    r.y -= 28
    r.table(
        [
            ["Aspecto revisado", "Resultado"],
            ["Periodo y unidad de registro", "2025 completo; una ciudad por hora local"],
            ["Integración", "43.800 filas; 32 columnas limpias y 63 enriquecidas"],
            ["Modelo final", "SQLite: 6 tablas y una vista de reconstrucción"],
            ["Herramientas de las fases previas", "DuckDB de EA1, Pandas y GitHub Actions"],
        ],
        [150, WIDTH - 150],
    )
    r.para(
        "En este trabajo reúno la ingesta, la limpieza y el enriquecimiento que desarrollé durante el curso. Explico cómo se conectan los scripts, cómo quedan organizados los datos y qué comprobaciones hice. La variable de energía fue simulada para el ejercicio; por eso no la uso para sacar conclusiones sobre el consumo eléctrico real ni sobre su relación con el clima."
    )
    r.para(
        'Repositorio: <link href="https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos" color="#176B72">JSebastianCCorrea/documentacion_arquitectura_modelo_datos</link>',
        SMALL,
    )
    r.para(
        "Lectura: arquitectura (2), ingesta (3), limpieza (4), enriquecimiento (5), modelo ER (6), tablas y campos (7-10), herramientas (11), automatización (12), resultados y recomendaciones (13), bibliografía (14).",
        SMALL,
    )

    r.new("1. Visión global de la arquitectura")
    r.para(
        "El proyecto trabaja con datos del clima de Medellín, Bogotá, Cali, Barranquilla y Bucaramanga, registrados por hora durante 2025. A esos datos les agregué una variable de energía simulada. La idea es tener una base organizada para revisar diferencias entre ciudades, fechas y horas. Con este tamaño puedo ejecutar todo en un computador y comprobar cada paso."
    )
    r.diagram("arquitectura", 365)
    r.para(
        "<b>Figura 1.</b> Flujo completo. Elaboración propia a partir de los scripts del repositorio. El tramo API-JSON corresponde a la extracción de EA1; la ejecución automatizada actual comienza en las respuestas archivadas.",
        SMALL,
    )
    r.para(
        "El proceso tiene cuatro pasos: leer los datos de entrada, limpiarlos, agregar información de otras fuentes y guardar el resultado en SQLite. Cada paso deja un reporte para revisar qué ocurrió. Conservo los archivos originales para poder repetir el proceso y encontrar de dónde sale cada dato."
    )
    r.para(
        "Esta entrega retoma el trabajo de ingesta de EA1, la limpieza de EA2 y el enriquecimiento guardado en actividad_4. Aquí los reúno en un solo proceso y explico el modelo final de datos."
    )

    r.new("2. Ingesta y origen de los datos")
    r.sub("2.1 Extracción realizada en EA1")
    r.para(
        "En EA1, el script consultó Historical Weather API de Open-Meteo con requests.get. Usó las coordenadas de cada ciudad, el periodo del 1 de enero al 31 de diciembre de 2025 y la zona America/Bogota. Solicitó temperature_2m, relative_humidity_2m, precipitation y wind_speed_10m, y guardó cada respuesta en JSON. Son datos meteorológicos modelados. Como esa consulta no fijó el parámetro models, no puedo asegurar que todos provengan de ERA5 (Open-Meteo, s. f.)."
    )
    r.para(
        "Las coordenadas de la base son las que se enviaron en la consulta. El proveedor puede responder con las de una celda cercana de su malla meteorológica. Los JSON originales permiten revisar esa diferencia y las unidades de cada variable."
    )
    r.sub("2.2 Simulación de energía y carga analítica")
    r.para(
        "Para simular la energía en EA1, usé valores base de 110, 130, 115, 125 y 100 para Medellín, Bogotá, Cali, Barranquilla y Bucaramanga. Cada valor se multiplicó por un factor horario: 1,25 entre las 18 y las 21 h, 1,15 entre las 7 y las 9 h, y 1 en las demás horas. También se aplicaron los factores 1 + |T - 22| × 0,015 y 1 + precipitación × 0,005, más un ruido normal con media 1 y desviación 0,05. La semilla 42 de NumPy permite repetir la simulación; el resultado se redondea a dos decimales."
    )
    r.para(
        "Los datos se guardaron primero en staging_weather y luego se organizaron en dim_city, dim_time y fact_weather_energy. En EA1, CREATE TABLE AS creó las tablas sin declarar claves primarias o foráneas. Por eso, antes de unirlas, el script de limpieza revisa que las claves no se repitan y que cada referencia tenga su ciudad y su hora."
    )
    r.table(
        [
            ["Tabla de EA1 (DuckDB)", "Filas", "Función"],
            ["staging_weather", "43.800", "Carga inicial: 11 columnas"],
            ["dim_city", "5", "Identificador local y coordenadas"],
            ["dim_time", "8.760", "Una hora por fila"],
            ["fact_weather_energy", "43.800", "Ciudad/hora, meteorología y energía sintética"],
        ],
        [180, 55, WIDTH - 235],
    )
    r.sub("2.3 Reproducción en esta entrega")
    r.para(
        "En esta entrega, src/ingestion.py comprueba la huella SHA-256 de los cinco JSON y vuelve a generar los datos sin conectarse a Internet. Mantiene el orden de ciudades y horas para obtener la misma energía simulada. Comparo cada valor con src/db/ingestion.db, que es una copia de analytics.duckdb de EA1 y sigue usando DuckDB. El código original está en docs/antecedentes/ingesta_ea1_original.py."
    )

    r.new("3. Preprocesamiento y limpieza")
    r.para(
        "Para la limpieza mantuve las reglas de EA2 en src/cleaning.py. El script lee la base sin modificarla, revisa las claves y ordena los registros por ciudad y hora. Asigna source_row para identificar cada fila, unifica la escritura de los nombres de ciudad y convierte los campos al tipo que corresponde."
    )
    r.table(
        [
            ["Control", "Decisión aplicada"],
            [
                "Clave ciudad-hora",
                "Se eliminan duplicados exactos. Si una clave ciudad-hora tiene valores contradictorios, se rechazan todas sus versiones.",
            ],
            [
                "Valores ausentes",
                "Se descartan claves inválidas. Los valores que se pueden completar usan la mediana de su ciudad, año y mes. Si falta lluvia o no hay datos válidos para calcular la mediana, se rechaza la fila.",
            ],
            [
                "Rangos físicos",
                "Latitud, longitud, humedad y medidas no negativas se validan antes de aceptar un registro.",
            ],
            [
                "Atípicos",
                "Regla IQR por ciudad: marcas de revisión, sin recortar ni borrar automáticamente.",
            ],
            [
                "Zona horaria",
                "Interpretación local America/Bogota y columna adicional observation_time_utc.",
            ],
            [
                "Transformaciones",
                "Z-score de temperatura y energía por ciudad, humedad/100 y log1p de precipitación.",
            ],
        ],
        [113, WIDTH - 113],
    )
    r.sub("3.1 Resultado de la limpieza")
    r.para(
        "Al revisar la entrada encontré 43.800 filas sin datos nulos ni duplicados. Por eso, en esta ejecución no fue necesario eliminar filas ni completar valores faltantes. Sí quedaron 6.240 filas con alguna marca de dato atípico. Las conservé para poder revisarlas, ya que una marca estadística por sí sola no demuestra que el dato esté mal."
    )
    r.para(
        "El CSV limpio tiene 32 columnas y coincide byte a byte con la salida de EA2. También se guardan muestras CSV y XLSX de 1.200 filas: hasta 20 por ciudad, año y mes, con semilla 42. El reporte de cobertura indica cuántas filas representa cada grupo y qué peso usar al calcular resultados con la muestra."
    )
    r.sub("3.2 Uso posterior de las variables")
    r.para(
        "Los z-scores y las marcas IQR se calcularon con todos los datos de 2025. Esto sirve para describir la base actual. Si después la uso para predecir, primero debo separar los datos por tiempo y calcular esas transformaciones solo con el conjunto de entrenamiento. En esta actividad no entrené modelos de predicción."
    )
    r.para(
        "Evidencias: src/static/auditoria/limpieza/cleaning_report.txt, cleaning_metrics.json, quality_profile.csv y rejected_records.csv. La copia histórica de auditoría de EA2 se conserva en ea2_original/ para distinguir el antecedente de la ejecución integrada.",
        SMALL,
    )

    r.new("4. Enriquecimiento de seis formatos")
    r.para(
        "Para enriquecer los datos uso el CSV limpio completo. Lo cargo en la tabla cleaned_data de cleaned.duckdb y lo leo con Pandas. Las seis fuentes están guardadas en el repositorio junto con las respuestas originales y los archivos que registran su origen y sus hashes. Elegí Pandas porque permite leer estos formatos y comprobar los cruces con merge (pandas development team, s. f.-a)."
    )
    r.table(
        [
            ["Archivo / formato", "Clave de cruce", "Filas fuente", "Aporte"],
            ["city_geography.json", "Ciudad normalizada", "5", "País, GeoNames y elevación"],
            ["calendar_2025.xlsx", "Fecha local", "365", "Festivo y fin de semana"],
            ["solar_daily_2025.csv", "Ciudad + fecha", "1.825", "Radiación y duración solar"],
            ["municipalities.html", "Ciudad normalizada", "5", "Códigos y nombres DANE"],
            ["thermal_parameters.xml", "Ciudad normalizada", "5", "Referencia académica 18 °C"],
            ["hour_bands.txt", "Hora local", "24", "Franja del día"],
        ],
        [164, 105, 58, WIDTH - 327],
    )
    r.para(
        'Los seis cruces usan LEFT JOIN y validate="many_to_one". Así conservo cada fila de la base y detengo el proceso si una fuente repite la clave que debería ser única. Para comparar nombres de ciudad creo una clave sin tildes, diferencias de mayúsculas ni espacios sobrantes; el nombre original se mantiene. Los cruces diarios usan la fecha de Colombia.'
    )
    r.para(
        "Las 43.800 filas encontraron datos en las seis fuentes y la cantidad de registros se mantuvo. Se agregaron 31 columnas, entre ellas los indicadores matched_*, las conversiones de unidades y el estado del enriquecimiento. Para pasar de MJ/m²/día a kWh/m²/día divido entre 3,6; para pasar de segundos a horas, entre 3.600. La referencia de 18 °C se usa como ejemplo de cálculo, sin tratarla como un indicador de confort validado."
    )
    r.sub("4.1 Origen de las fuentes y uso de los datos")
    r.para(
        "Usé cuatro conjuntos de datos externos de tres proveedores: Open-Meteo/GeoNames, Nager.Date y DANE. Los catálogos XML y TXT los preparé para el ejercicio. El HTML se generó a partir del JSON oficial del DANE. En el calendario, 18 festividades se agrupan en 17 fechas. Para Bucaramanga conservé el año DIVIPOLA 2024 que devuelve el servicio, aunque su nombre indique 2025."
    )
    r.para(
        "Cuando una fila no encuentra información en alguna fuente, enrichment.py la conserva con el estado INCOMPLETE y deja los campos faltantes sin completar. El paso a SQLite exige COMPLETE y se detiene si hay pendientes. Además, los datos solares describen el día completo: no se pueden usar para predecir una hora de ese mismo día antes de que esos datos estén disponibles."
    )

    r.new("5. Modelo lógico y relaciones")
    r.para(
        "Organicé el modelo en dos tablas de hechos y cuatro dimensiones. Una tabla guarda las mediciones por ciudad y hora; la otra, los datos solares por ciudad y día. Las dimensiones contienen la ciudad, la fecha, la hora y el instante de observación. Separé los datos diarios de los horarios para evitar sumar 24 veces una misma medida solar."
    )
    r.diagram("er", 390)
    r.para(
        "<b>Figura 2.</b> Modelo físico SQLite. Las flechas indican relación de padre a hijo 1:N. Cada hijo tiene una sola fila padre para la clave obligatoria. Elaboración propia; PK y FK corresponden al DDL ejecutado.",
        SMALL,
    )
    r.para(
        "fact_hourly se relaciona con dim_city y dim_time. A su vez, dim_time se relaciona con dim_date y dim_hour. fact_solar_day usa dim_city y dim_date. Para consultar todo junto, la vista enriched_data une los datos horarios y solares por ciudad y fecha, sin una clave foránea directa entre las dos tablas de hechos."
    )
    r.para(
        "model.py activa PRAGMA foreign_keys=ON y crea las tablas STRICT en una base temporal. Luego ejecuta foreign_key_check e integrity_check y compara las 63 columnas de la vista con el CSV. Solo reemplaza analytics.sqlite si todas las comprobaciones pasan. Las reglas NOT NULL, UNIQUE y CHECK también ayudan a detectar datos que no cumplen el esquema (SQLite, s. f.-a)."
    )

    descriptions = field_descriptions()

    def physical(name):
        info = catalog["tables"][name]
        r.sub(name + " | " + f"{info['rows']:,}".replace(",", ".") + " filas")
        rows = [["Campo", "Tipo / clave", "Descripción"]]
        for _, field, typ, nonnull, default, pk in info["columns"]:
            fk = any(item[3] == field for item in info["foreign_keys"])
            annotation = typ + (" / PK" if pk else "") + (" / FK" if fk else "")
            desc = descriptions.get(field, field)
            desc = desc.split(";")[0]
            if len(desc) > 120:
                desc = desc[:117] + "..."
            rows.append([field, annotation, desc])
        r.table(rows, [162, 69, WIDTH - 231])

    r.new("6. Tablas y campos: ciudad")
    r.para(
        "Los tipos de estas tablas se tomaron de la base creada mediante PRAGMA table_info. Todos los campos son NOT NULL. Los booleanos se guardan como INTEGER y solo aceptan 0 o 1. Los códigos territoriales se guardan como TEXT para conservar ceros iniciales, como en 05001. DICCIONARIO_DATOS.md incluye las unidades y la explicación completa de las 63 variables."
    )
    physical("dim_city")
    r.para(
        "city_id es el identificador que viene de EA1; municipality_code es el código DANE. city y municipality_code son únicos. Los códigos municipales deben tener cinco dígitos y los departamentales, dos. Esta tabla contiene las cinco ciudades del proyecto.",
        SMALL,
    )

    r.new("7. Tablas y campos: calendario y tiempo")
    physical("dim_date")
    physical("dim_hour")
    physical("dim_time")
    r.para(
        "Las fechas se guardan como texto ISO 8601. observation_time usa el desplazamiento -05:00; observation_time_utc guarda el mismo instante en UTC. timezone indica America/Bogota. SQLite no tiene un tipo TIMESTAMPTZ, que sí se usa en la tabla cleaned_data de DuckDB (SQLite, s. f.-b).",
        SMALL,
    )

    r.new("8. Tablas y campos: datos solares")
    physical("fact_solar_day")
    r.sub("8.1 Un registro solar por ciudad y día")
    r.para(
        "La clave primaria (city_id, local_date) permite guardar un solo registro solar por ciudad y día. Antes de separar estos datos, model.py comprueba que las 24 filas horarias de cada día tengan los mismos valores solares. Si encuentra diferencias, detiene el proceso; si coinciden, guarda una sola fila diaria."
    )
    r.para(
        "Para sumar la radiación del año uso fact_solar_day y agrupo por city_id. En la vista enriched_data, el valor diario aparece en cada hora, así que sumarlo allí duplicaría la medida. La energía sintética sí está calculada por hora y se puede sumar por periodos, recordando que sigue siendo una simulación."
    )
    r.sub("8.2 Integridad del dato diario")
    r.para(
        "Las reglas CHECK exigen radiación igual o mayor que cero, luz diaria entre 0 y 86.400 segundos, y horas de sol que no superen la duración de la luz. Las dos claves foráneas comprueban que existan la ciudad y la fecha. Guardo también las conversiones a horas y kWh/m²/día para facilitar las consultas; sus fórmulas se revisan en las pruebas de enriquecimiento."
    )
    r.para(
        "Los datos meteorológicos corresponden a 2025. La fecha UTC que aparece en los reportes indica cuándo se ejecutó el proceso. Son dos fechas distintas: una corresponde a la observación y la otra a la ejecución del código."
    )

    r.new("9. Tablas y campos: datos por hora")
    physical("fact_hourly")
    r.para(
        "source_row identifica cada fila y es la clave primaria. La combinación (city_id, time_id) también debe ser única. Los índices por time_id y fecha solar apoyan las consultas por tiempo. La vista enriched_data reúne las seis tablas y conserva las 63 columnas en el orden del CSV, incluidas las marcas de calidad y de cruce. El esquema completo está en src/sql/schema.sql.",
        SMALL,
    )

    r.new("10. Herramientas y simulación de nube")
    r.table(
        [
            ["Herramienta", "Para qué la usé", "Límite y posible mejora"],
            [
                "DuckDB 1.5.5",
                "Permite consultar con SQL las bases de EA1 y la entrada limpia del enriquecimiento.",
                "Se ejecuta en una sola máquina, dentro del proceso.",
            ],
            [
                "SQLite (sqlite3)",
                "Guarda el modelo final, sus claves y reglas en un archivo fácil de compartir.",
                "Tiene límites cuando muchos usuarios escriben al mismo tiempo.",
            ],
            [
                "Pandas 2.3.3 / NumPy 1.26.4",
                "Permiten leer los formatos, limpiar, unir datos y repetir la simulación.",
                "Carga en memoria. El volumen actual cabe en una máquina.",
            ],
            [
                "PySpark",
                "Lo considero una opción para repartir el trabajo si aumenta el volumen. No se usa aquí.",
                "Requiere configurar particiones y ejecutores, y medir si compensa el esfuerzo.",
            ],
            [
                "GitHub Actions",
                "Ejecuta las pruebas y el proceso con Ubuntu/Python 3.12 y guarda los resultados.",
                "La máquina de ejecución es temporal; los datos necesitan un respaldo.",
            ],
            [
                "Openpyxl / lxml",
                "Lectura y exportación XLSX; lectura de tablas HTML. XML usa el parser etree.",
                "Los CSV y manifiestos permiten revisar los datos y su origen.",
            ],
        ],
        [100, 210, WIDTH - 310],
    )
    r.para(
        "Elegí SQLite para el modelo final porque permite trabajar con relaciones y restricciones en un archivo que se puede abrir sin instalar un servidor. Conservé DuckDB para usar las bases de las actividades anteriores. Así puedo seguir el proceso completo y revisar el resultado con SQL (DuckDB Foundation, s. f.; SQLite, s. f.-c)."
    )
    r.para(
        "La nube se simula con carpetas que separan los JSON originales, los datos limpios, los enriquecidos y la base final. GitHub guarda el código y las copias de los datos, mientras GitHub Actions ejecuta el proceso en una máquina temporal. El alcance es académico: no se desplegaron servicios como S3 ni un clúster distribuido."
    )
    r.para(
        "Usé Pandas porque los datos actuales caben en la memoria de un computador. Si el volumen crece, primero revisaría el consumo de RAM, los tiempos y la posibilidad de procesar por partes. PySpark sería una opción para repartir el trabajo entre varias máquinas, pero habría que justificar esa complejidad con mediciones. En esta entrega se explica como alternativa y no se ejecuta (pandas development team, s. f.-b; Apache Software Foundation, s. f.)."
    )

    r.new("11. Automatización y reproducción")
    r.para(
        "El archivo que ejecuta GitHub Actions está en .github/workflows/bigdata.yml, en la raíz del repositorio. Dejé una copia dentro de sebastian_clavijo_correa para cumplir la estructura de la actividad; el proceso comprueba que sean iguales. Se activa al subir cambios, abrir una solicitud de cambios o iniciarlo manualmente. Usa contents: read, versiones fijas de las dependencias y acciones identificadas por su SHA."
    )
    r.table(
        [
            ["Orden", "Operación", "Evidencia o condición"],
            ["1", "Checkout e instalación", "Python 3.12; requirements.txt; setup.py"],
            ["2", "Pruebas unitarias", "44 casos; build/tests.log"],
            ["3", "Repetir ingesta y comparar con EA1", "5 JSON íntegros; valores idénticos"],
            ["4", "Limpieza y contraste EA2", "CSV nuevo idéntico byte a byte"],
            ["5", "Enriquecimiento", "6 cruces; CSV idéntico al antecedente"],
            ["6", "Modelo SQLite", "6 tablas; 63 columnas reconstruidas"],
            ["7", "Publicación del artefacto", "Salidas nuevas, auditorías, SQL, PDF y diagramas"],
        ],
        [40, 167, WIDTH - 207],
    )
    r.para(
        "Cada ejecución genera sus resultados en build/, una carpeta excluida de Git. De esta forma se comprueban salidas recién creadas y se conservan las bases de entrada. Si una comparación o una regla falla, el proceso se detiene y no publica el paquete de resultados."
    )
    r.sub("11.1 Comandos desde la carpeta académica")
    for cmd in [
        "python -m venv .venv",
        "python -m pip install -r requirements.txt",
        "python -m pip install -e . --no-deps --no-build-isolation",
        "python -m unittest discover -s tests -v",
        "python src/pipeline.py --output-dir build",
        "python src/enrichment.py",
    ]:
        r.para(cmd, SMALL)
    r.para(
        "Antes de instalar, activa el entorno con .venv\\Scripts\\Activate.ps1 en PowerShell o source .venv/bin/activate en Linux/macOS. pipeline.py ejecuta todo el proceso; enrichment.py permite repetir solo el enriquecimiento desde cleaned.duckdb. El README explica cómo clonar el repositorio y dónde queda cada salida.",
        SMALL,
    )
    r.para(
        "Actions guarda el paquete de resultados durante 30 días. Por eso también conservo las evidencias de la entrega en el repositorio y en el ZIP. El archivo docs/ENTREGA.md contiene el enlace y el resultado de la ejecución remota revisada (GitHub, s. f.)."
    )

    r.new("12. Resultados, conclusiones y mejoras")
    r.table(
        [
            ["Comprobación local", "Resultado observado"],
            ["Comparación con EA1", "43.800 filas reproducidas con valores exactos"],
            ["Comparación con EA2 y enriquecimiento", "Ambos CSV completos coinciden byte a byte"],
            ["Columnas conservadas", "32 variables heredadas intactas; 31 incorporadas"],
            [
                "SQLite",
                "5 ciudades, 365 fechas, 24 horas, 8.760 instantes, 1.825 hechos solares y 43.800 horarios",
            ],
            ["Integridad", "0 huérfanos; integrity_check=ok; 2.759.400 celdas reconstruidas"],
            ["Pruebas", "44 casos aprobados: 13 de limpieza, 25 de enriquecimiento y 6 del modelo"],
        ],
        [180, WIDTH - 180],
    )
    r.para(
        "Las pruebas del modelo usan casos con un dato solar contradictorio, un booleano inválido, una hora duplicada y una referencia a una fecha inexistente. El proceso debe rechazarlos. También revisan los ceros iniciales de los códigos DANE y la recuperación de todas las columnas. Las pruebas de las fases anteriores comprueban nulos, duplicados, unidades, cruces y zonas horarias. No se hicieron pruebas de carga distribuida ni de predicción."
    )
    r.sub("12.1 Conclusiones")
    r.para(
        "Con esta integración puedo seguir un dato desde la respuesta de la API hasta la base final. Las comparaciones con las actividades anteriores permiten comprobar que la limpieza y el enriquecimiento se mantienen al ejecutar todo junto. SQLite agrega reglas sobre las claves y separa los valores diarios de los horarios, lo que ayuda a consultar la información sin contar medidas de más."
    )
    r.para(
        "El proyecto se limita a cinco ciudades, un año y una variable de energía simulada. Por eso no permite estimar la demanda eléctrica real de Colombia. Además, el proceso trabaja en memoria y guarda archivos locales: funciona para esta actividad, pero necesitaría cambios para manejar muchos más datos o varios usuarios al mismo tiempo."
    )
    r.sub("12.2 Recomendaciones")
    r.para(
        "Como siguiente paso, llevaría los archivos a un almacenamiento de objetos con versiones y guardaría los datos en Parquet, separados por fecha. También revisaría una base analítica administrada, los permisos de acceso, el manejo de credenciales y las copias de respaldo. Antes de pasar a PySpark mediría tiempos y memoria. Para actualizar la información, agregaría una ingesta que traiga solo los datos nuevos, con reintentos y revisión del esquema."
    )
    r.para(
        "Si el proyecto continúa hacia la predicción, necesitaría mediciones reales de energía o mantener claro que se trata de una simulación. Separaría entrenamiento y evaluación por tiempo, recalcularía las escalas con entrenamiento y usaría solo la información disponible al momento de predecir. Estas recomendaciones quedan como trabajo pendiente."
    )

    r.new("Bibliografía")
    references = [
        (
            "Apache Software Foundation. (s. f.). <i>Cluster mode overview.</i>",
            "https://spark.apache.org/docs/latest/cluster-overview.html",
        ),
        ("DuckDB Foundation. (s. f.). <i>Why DuckDB.</i>", "https://duckdb.org/why_duckdb"),
        (
            "GitHub. (s. f.). <i>Workflow artifacts.</i>",
            "https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts",
        ),
        (
            "Open-Meteo. (s. f.). <i>Historical weather API.</i>",
            "https://open-meteo.com/en/docs/historical-weather-api",
        ),
        (
            "pandas development team. (s. f.-a). <i>pandas.DataFrame.merge.</i>",
            "https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.DataFrame.merge.html",
        ),
        (
            "pandas development team. (s. f.-b). <i>Scaling to large datasets.</i>",
            "https://pandas.pydata.org/pandas-docs/version/2.3/user_guide/scale.html",
        ),
        (
            "SQLite. (s. f.-a). <i>SQLite foreign key support.</i>",
            "https://www.sqlite.org/foreignkeys.html",
        ),
        ("SQLite. (s. f.-b). <i>Datatypes in SQLite.</i>", "https://www.sqlite.org/datatype3.html"),
        (
            "SQLite. (s. f.-c). <i>Appropriate uses for SQLite.</i>",
            "https://www.sqlite.org/whentouse.html",
        ),
        (
            "Clavijo Correa, J. S. (2026a). <i>Preprocesamiento y limpieza de datos en plataforma de Big Data en la nube</i> [Código fuente y evidencias]. GitHub.",
            "https://github.com/JSebastianCCorrea/Preprocesamiento_Limpieza_de_Datos_en_Plataforma_de_Big_Data_en_la_Nube",
        ),
        (
            "Clavijo Correa, J. S. (2026b). <i>Enriquecimiento de datos en plataforma Big Data en la nube</i> [Código fuente y evidencias]. GitHub.",
            "https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube",
        ),
    ]
    for text, url in references:
        r.para(
            text
            + '<br/><link href="'
            + escape(url)
            + '" color="#176B72">'
            + escape(url)
            + "</link>",
            SMALL,
        )
    r.sub("Materiales y fuentes de datos")
    r.para(
        "Para esta documentación revisé el código, las bases y las evidencias de las actividades anteriores. Los archivos FUENTES.md y src/sources/source_manifest.json registran las consultas al DANE, Nager.Date y Open-Meteo, las condiciones de uso y los cambios de formato. También se conservan las doce respuestas originales del enriquecimiento para repetir y revisar los cruces.",
        SMALL,
    )
    r.pdf.save()
    (DOCS / "arquitectura_modelo_texto.txt").write_text("\n\n".join(r.transcript), encoding="utf-8")
    print(f"PDF generado: {r.page} páginas")


if __name__ == "__main__":
    build()
