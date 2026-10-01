# Documentación de arquitectura y modelo de datos

**Juan Sebastian Clavijo Correa · Infraestructura y Arquitectura para Big Data · IUDigital**

En esta entrega reuní el trabajo de ingesta, limpieza y enriquecimiento de las actividades anteriores. El [documento principal](sebastian_clavijo_correa/docs/arquitectura_modelo.pdf) explica cómo se conectan esas fases y cómo organicé el resultado en SQLite.

El proyecto trabaja con 43.800 registros por hora de cinco ciudades durante 2025. El conjunto enriquecido tiene 63 columnas y se guarda también una muestra de 1.200 filas. La energía fue simulada para el ejercicio; no corresponde a mediciones reales de consumo.

La carpeta **sebastian_clavijo_correa** contiene el código y las evidencias de la actividad. Su [README](sebastian_clavijo_correa/README.md) explica cómo clonar el repositorio, instalar las dependencias y ejecutar todo el proceso o solo el enriquecimiento.

- [Informe de arquitectura y modelo](sebastian_clavijo_correa/docs/arquitectura_modelo.pdf).
- [Diagramas y archivos editables](sebastian_clavijo_correa/docs/diagramas/).
- [Pruebas realizadas](sebastian_clavijo_correa/docs/PRUEBAS.md): 44 casos y comparación con las salidas anteriores.
- [Continuidad entre actividades](sebastian_clavijo_correa/docs/TRAZABILIDAD.md).
- [Datos de entrega y ejecución en GitHub](sebastian_clavijo_correa/docs/ENTREGA.md).

Conservé las bases DuckDB de las fases anteriores y agregué SQLite para el modelo final, con seis tablas relacionadas y una vista que reúne las 63 columnas. El proceso automático se encuentra en [.github/workflows/bigdata.yml](.github/workflows/bigdata.yml).
