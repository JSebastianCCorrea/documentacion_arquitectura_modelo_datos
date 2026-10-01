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
WIDTH = W - M*2
NAVY = colors.HexColor('#19344B')
TEAL = colors.HexColor('#176B72')
PALE = colors.HexColor('#EDF4F6')
TEXT = colors.HexColor('#243746')
BODY = ParagraphStyle('body', fontName='Helvetica', fontSize=10.4, leading=15,
                      textColor=TEXT, alignment=TA_JUSTIFY, spaceAfter=9)
SMALL = ParagraphStyle('small', parent=BODY, fontSize=8.4, leading=11, alignment=0)
CELL = ParagraphStyle('cell', parent=SMALL, fontSize=8, leading=10)
HEAD = ParagraphStyle('head', parent=BODY, fontName='Helvetica-Bold', fontSize=13,
                      leading=17, textColor=NAVY, alignment=0)
TITLE = ParagraphStyle('title', parent=HEAD, fontSize=22, leading=27)


class Report:
    def __init__(self, path):
        self.pdf = canvas.Canvas(str(path), pagesize=(W,H))
        self.pdf.setTitle('Arquitectura y modelo de datos del proyecto integrador')
        self.pdf.setAuthor('Juan Sebastian Clavijo Correa')
        self.page = 0
        self.y = H-M
        self.transcript = []

    def new(self, title, subtitle=''):
        if self.page:self.pdf.showPage()
        self.page += 1
        self.y = H-M
        c=self.pdf
        c.setFillColor(TEAL);c.rect(M,H-30,WIDTH,3,fill=1,stroke=0)
        c.setFont('Helvetica',8);c.setFillColor(TEXT)
        c.drawString(M,25,'INFRA BIG DATA  /  JUAN SEBASTIAN CLAVIJO CORREA')
        c.drawRightString(W-M,25,str(self.page))
        self.para(title,TITLE)
        if subtitle:self.para(subtitle,SMALL)
        self.y-=8

    def para(self, text, style=BODY):
        item=Paragraph(text,style);_,height=item.wrap(WIDTH,720)
        if self.y-height < 47:raise ValueError(f'Página {self.page} desbordada: {text[:70]}')
        item.drawOn(self.pdf,M,self.y-height);self.y-=height+style.spaceAfter
        self.transcript.append(re.sub('<[^>]+>','',text))

    def sub(self,text):self.para(text,HEAD)

    def table(self, rows, widths=None):
        data=[[Paragraph(escape(str(v)),CELL) for v in row] for row in rows]
        t=Table(data,colWidths=widths or [WIDTH/len(rows[0])]*len(rows[0]))
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),
             ('LINEBELOW',(0,0),(-1,0),.7,TEAL),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#D1DDE1')),
             ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
             ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        _,height=t.wrap(WIDTH,700)
        if self.y-height<47:raise ValueError(f'Tabla desbordada en página {self.page}')
        t.drawOn(self.pdf,M,self.y-height);self.y-=height+12

    def diagram(self, kind, height):
        self.pdf.saveState();self.pdf.translate(M,self.y-height)
        draw_diagram(self.pdf,kind);self.pdf.restoreState();self.y-=height+12


def diagram_data(kind):
    if kind=='arquitectura':
        nodes=[('api',8,286,150,65,'API Open-Meteo','Extracción histórica EA1|5 JSON horarios de 2025'),
               ('raw',174,286,150,65,'Respuestas archivadas','JSON + SHA-256|Replay sin red en CI'),
               ('ing',340,286,150,65,'ingestion.py','Pandas + NumPy|Energía sintética / DuckDB'),
               ('clean',340,173,150,70,'cleaning.py','Hechos + dimensiones|32 columnas / auditoría'),
               ('enrich',174,173,150,70,'enrichment.py','6 cruces LEFT N:1|63 columnas / auditoría'),
               ('source',8,173,150,70,'Fuentes complementarias','JSON, XLSX, CSV|XML, HTML, TXT'),
               ('sql',174,58,150,70,'model.py + SQLite','6 tablas con PK / FK|Vista enriched_data'),
               ('out',340,58,150,70,'Evidencias','CSV y XLSX / 1.200 filas|PDF, SQL, logs y artefacto')]
        edges=[('api','raw'),('raw','ing'),('ing','clean'),('clean','enrich'),('source','enrich'),('enrich','sql'),('sql','out')]
    else:
        nodes=[('city',8,302,200,75,'dim_city  /  5','PK city_id|Ciudad, coordenadas, DIVIPOLA'),
               ('date',289,302,200,75,'dim_date  /  365','PK local_date|Calendario y festivos'),
               ('solar',8,164,200,90,'fact_solar_day  /  1.825','PK (city_id, local_date)|FK ciudad y fecha|Radiación y duración del día'),
               ('time',289,164,200,90,'dim_time  /  8.760','PK time_id|FK local_date, hour|Instantes local y UTC'),
               ('fact',8,23,200,90,'fact_hourly  /  43.800','PK source_row|FK city_id, time_id|UNIQUE (city_id, time_id)'),
               ('hour',289,23,200,90,'dim_hour  /  24','PK hour|Franja horaria')]
        edges=[('city','solar'),('date','time'),('hour','time'),('time','fact'),('city','fact'),('date','solar')]
    return nodes,edges


