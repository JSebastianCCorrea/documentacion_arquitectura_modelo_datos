# Entrega y ejecución comprobada

URL para proporcionar en la plataforma educativa:

https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos

Autor: **Juan Sebastian Clavijo Correa**. Materia: **Infraestructura y Arquitectura para Big Data**.

Documento principal: [arquitectura_modelo.pdf](arquitectura_modelo.pdf), 14 páginas con arquitectura, fases, diagramas, diccionario físico, herramientas, automatización, conclusiones y bibliografía. Las fuentes editables de los diagramas están en [diagramas/](diagramas/).

## Validación realizada

- 44 pruebas locales aprobadas y 44 pruebas remotas aprobadas en Ubuntu/Python 3.12.
- Ingesta reproducida desde cinco respuestas API archivadas; equivalencia exacta con EA1.
- CSV limpio y enriquecido nuevos coinciden byte a byte con sus antecedentes.
- 43.800 filas y 63 columnas; vista SQLite reconstruida sin diferencias ni huérfanos.
- PDF revisado visualmente en todas sus páginas.

[GitHub Actions: ejecución 36804375739, exitosa](https://github.com/JSebastianCCorrea/documentacion_arquitectura_modelo_datos/actions/runs/36804375739).

Commit de código comprobado: `a9660dc1be7a75f75c6e730fd09800ddf71ff1bd`. Ejecución terminada el 30 de septiembre de 2026, hora de Colombia; los logs expresan su fecha en UTC.

Artefacto: `arquitectura-modelo-36804375739-1`, ID `11136618535`, 8.216.366 bytes, retención de 30 días. Se descargó y se comparó con la entrega local: CSV y PDF idénticos byte a byte; las 2.759.400 celdas de la vista SQLite son iguales. Los binarios SQLite pueden tener distinta huella entre versiones de motor; la comparación se realiza sobre tipos, claves y valores, no sobre una equivalencia ficticia de sus archivos.

El detalle está en `src/static/auditoria/remote_verification.json`. El commit que agrega este registro modifica solo documentación y evidencia de verificación; Actions vuelve a ejecutarse automáticamente.

## Qué entregar

Proporciona la URL del repositorio. El PDF está dentro de `sebastian_clavijo_correa/docs`, como indica la estructura. El ZIP local contiene los archivos del repositorio, sin `.git`, entornos ni carpetas temporales.

No se ha pulsado Cargar Tarea ni Enviar en la plataforma educativa.
