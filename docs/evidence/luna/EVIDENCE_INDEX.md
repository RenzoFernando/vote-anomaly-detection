# Evidencias de Luna Martínez

Las ejecuciones se hicieron el 26 de noviembre de 2026 en Windows con Python 3.13.9 de Anaconda, pandas 2.3.3 y NumPy 2.3.5.

| Evidencia de ejecución | Resultado |
| --- | --- |
| [01_iqr_alerts.csv](01_iqr_alerts.csv) y [02_descriptive_summary.json](02_descriptive_summary.json) | Comprobación auxiliar con 12 registros. M007 alertó con una tasa de 115 % y un límite superior de 78,125 %. |
| [03_pytest.txt](03_pytest.txt) | 26 pruebas de Luna aprobadas, incluidas dos pruebas a través del pipeline con los módulos reales. |
| [04_notebook_execution.txt](04_notebook_execution.txt) | Cuatro celdas de código ejecutadas con el kernel `python3` y verificadas con `nbformat`. El [notebook](../../../notebooks/luna_exploratory_analysis.ipynb) conserva las salidas. También se comprobó **Run All** en VS Code con el kernel de Anaconda. |
| [05_pytest_integration.txt](05_pytest_integration.txt) | Ocho pruebas de integración de Renzo aprobadas. |
| [06_pipeline_partial.txt](06_pipeline_partial.txt) | 500 registros de Diana. Las etapas de análisis e IQR se ejecutaron. Los cuatro archivos exportados coinciden byte a byte con los de la ejecución del equipo en el notebook. |
| [07_pipeline_low_turnout.txt](07_pipeline_low_turnout.txt) | Una alerta IQR para REC-0240, con 25 votos coherentes, 500 electores y un límite inferior de 35,48 %. La evaluación registró un verdadero positivo adicional. |
| [08_pytest_full.txt](08_pytest_full.txt) | Las 56 pruebas de la suite completa pasaron. |

## Capturas de VS Code

- [01_iqr_alerts.png](01_iqr_alerts.png) muestra la alerta de REC-0240 y la evaluación del escenario controlado.
- [02_descriptive_summary.png](02_descriptive_summary.png) muestra el resumen exportado de los 500 registros.
- [03_pytest.png](03_pytest.png) muestra la transcripción real de la suite completa abierta en el editor.
- [04_notebook_executed.png](04_notebook_executed.png) muestra el kernel seleccionado, los indicadores de ejecución y la vista previa de los registros preparados.

## Reproducción

Desde la raíz, con las dependencias de `requirements.txt` instaladas en el entorno activo, ejecuta:

```bash
python -m pytest -q tests/test_statistics.py tests/test_analysis.py tests/test_luna_pipeline.py
python -m pytest -q tests/test_integration.py
python -m pytest -q
python -m src.main --output-dir outputs/temp/luna/verify
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=60 notebooks/luna_exploratory_analysis.ipynb
```

En VS Code, abre el notebook, elige el kernel con las dependencias y pulsa **Run All**. El notebook guarda el conjunto del equipo en `outputs/temp/luna/notebook/team/results/` y el escenario controlado en `outputs/temp/luna/notebook/low-turnout/results/`. Cada ejecución exporta los registros preparados, las alertas, las métricas y el informe HTML.

En `metrics.json`, revisa `analysis`, `stages.statistical`, `stages.analysis` y `breakdown.by_method.statistical`. En `alerts.csv`, verifica las columnas `record_id`, `method` y `reason` en ese orden. En el conjunto del equipo el filtro `method == "statistical"` queda vacío. En el caso controlado incluye REC-0240. El modo `--require-complete` devolvió código 2 e identificó las etapas pendientes de reglas y visualizaciones. La ejecución parcial utilizó `diana_validation_baseline` para las reglas.

## Notas para el informe

- En el conjunto del equipo la participación media fue de 72,33 %, con Q1 de 63,09 % y Q3 de 81,77 %. Cuatro tasas superaron el 100 %. El límite superior del IQR fue de 109,80 %, por lo que esas cuatro tasas quedaron dentro de los límites, al igual que el resto de las observaciones.
- El IQR usa cuartiles lineales y exige al menos cuatro tasas finitas. Los límites se incluyen en el intervalo y coinciden si IQR vale cero. El método admite tasas finitas fuera de `[0, 1]` y requiere `record_id` únicos. Las repeticiones de `station_id` se revisan en la validación.
- La baja participación de REC-0240 produjo una alerta por debajo del límite inferior pese a que sus conteos eran coherentes. En la muestra auxiliar, M008 mostró 154 votos reportados frente a 124 papeletas sumadas, con una participación de 73,33 % dentro de los límites. Los dos casos ilustran qué observa cada método.
- Los cuartiles dependen de la distribución. Las diferencias legítimas entre grupos pueden generar falsas alarmas. Las alertas de estos escenarios simulados identifican registros para revisión.

## Respaldo local de la copia temporal

Se comprobó que los 13 commits accesibles de `tmp/luna-work` y sus ocho archivos de evidencia registrados estaban en el historial del repositorio original. Se respaldaron los 137 archivos de salida ignorados por Git en `outputs/temp/luna/archive/previous-run-outputs.zip` y se comprobó cada entrada con SHA-256. La copia preexistente se retiró de la raíz mediante un traslado a la carpeta temporal de Windows.
