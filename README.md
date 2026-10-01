# Documentación de arquitectura y modelo de datos

**Juan Sebastian Clavijo Correa · Infraestructura y Arquitectura para Big Data · IUDigital**

**Documento principal:** [arquitectura_modelo.pdf](sebastian_clavijo_correa/docs/arquitectura_modelo.pdf).

El [README del proyecto](sebastian_clavijo_correa/README.md) explica cómo clonar, instalar y ejecutar la cadena completa o únicamente el enriquecimiento. Se conserva la carpeta académica **sebastian_clavijo_correa** solicitada en la estructura de entrega.

- 43.800 registros horarios de cinco ciudades y 2025 completo.
- 63 columnas enriquecidas; muestra de 1.200 filas.
- SQLite: seis tablas con PK/FK y vista que reconstruye todos los valores.
- 44 pruebas locales y contraste con las salidas de las entregas previas.
- [Arquitectura](sebastian_clavijo_correa/docs/diagramas/arquitectura.pdf), [diagrama ER](sebastian_clavijo_correa/docs/diagramas/er.pdf) y fuentes .drawio.

La energía es sintética. Las bases DuckDB heredadas se conservan; SQLite materializa el modelo final. El workflow activo está en [.github/workflows/bigdata.yml](.github/workflows/bigdata.yml).

[Entrega y ejecución verificada](sebastian_clavijo_correa/docs/ENTREGA.md) · [Pruebas](sebastian_clavijo_correa/docs/PRUEBAS.md) · [Trazabilidad](sebastian_clavijo_correa/docs/TRAZABILIDAD.md)
