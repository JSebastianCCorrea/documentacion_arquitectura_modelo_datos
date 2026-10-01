# Entrega de la actividad de enriquecimiento

**Autor:** Juan Sebastian Clavijo Correa.

La URL para entregar en la plataforma educativa es [https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube](https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube). La carpeta `sebastian_clavijo_correa` contiene el proyecto con la estructura solicitada. El workflow ejecutable permanece también en la raíz del repositorio; las dos copias se comparan en cada ejecución.

## Resultado verificado

La ejecución de [GitHub Actions del 23 de septiembre de 2026](https://github.com/JSebastianCCorrea/Enriquecimiento_Datos_Plataforma_Big_Data_Nube/actions/runs/35820741385) terminó correctamente sobre el commit `28f7c01364346cd07c77be610698cd370e65e31a`. Instaló las dependencias en Ubuntu con Python 3.12, ejecutó las 25 pruebas, regeneró las salidas, verificó sus contratos y publicó el artefacto de evidencias. Los resultados locales se conservan en el repositorio; los archivos del artefacto corresponden a la ejecución remota.

| Entregable | Ubicación dentro del proyecto |
|---|---|
| Código de integración | `src/enrichment.py` |
| Muestra de 1.200 registros | `src/xlsx/enriched_data.xlsx` y `.csv` |
| Conjunto completo de 43.800 registros y 63 columnas | `src/data/enriched_full.csv` |
| Auditoría de los seis cruces | `src/static/auditoria/enriched_report.txt` |
| Comprobaciones de integridad | `src/static/auditoria/verification.json` |
| Registro de las 25 pruebas | `src/static/auditoria/tests.log` |
| Fuentes, método, diccionario y pruebas | `docs/` |

Las 32 columnas originales se conservan. Cada una de las seis fuentes encontró correspondencia para los 43.800 registros, sin multiplicar filas. El resultado incorpora JSON, XLSX, CSV, XML, HTML y TXT. La muestra tiene 20 observaciones por ciudad y mes; la hoja `Cobertura` incluye los pesos para interpretar ese muestreo.

## Cómo revisar la automatización

1. Abrir la ejecución de Actions enlazada arriba.
2. Consultar los pasos de pruebas, enriquecimiento y verificación.
3. Descargar `evidencias-enriquecimiento-35820741385-1` desde **Artifacts**. La retención configurada es de 30 días; después se puede volver a ejecutar el workflow.
4. Revisar `verification.json`, `tests.log`, la auditoría y los datos del artefacto.

El repositorio incluye todos los insumos necesarios para repetir el proceso, siguiendo el [README](../README.md). La copia ZIP local se denomina `ClavijoCorrea_JuanSebastian_Enriquecimiento.zip` y contiene los archivos versionados del proyecto, sin el historial de Git ni entornos virtuales.

La energía continúa siendo sintética y la información solar es retrospectiva. El enriquecimiento añade contexto; su utilidad predictiva se deberá evaluar en la etapa de modelado. La [metodología](METODOLOGIA.md) explica cómo evitar usar información futura en esa etapa.
