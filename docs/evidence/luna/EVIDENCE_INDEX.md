# Evidencias de Luna Martínez

Las salidas se obtuvieron con datos simulados. La muestra de 12 mesas sirve para verificar el método. La ejecución del pipeline usa el conjunto del proyecto o un escenario generado de forma reproducible.

| Evidencia guardada | Qué se verificó |
| --- | --- |
| [01_iqr_alerts.csv](01_iqr_alerts.csv) | Una alerta estadística para M007. Su tasa es 1,15 y el límite superior es aproximadamente 0,78125. |
| [02_descriptive_summary.json](02_descriptive_summary.json) | 12 tasas finitas, una superior al 100 % y participación media de 71,51 %. |
| [03_pytest.txt](03_pytest.txt) | 24 pruebas de Luna aprobadas. |
| [04_notebook_execution.txt](04_notebook_execution.txt) | Las cuatro celdas de código ejecutadas en IPython 9.10.0. El [notebook](../../../notebooks/luna_exploratory_analysis.ipynb) conserva las salidas de esa ejecución. |
| [05_pytest_integration.txt](05_pytest_integration.txt) | Ocho pruebas de integración del repositorio aprobadas. |
| [06_pipeline_partial.txt](06_pipeline_partial.txt) | Pipeline de 500 registros con IQR y análisis ejecutados. El modo completo devuelve código 2 e identifica las etapas pendientes. |
| [07_pipeline_low_turnout.txt](07_pipeline_low_turnout.txt) | Escenario de 240 registros generado con semilla 19. En REC-0240 se usaron 25 votos coherentes y 500 electores, y la evaluación registró un verdadero positivo exclusivo del IQR. |

## Reproducción y capturas pendientes

Desde la raíz de esta copia del repositorio, activa el entorno donde instalaste `requirements.txt`. Ejecuta:

```bash
python -m pytest -q tests/test_statistics.py tests/test_analysis.py
python -m pytest -q tests/test_integration.py
python -m src.main --output-dir outputs/temp/luna/verify
jupyter lab
```

En JupyterLab abre `notebooks/luna_exploratory_analysis.ipynb`, elige el kernel Python del entorno y usa **Restart Kernel and Run All Cells**. Durante esta verificación, el arranque estándar del kernel se quedó en `socket.accept` al construir el bucle de eventos de Windows. Las cuatro celdas se ejecutaron en orden mediante `IPython.core.interactiveshell.InteractiveShell.run_cell` y el archivo resultante se validó con `nbformat`.

La autorización de la ventana de captura expiró. Para completar las capturas, guarda estos PNG en esta carpeta:

1. `01_iqr_alerts.png` con la celda de alertas y la fila M007, incluido el umbral.
2. `02_descriptive_summary.png` con la celda del JSON y sus conteos y cuartiles.
3. `03_pytest.png` con el comando de pruebas de Luna y el resultado de pytest.
4. `04_notebook_executed.png` con el nombre del notebook, los números de ejecución y la salida de M007 y M008 visible.

## Notas para el informe compartido

- El IQR compara únicamente la tasa de cada registro con los límites derivados de su distribución. Usa cuartiles lineales, exige al menos cuatro tasas finitas y alerta solo fuera de los límites. Con IQR cero los dos límites coinciden. Las tasas finitas por debajo de 0 o por encima de 1 siguen en el cálculo. El detector exige `record_id` únicos y admite `station_id` repetidos.
- M007 entró en la cola superior. En M008 se reportaron 154 votos frente a 124 papeletas sumadas, y su participación de 73,33 % quedó dentro de los límites. Las reglas de consistencia complementan al IQR en ese caso.
- En los 500 registros del repositorio, el IQR no generó alertas y la validación de Diana cubrió las 25 anomalías inyectadas, con un falso positivo. En el escenario controlado de participación baja, el IQR añadió una detección con conteos coherentes. Estos resultados corresponden a dos distribuciones simuladas concretas.
- Las diferencias legítimas entre grupos pueden producir falsos positivos. Los cuartiles se desplazan cuando hay muchas observaciones anómalas o cuando cambia la composición del conjunto. Las alertas indican casos para revisar y por sí solas no establecen fraude.