def draw_diagram(c,kind):
    nodes,edges=diagram_data(kind)
    lookup={n[0]:n for n in nodes}
    def arrow(points,label=''):
        c.setStrokeColor(TEAL);c.setLineWidth(1.1)
        p=c.beginPath();p.moveTo(*points[0])
        for pt in points[1:]:p.lineTo(*pt)
        c.drawPath(p)
        import math
        x,y=points[-1];a=math.atan2(y-points[-2][1],x-points[-2][0]);size=5
        p=c.beginPath();p.moveTo(x,y);p.lineTo(x-size*math.cos(a-.5),y-size*math.sin(a-.5));p.lineTo(x-size*math.cos(a+.5),y-size*math.sin(a+.5));p.close()
        c.setFillColor(TEAL);c.drawPath(p,fill=1)
        if label:
            c.setFont('Helvetica',8);c.drawString(points[0][0]+4,points[0][1]-14,label)
    for a,b in edges:
        _,x,y,w,h,*_=lookup[a];_,xx,yy,ww,hh,*_=lookup[b]
        if kind=='er' and a=='city' and b=='fact':points=[(x,y+h/2),(0,y+h/2),(0,yy+hh/2),(xx,yy+hh/2)]
        elif kind=='er' and a=='date' and b=='solar':points=[(x,y+h/2),(247,y+h/2),(247,yy+hh/2),(xx+ww,yy+hh/2)]
        elif kind=='er' and a=='time' and b=='fact':points=[(x,y+12),(255,y+12),(255,yy+hh/2),(xx+ww,yy+hh/2)]
        elif abs(y-yy)<10:
            points=[(x+w,y+h/2),(xx,yy+hh/2)] if xx>x else [(x,y+h/2),(xx+ww,yy+hh/2)]
        elif yy<y:points=[(x+w/2,y),(xx+ww/2,yy+hh)]
        else:points=[(x+w/2,y+h),(xx+ww/2,yy)]
        arrow(points)
    for _,x,y,w,h,title,body in nodes:
        c.setFillColor(PALE);c.setStrokeColor(TEAL);c.roundRect(x,y,w,h,5,fill=1)
        c.setFont('Helvetica-Bold',9.1);c.setFillColor(NAVY);c.drawString(x+8,y+h-17,title)
        c.setFont('Helvetica',8.4)
        for i,line in enumerate(body.split('|')):c.drawString(x+8,y+h-33-i*12,line)
    if kind=='er':
        c.setFillColor(TEAL);c.setFont('Helvetica',8)
        for x,y in [(113,280),(395,280),(395,137),(260,145),(5,132),(226,276)]:c.drawString(x,y,'1:N')
    if kind=='arquitectura':
        c.setFillColor(TEXT);c.setFont('Helvetica',8.4)
        c.drawString(8,20,'GitHub Actions ejecuta la cadena en un runner y conserva los resultados durante 30 días.')


def save_diagrams():
    directory=DOCS/'diagramas';directory.mkdir(exist_ok=True)
    for kind,height in [('arquitectura',365),('er',390)]:
        cv=canvas.Canvas(str(directory/f'{kind}.pdf'),pagesize=(WIDTH,height))
        draw_diagram(cv,kind);cv.save()
        nodes,edges=diagram_data(kind)
        mx=ET.Element('mxfile',host='app.diagrams.net');dia=ET.SubElement(mx,'diagram',name=kind)
        graph=ET.SubElement(dia,'mxGraphModel');root=ET.SubElement(graph,'root')
        ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
        for ident,x,y,w,h,title,body in nodes:
            node=ET.SubElement(root,'mxCell',id=ident,value=title+'\n'+body.replace('|','\n'),
                  style='rounded=1;whiteSpace=wrap;html=0;fillColor=#EDF4F6;strokeColor=#176B72;',vertex='1',parent='1')
            ET.SubElement(node,'mxGeometry',x=str(x*2),y=str((height-y-h)*2),width=str(w*2),height=str(h*2),attrib={'as':'geometry'})
        for i,(a,b) in enumerate(edges):
            node=ET.SubElement(root,'mxCell',id='e'+str(i),source=a,target=b,value='1:N' if kind=='er' else '',
                edge='1',parent='1',style='edgeStyle=orthogonalEdgeStyle;endArrow=block;html=0;')
            ET.SubElement(node,'mxGeometry',relative='1',attrib={'as':'geometry'})
        ET.ElementTree(mx).write(directory/f'{kind}.drawio',encoding='utf-8',xml_declaration=True)


