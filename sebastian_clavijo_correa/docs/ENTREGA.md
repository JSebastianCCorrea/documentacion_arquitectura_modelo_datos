# Entrega y ejecución comprobada

URL para proporcionar en la plataforma educativa:

https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos

Autor: **Juan Sebastian Clavijo Correa**. Materia: **Infraestructura y Arquitectura para Big Data**.

Documento principal: [arquitectura_modelo.pdf](arquitectura_modelo.pdf), 14 páginas con arquitectura, fases, diagramas, diccionario físico, herramientas, automatización, conclusiones y bibliografía. Las fuentes editables de los diagramas están en [diagramas/](diagramas/).

## Versión actual

Se revisó la redacción del informe, los README y la documentación, y se ordenó el código para facilitar su lectura. Los comentarios no contienen emojis ni emoticones. Los datos, las fórmulas y las reglas del proceso se conservan.

Después de la revisión pasaron las 44 pruebas locales y la ejecución completa. Los CSV generados coinciden con las entregas anteriores y la vista SQLite conserva todos los valores. El PDF mantiene 14 páginas, revisadas visualmente. Los registros están indicados en [PRUEBAS.md](PRUEBAS.md).

## Validación de la versión anterior a la revisión de estilo

- 44 pruebas locales aprobadas y 44 pruebas remotas aprobadas en Ubuntu/Python 3.12.
- Ingesta reproducida desde cinco respuestas API archivadas; equivalencia exacta con EA1.
- CSV limpio y enriquecido nuevos coinciden byte a byte con sus antecedentes.
- 43.800 filas y 63 columnas; vista SQLite reconstruida sin diferencias ni huérfanos.
- PDF revisado visualmente en todas sus páginas.

[GitHub Actions: ejecución 36804375739, exitosa](https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos/actions/runs/36804375739).

Commit de código comprobado: `a9660dc1be7a75f75c6e730fd09800ddf71ff1bd`. Ejecución terminada el 30 de septiembre de 2026, hora de Colombia; los logs expresan su fecha en UTC.

Artefacto: `arquitectura-modelo-36804375739-1`, ID `11136618535`, 8.216.366 bytes, retención de 30 días. Se descargó y se comparó con la entrega local: CSV y PDF idénticos byte a byte; las 2.759.400 celdas de la vista SQLite son iguales. Los archivos SQLite pueden cambiar entre versiones del motor aunque contengan los mismos datos. Por eso se compararon sus tipos, claves y valores.

El detalle de esa ejecución está en `src/static/auditoria/remote_verification.json`. Ese registro corresponde al código y al PDF de la versión anterior. Las ejecuciones más recientes se pueden consultar en [GitHub Actions](https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos/actions).

## Qué entregar

Proporciona la URL del repositorio. El PDF está dentro de `sebastian_clavijo_correa/docs`, como indica la estructura. El ZIP local contiene los archivos del repositorio, sin `.git`, entornos ni carpetas temporales.

La entrega en la plataforma educativa queda pendiente.