def field_descriptions():
    result={}
    for line in (DOCS/'DICCIONARIO_DATOS.md').read_text(encoding='utf-8').splitlines():
        match=re.match(r'\| `([^`]+)` \| (.*?) \| (.*?) \|',line)
        if match:result[match[1]]=match[3].replace('`','').replace('\\','')
    return result


def build():
    catalog=json.loads((ROOT/'src/static/auditoria/model_validation.json').read_text(encoding='utf-8'))
    save_diagrams()
    r=Report(DOCS/'arquitectura_modelo.pdf')
    r.new('Arquitectura y modelo de datos','Proyecto integrador | Documentación técnica y académica')
    r.y-=55
    r.para('Meteorología y energía sintética en cinco ciudades de Colombia',TITLE)
    r.y-=20
    r.para('<b>Juan Sebastian Clavijo Correa</b>')
    r.para('Institución Universitaria Digital de Antioquia<br/>Infraestructura y Arquitectura para Big Data<br/>30 de septiembre de 2026')
    r.y-=28
    r.table([['Alcance verificado','Resultado'],['Periodo y grano','2025 completo; una ciudad por hora local'],
        ['Integración','43.800 filas; 32 columnas limpias y 63 enriquecidas'],
        ['Modelo final','SQLite: 6 tablas y una vista de reconstrucción'],
        ['Continuidad','DuckDB heredado de EA1, Pandas y GitHub Actions']], [150,WIDTH-150])
    r.para('Este documento reúne las fases desarrolladas durante el curso y las contrasta con sus archivos de entrada, scripts y evidencias. La energía es una variable sintética con fines académicos; los resultados no describen consumo eléctrico medido ni prueban una relación causal con el clima.')
    r.para('Repositorio: <link href="https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos" color="#176B72">JSebastianCCorrea/documentacion_arquitectura_modelo_datos</link>',SMALL)
    r.para('Lectura: arquitectura (2), ingesta (3), limpieza (4), enriquecimiento (5), modelo ER (6), diccionario físico (7-10), herramientas (11), automatización (12), resultados y recomendaciones (13), bibliografía (14).',SMALL)

    r.new('1. Visión global de la arquitectura')
    r.para('El proyecto organiza datos meteorológicos horarios de Medellín, Bogotá, Cali, Barranquilla y Bucaramanga, y los combina con una simulación de energía. Su propósito es disponer de una base trazable para explorar patrones por ciudad y tiempo. El volumen permite ejecutar el proceso localmente y comprobar las reglas antes de trasladarlas a una infraestructura mayor.')
    r.diagram('arquitectura',365)
    r.para('<b>Figura 1.</b> Flujo completo. Elaboración propia a partir de los scripts del repositorio. El tramo API-JSON corresponde a la extracción de EA1; la ejecución automatizada actual comienza en las respuestas archivadas.',SMALL)
    r.para('La entrada se conserva, la limpieza genera una versión tipada y el enriquecimiento añade contexto sin sustituir las variables originales. Después se materializa el modelo SQLite. Cada transición produce evidencias que permiten localizar una diferencia sin repetir solicitudes a proveedores externos.')
    r.para('La carpeta anterior se llamaba actividad_4, pero contenía la fase de enriquecimiento. En este informe se distinguen las fases por su función: EA1, ingesta; EA2, limpieza; tercera fase, enriquecimiento. La presente entrega integra y documenta esas implementaciones.')

    r.new('2. Ingesta y trazabilidad de origen')
    r.sub('2.1 Extracción realizada en EA1')
    r.para('El script original consultó Historical Weather API de Open-Meteo mediante requests.get, con fechas 2025-01-01 a 2025-12-31, coordenadas de cada ciudad y timezone=America/Bogota. Solicitó temperature_2m, relative_humidity_2m, precipitation y wind_speed_10m. Cada respuesta quedó guardada como JSON. El API entrega productos meteorológicos modelados; la consulta de EA1 no fijó el parámetro models, por lo que no se atribuye toda la meteorología exclusivamente a ERA5 (Open-Meteo, s. f.).')
    r.para('Las coordenadas incorporadas a la base son las solicitadas para las ciudades. No deben confundirse con las coordenadas de la celda de la malla que devuelve el proveedor. Las respuestas originales conservan esa información y sus unidades.')
    r.sub('2.2 Simulación de energía y carga analítica')
    r.para('EA1 asignó consumos base ilustrativos de 110, 130, 115, 125 y 100 a Medellín, Bogotá, Cali, Barranquilla y Bucaramanga. Multiplicó cada base por un factor horario (1,25 de 18 a 21 h; 1,15 de 7 a 9 h; 1 en otras horas), un factor térmico 1 + |T - 22| × 0,015, un factor de lluvia 1 + precipitación × 0,005 y ruido normal con media 1 y desviación 0,05. NumPy utilizó semilla 42 y se redondeó a dos decimales.')
    r.para('El resultado pasó a staging_weather y a las dimensiones dim_city y dim_time, relacionadas lógicamente con fact_weather_energy. La construcción original mediante CREATE TABLE AS no declaró claves primarias ni foráneas. Por eso la limpieza comprueba unicidad y ausencia de huérfanos antes de unir estas tablas.')
    r.table([['Tabla de EA1 (DuckDB)','Filas','Función'],['staging_weather','43.800','Carga inicial: 11 columnas'],['dim_city','5','Identificador local y coordenadas'],['dim_time','8.760','Una hora por fila'],['fact_weather_energy','43.800','Ciudad/hora, meteorología y energía sintética']], [180,55,WIDTH-235])
    r.sub('2.3 Reproducción en esta entrega')
    r.para('src/ingestion.py verifica SHA-256 de los cinco JSON y reconstruye la ingesta sin red. Mantiene el orden original de ciudades y horas para reproducir el ruido. src/db/ingestion.db es una copia inalterada de analytics.duckdb de EA1: su extensión .db no la convierte en SQLite. El replay se contrasta, valor por valor, contra la extracción de esa copia. El código histórico está en docs/antecedentes/ingesta_ea1_original.py.')

    r.new('3. Preprocesamiento y limpieza')
    r.para('src/cleaning.py conserva la lógica de EA2. Lee la tabla de hechos y sus dimensiones en modo de solo lectura, valida las claves y ordena por ciudad y tiempo. Asigna source_row para mantener la correspondencia con la salida original. Después normaliza los nombres de ciudad y convierte números, booleanos y fechas.')
    r.table([['Control','Decisión aplicada'],['Clave ciudad-hora','Se eliminan duplicados exactos. Si una clave ciudad-hora tiene valores contradictorios, se rechazan todas sus versiones.'],['Valores ausentes','Se descartan claves inválidas. Las medidas imputables siguen la regla de mediana por ciudad, año y mes. Si falta lluvia o no hay donante para imputar, se rechaza la fila.'],['Rangos físicos','Latitud, longitud, humedad y medidas no negativas se validan antes de aceptar un registro.'],['Atípicos','Regla IQR por ciudad: marcas de revisión, sin recortar ni borrar automáticamente.'],['Zona horaria','Interpretación local America/Bogota y columna adicional observation_time_utc.'],['Transformaciones','Z-score de temperatura y energía por ciudad, humedad/100 y log1p de precipitación.']], [113,WIDTH-113])
    r.sub('3.1 Lo observado en la entrada disponible')
    r.para('La base recibida ya tenía 43.800 filas sin nulos ni duplicados: en esta ejecución no se eliminaron filas, no se imputaron valores y no hubo rechazos. Se conservaron 6.240 filas con alguna marca de atípico. Aplicar controles no obliga a encontrar errores; el informe registra las operaciones realmente necesarias.')
    r.para('El CSV limpio contiene 32 columnas. Su huella coincide byte a byte con el archivo aprobado en EA2. Las muestras CSV y XLSX contienen 1.200 registros: hasta 20 por ciudad, año y mes, con semilla 42. La cobertura y los pesos de expansión permiten reconocer que se trata de una muestra estratificada de cuota fija.')
    r.sub('3.2 Uso posterior de las variables')
    r.para('Los z-scores y las marcas IQR se calcularon con el año completo. Son útiles para describir esta base, pero no deben trasladarse sin revisión a un experimento predictivo. Primero habría que separar entrenamiento y evaluación por tiempo y ajustar las transformaciones solo con el entrenamiento. Esta entrega no entrena ni evalúa modelos de predicción.')
    r.para('Evidencias: src/static/auditoria/limpieza/cleaning_report.txt, cleaning_metrics.json, quality_profile.csv y rejected_records.csv. La copia histórica de auditoría de EA2 se conserva en ea2_original/ para distinguir el antecedente de la ejecución integrada.',SMALL)

    r.new('4. Enriquecimiento de seis formatos')
    r.para('La entrada es el CSV limpio completo, no la muestra. Se carga en cleaned_data dentro de cleaned.duckdb y se lee con Pandas. Las seis fuentes están incluidas en el repositorio con sus manifiestos, instantáneas originales y hashes. Pandas permite lectores distintos y una operación merge con validación de cardinalidad (pandas development team, s. f.-a).')
    r.table([['Archivo / formato','Clave de cruce','Filas fuente','Aporte'],
       ['city_geography.json','Ciudad normalizada','5','País, GeoNames y elevación'],
       ['calendar_2025.xlsx','Fecha local','365','Festivo y fin de semana'],
       ['solar_daily_2025.csv','Ciudad + fecha','1.825','Radiación y duración solar'],
       ['municipalities.html','Ciudad normalizada','5','Códigos y nombres DANE'],
       ['thermal_parameters.xml','Ciudad normalizada','5','Referencia académica 18 °C'],
       ['hour_bands.txt','Hora local','24','Franja del día']], [164,105,58,WIDTH-327])
    r.para('Cada unión es LEFT JOIN con validate="many_to_one": todas las filas base se conservan y una clave repetida en una fuente detiene el proceso. La clave auxiliar de ciudad elimina tildes y diferencias de mayúsculas o espacios; el nombre original queda intacto. Las fechas se obtienen en Colombia antes de cruzar con fuentes diarias.')
    r.para('Los seis cruces encontraron correspondencia para las 43.800 filas; no aumentó el número de registros. Se añadieron 31 columnas: atributos, indicadores matched_*, conversiones de unidades y estado de integración. MJ/m²/día se divide por 3,6 para obtener kWh/m²/día; las duraciones en segundos se dividen por 3.600. Las diferencias con 18 °C son referencias ilustrativas, no índices de confort validados.')
    r.sub('4.1 Procedencia y límites de interpretación')
    r.para('Hay cuatro conjuntos externos de tres proveedores: Open-Meteo/GeoNames, Nager.Date y DANE. XML y TXT son catálogos propios. El HTML se preparó a partir del servicio JSON oficial DANE, no de una página inventada. El calendario agrupa 18 festividades en 17 fechas. Bucaramanga conserva el año DIVIPOLA 2024 recibido por el servicio denominado 2025; no se corrigió ese dato sin evidencia.')
    r.para('Si falta correspondencia, enrichment.py conserva la fila con INCOMPLETE y no imputa los atributos externos. La materialización SQLite de esta entrega exige COMPLETE y detiene su publicación si encuentra faltantes. El dato solar del día completo es retrospectivo y no debe emplearse para anticipar una hora de ese mismo día.')

    r.new('5. Modelo lógico y relaciones')
    r.para('El modelo final es una constelación dimensional pequeña: dos tablas de hechos comparten dimensiones, y la dimensión temporal separa calendario y hora. La ciudad-hora identifica cada observación meteorológica; la ciudad-fecha identifica cada observación solar. Esta separación evita sumar 24 veces el valor diario que se repite en el archivo plano.')
    r.diagram('er',390)
    r.para('<b>Figura 2.</b> Modelo físico SQLite. Las flechas indican relación de padre a hijo 1:N. Cada hijo tiene una sola fila padre para la clave obligatoria. Elaboración propia; PK y FK corresponden al DDL ejecutado.',SMALL)
    r.para('fact_hourly referencia dim_city y dim_time. dim_time referencia dim_date y dim_hour. fact_solar_day referencia dim_city y dim_date. No se enlazan directamente los dos hechos mediante una FK: la vista los integra por ciudad y la fecha obtenida desde dim_time.')
    r.para('model.py activa PRAGMA foreign_keys=ON, carga tablas STRICT en una base temporal y ejecuta foreign_key_check e integrity_check. Solo sustituye analytics.sqlite cuando la vista reconstruye las 63 columnas sin diferencias. Las claves, NOT NULL, UNIQUE y CHECK complementan los controles de Pandas (SQLite, s. f.-a).')

    descriptions=field_descriptions()
    def physical(name):
        info=catalog['tables'][name]
        r.sub(name+' | '+f"{info['rows']:,}".replace(',','.')+' filas')
        rows=[['Campo','Tipo / clave','Descripción']]
        for _,field,typ,nonnull,default,pk in info['columns']:
            fk=any(item[3]==field for item in info['foreign_keys'])
            annotation=typ+(' / PK' if pk else '')+(' / FK' if fk else '')
            desc=descriptions.get(field,field)
            desc=desc.split(';')[0]
            if len(desc)>120:desc=desc[:117]+'...'
            rows.append([field,annotation,desc])
        r.table(rows,[162,69,WIDTH-231])
    r.new('6. Diccionario físico: ciudad')
    r.para('Los tipos siguientes proceden de PRAGMA table_info sobre la base creada. Todos los campos físicos son NOT NULL. Los booleanos se guardan como INTEGER con CHECK IN (0,1); los identificadores territoriales se conservan como TEXT para mantener ceros iniciales. Las unidades y definiciones completas de las 63 variables están también en DICCIONARIO_DATOS.md.')
    physical('dim_city')
    r.para('city_id conserva el identificador local de EA1; no equivale a municipality_code. city y municipality_code tienen restricciones UNIQUE. Los códigos municipales y departamentales exigen cinco y dos dígitos, respectivamente. La dimensión representa únicamente las cinco ciudades incluidas, no un catálogo nacional completo.',SMALL)

    r.new('7. Diccionario físico: calendario y tiempo')
    physical('dim_date');physical('dim_hour');physical('dim_time')
    r.para('Las fechas se almacenan como texto ISO 8601. observation_time conserva el desplazamiento -05:00 y observation_time_utc el instante en UTC; timezone conserva America/Bogota. SQLite no tiene un tipo nativo TIMESTAMPTZ. El origen DuckDB sí lo utiliza en cleaned_data. (SQLite, s. f.-b).',SMALL)

    r.new('8. Diccionario físico: hechos solares')
    physical('fact_solar_day')
    r.sub('8.1 Granularidad y agregación')
    r.para('La clave primaria compuesta (city_id, local_date) obliga a tener como máximo una observación solar por ciudad y día. Si las 24 filas horarias de un mismo día aportan valores solares distintos, model.py falla antes de escribir. La selección de filas únicas es válida porque primero se comprueba esa dependencia funcional.')
    r.para('La suma anual de radiación se consulta en fact_solar_day, agrupando por city_id. En enriched_data la medida diaria vuelve a repetirse para facilitar el análisis de cada hora: no se debe sumar directamente allí. La energía sintética horaria sí puede sumarse por periodos, siempre manteniendo su carácter simulado.')
    r.sub('8.2 Integridad del dato diario')
    r.para('Los CHECK exigen radiación no negativa, duración de luz entre 0 y 86.400 segundos y sunshine_seconds entre cero y daylight_seconds. Las dos FK impiden cargar una ciudad o fecha inexistente. Las conversiones se conservan para lectura directa; sus fórmulas se prueban en la etapa de enriquecimiento.')
    r.para('Las fechas y variables meteorológicas describen 2025. La fecha de ejecución del pipeline, registrada en UTC en los archivos JSON, identifica cuándo se transformó la instantánea; no sustituye la fecha de observación ni representa una actualización automática del proveedor.')

    r.new('9. Diccionario físico: hechos horarios')
    physical('fact_hourly')
    r.para('source_row es PK y (city_id, time_id) es UNIQUE. Los índices por time_id y fecha solar favorecen consultas temporales. La vista enriched_data une las seis tablas y devuelve las 63 columnas en el mismo orden del CSV, incluyendo las marcas de calidad y de correspondencia. El SQL completo está en src/sql/schema.sql.',SMALL)

    r.new('10. Herramientas y simulación de nube')
    r.table([['Herramienta','Uso efectivo y justificación','Límite / siguiente paso'],
       ['DuckDB 1.5.5','Conserva EA1 y la entrada limpia de enriquecimiento; consulta analítica SQL embebida.','No se presenta como un servicio cloud ni un clúster distribuido.'],
       ['SQLite (sqlite3)','Modelo final portable con PK, FK y restricciones. Se abre sin administrar un servidor.','Un archivo local no resuelve alta concurrencia de escritura ni disponibilidad multizona.'],
       ['Pandas 2.3.3 / NumPy 1.26.4','Lectura multiformato, reglas de calidad, cruces y reproducción de la simulación.','Carga en memoria. El volumen actual cabe en una máquina.'],
       ['PySpark','Alternativa estudiada para crecimiento; no se usa ni se instala en esta entrega.','Su adopción requiere particiones, ejecutores y mediciones que justifiquen el costo operativo.'],
       ['GitHub Actions','Runner Ubuntu/Python 3.12: instala, prueba, ejecuta y publica artefactos.','Es automatización remota; no reemplaza un almacén de datos persistente.'],
       ['Openpyxl / lxml','Lectura y exportación XLSX; lectura de tablas HTML. XML usa el parser etree.','Los CSV y manifiestos conservan trazabilidad independiente del formato visual.']], [100,210,WIDTH-310])
    r.para('SQLite se incorpora para cumplir el modelo solicitado, sin describir retrospectivamente DuckDB como si fuera SQLite. La integración conserva ambas tecnologías con responsabilidades distintas: compatibilidad con las fases previas y consulta relacional final. La justificación es verificabilidad y portabilidad, no una supuesta superioridad universal (DuckDB Foundation, s. f.; SQLite, s. f.-c).')
    r.para('La simulación representa capas de almacenamiento con carpetas y archivos: JSON originales, datos limpios, datos enriquecidos y modelo consultable. GitHub aloja código e instantáneas; un runner ejecuta el lote. No se despliegan S3, Azure Blob Storage, redes virtuales ni nodos distribuidos. No se afirma haber procesado un volumen de Big Data real.')
    r.para('Pandas opera en memoria; para crecer se debe medir uso de RAM y tiempos, reducir columnas y evaluar procesamiento por particiones. Spark distribuye trabajo entre un controlador y ejecutores, pero incorporarlo ahora añadiría complejidad sin una necesidad demostrada (pandas development team, s. f.-b; Apache Software Foundation, s. f.).')

    r.new('11. Automatización y reproducción')
    r.para('El workflow activo está en .github/workflows/bigdata.yml de la raíz. La copia interior conserva la estructura académica sebastian_clavijo_correa; CI comprueba que ambas coincidan. Se ejecuta con push, pull_request o workflow_dispatch y solo solicita permiso contents: read. Las acciones están fijadas por SHA y las dependencias principales por versión.')
    r.table([['Orden','Operación','Evidencia o condición'],['1','Checkout e instalación','Python 3.12; requirements.txt; setup.py'],['2','Pruebas unitarias','44 casos; build/tests.log'],['3','Replay y contraste EA1','5 JSON íntegros; valores idénticos'],['4','Limpieza y contraste EA2','CSV nuevo idéntico byte a byte'],['5','Enriquecimiento','6 cruces; CSV idéntico al antecedente'],['6','Modelo SQLite','6 tablas; 63 columnas reconstruidas'],['7','Publicación del artefacto','Salidas nuevas, auditorías, SQL, PDF y diagramas']], [40,167,WIDTH-207])
    r.para('La ejecución integrada escribe en build/, un directorio ignorado por Git y creado en el runner. Así no puede aprobar una evidencia versionada sin volver a generarla. Las instantáneas de entrada permanecen inalteradas. Si falla una comparación o restricción, el proceso devuelve error y no publica el artefacto exitoso.')
    r.sub('11.1 Comandos desde la carpeta académica')
    for cmd in ['python -m venv .venv','python -m pip install -r requirements.txt','python -m pip install -e . --no-deps --no-build-isolation','python -m unittest discover -s tests -v','python src/pipeline.py --output-dir build','python src/enrichment.py']:
        r.para(cmd,SMALL)
    r.para('Activa el entorno antes de instalar: en PowerShell, .venv\\Scripts\\Activate.ps1; en Linux/macOS, source .venv/bin/activate. El último comando permite ejecutar solo enriquecimiento desde cleaned.duckdb; la cadena completa incluye además ingesta, limpieza y SQLite. El README proporciona el comando de clonación y rutas de cada salida.',SMALL)
    r.para('Los artefactos de Actions se retienen 30 días; no son una política de respaldo permanente. Las evidencias versionadas y el ZIP de entrega preservan el estado evaluado. docs/ENTREGA.md registra la URL de la ejecución remota y su resultado comprobado (GitHub, s. f.).')

    r.new('12. Resultados, conclusiones y mejoras')
    r.table([['Comprobación local','Resultado observado'],['Regresión EA1','43.800 filas reproducidas con valores exactos'],['Regresión EA2 y enriquecimiento','Ambos CSV completos coinciden byte a byte'],['Preservación','32 variables heredadas intactas; 31 incorporadas'],['SQLite','5 ciudades, 365 fechas, 24 horas, 8.760 instantes, 1.825 hechos solares y 43.800 horarios'],['Integridad','0 huérfanos; integrity_check=ok; 2.759.400 celdas reconstruidas'],['Pruebas','44 casos aprobados: 13 de limpieza, 25 de enriquecimiento y 6 del modelo']], [180,WIDTH-180])
    r.para('Las pruebas del modelo introducen un valor solar diario inconsistente, un booleano inválido, una hora duplicada y una FK sin padre; verifican su rechazo. También comprueban los ceros iniciales en DIVIPOLA y la reconstrucción completa. Las pruebas previas ejercitan nulos, duplicados, unidades, claves de cruce, zonas horarias y conservación de datos. No se realizó una prueba de carga distribuida ni se midió una mejora predictiva.')
    r.sub('12.1 Conclusiones')
    r.para('La arquitectura mantiene continuidad entre las entregas: se puede recorrer desde una fila enriquecida hasta la observación limpia y la extracción de EA1. Las comprobaciones de igualdad convierten esa trazabilidad en una condición ejecutable, no solo en una explicación. El modelo SQLite añade restricciones físicas que faltaban en el esquema original y separa las medidas diarias de las horarias.')
    r.para('La principal limitación es de alcance: cinco ciudades, un año y energía simulada no permiten inferir demanda real de Colombia. La repetición de datos de referencia, la ejecución en memoria y las instantáneas versionadas son manejables aquí, pero no constituyen una arquitectura productiva de gran escala.')
    r.sub('12.2 Recomendaciones')
    r.para('Para una nube real, mover las instantáneas a almacenamiento de objetos versionado, usar Parquet particionado por fecha y revisar un almacén analítico administrado. Agregar autenticación con privilegio mínimo, gestión de secretos, respaldo y recuperación. Medir tiempos, RAM y concurrencia antes de migrar a PySpark. Incorporar ingesta incremental con reintentos, controles de esquema y un catálogo de procedencia.')
    r.para('Antes del modelado, obtener mediciones energéticas legítimas o mantener explícito el experimento sintético; dividir por tiempo, recalcular escalas en entrenamiento y excluir atributos diarios aún no disponibles al momento de predecir. Las mejoras propuestas son trabajo futuro, no capacidades ya desplegadas.')

    r.new('Bibliografía')
    references=[
      ('Apache Software Foundation. (s. f.). <i>Cluster mode overview.</i>','https://spark.apache.org/docs/latest/cluster-overview.html'),
      ('DuckDB Foundation. (s. f.). <i>Why DuckDB.</i>','https://duckdb.org/why_duckdb'),
      ('GitHub. (s. f.). <i>Workflow artifacts.</i>','https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts'),
      ('Open-Meteo. (s. f.). <i>Historical weather API.</i>','https://open-meteo.com/en/docs/historical-weather-api'),
      ('pandas development team. (s. f.-a). <i>pandas.DataFrame.merge.</i>','https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.DataFrame.merge.html'),
      ('pandas development team. (s. f.-b). <i>Scaling to large datasets.</i>','https://pandas.pydata.org/pandas-docs/version/2.3/user_guide/scale.html'),
      ('SQLite. (s. f.-a). <i>SQLite foreign key support.</i>','https://www.sqlite.org/foreignkeys.html'),
      ('SQLite. (s. f.-b). <i>Datatypes in SQLite.</i>','https://www.sqlite.org/datatype3.html'),
      ('SQLite. (s. f.-c). <i>Appropriate uses for SQLite.</i>','https://www.sqlite.org/whentouse.html'),
      ('Clavijo Correa, J. S. (2026a). <i>Preprocesamiento y limpieza de datos en plataforma de Big Data en la nube</i> [Código fuente y evidencias]. GitHub.','https://github.com/JSebastianCCorrea/Preprocesamiento_Limpieza_de_Datos_en_Plataforma_de_Big_Data_en_la_Nube'),
      ('Clavijo Correa, J. S. (2026b). <i>Enriquecimiento de datos en plataforma Big Data en la nube</i> [Código fuente y evidencias]. GitHub.','https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube')]
    for text,url in references:
        r.para(text+'<br/><link href="'+escape(url)+'" color="#176B72">'+escape(url)+'</link>',SMALL)
    r.sub('Materiales y fuentes de datos')
    r.para('La revisión funcional usa el código y las evidencias locales de EA1, EA2 y enriquecimiento. La consigna y su imagen de estructura fueron suministradas en el chat; los enlaces del aula requieren acceso y no se atribuye contenido adicional no consultado. FUENTES.md y src/sources/source_manifest.json identifican las consultas DANE, Nager.Date y Open-Meteo, sus licencias, formatos preparados y doce respuestas conservadas. No se reproducen credenciales ni datos personales.',SMALL)
    r.pdf.save()
    (DOCS/'arquitectura_modelo_texto.txt').write_text('\n\n'.join(r.transcript),encoding='utf-8')
    print(f'PDF generado: {r.page} páginas')


if __name__=='__main__':build()
