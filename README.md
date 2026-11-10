https://a01769825-banco-siete-streamlit-v2-app-nefmr1.streamlit.app/

# Banco Siete · Plataforma de Créditos Hipotecarios (Equipo 2)

Dashboard en Streamlit sobre el conjunto HMEQ (5,960 solicitudes de crédito con garantía hipotecaria). Proyecto TI3008C, socio formador SAS Data and AI Solutions.

## Versiones

| Versión | URL | Qué es |
|---|---|---|
| **v2 (entrega)** | https://a01769825-banco-siete-streamlit-v2-app-nefmr1.streamlit.app/ | Incorpora las observaciones del profesor Juan Vélez. Es la que se evalúa. |
| v1 (exposición del 21 de octubre) | https://banco-siete.streamlit.app/ | Versión presentada; se conserva como punto de comparación. |

Lo que cambió de v1 a v2: nombres claros en lugar de códigos (glosario en el menú lateral); cada tasa con «1 de cada N» y «× la cartera»; semáforo con referencia en todos los indicadores; identidad visual azul y blanca con títulos en serif; analista de 2 a 4 pantallas; filtros en un botón discreto; gerente simplificado (3 indicadores, un gráfico de puntos y una tabla); casos en tablas sin scroll; supervisor con tabla de selección múltiple. Se mantienen los datos, las reglas (mínimo 30 solicitudes; prioritario ≥ 1.5×; vigilar 1.15–1.5×) y n = 5,960.

## Cómo entrar

La aplicación simula el acceso por rol (no es seguridad real). Usuarios de demostración, contraseña `demo123`:

| Usuario | Rol | Pantallas |
|---|---|---|
| `analista` | Analista | Resumen · Mapa de riesgo · Perfiles a revisar · Desempeño del modelo |
| `gerente` | Gerente | Comparativo de cartera |
| `supervisor` | Supervisor | Seguimiento de cartera |

Las credenciales también aparecen en la pantalla de inicio, en «Usuarios de demostración».

## Cómo correrlo en local

```
pip install -r requirements.txt
streamlit run app.py
```

## Objetivo de negocio

| | |
|---|---|
| **Línea base** | Tasa de incumplimiento de la cartera: **19.95 %** (1,189 de 5,960). Sin priorización, revisar el 24 % de las solicitudes al azar capturaría solo ~24 % de los incumplimientos. |
| **Meta** | (1) Que los perfiles prioritarios concentren **≥ 70 % de los incumplimientos con ≤ 25 % de las solicitudes** (hoy: 9 perfiles, 1,443 solicitudes = 24.2 %, que contienen 877 incumplimientos = 73.8 %; su tasa es 60.8 % contra 6.9 % en el resto). (2) Modelo de apoyo con **AUC ≥ 0.85 y recall ≥ 0.70** (hipótesis H4a; Gradient Boosting en validación: AUC 0.965). |
| **Decisión que habilita** | Analista: qué perfiles pasan a evaluación detallada. Gerente: a qué segmentos dirigir la atención. Supervisor: qué grupos marcar para seguimiento. El tablero no aprueba ni rechaza solicitudes. |

## Observaciones de la exposición del 21 de octubre: qué cambió y dónde quedó

| Observación recibida | Estado | Qué cambió | Dónde quedó |
|---|---|---|---|
| Las gráficas se confundían con el EDA; el EDA no era lo esencial. | Cerrada | Se eliminaron las gráficas de exploración por variable. Cada gráfica responde a una pregunta y a una decisión. | Analista › Mapa de riesgo (mapa de calor deuda sobre ingreso × líneas morosas); Gerente › gráfico de puntos por grupo. |
| Faltaba el flujo de los datos. | Parcial | Cadena solicitudes → incumplen → tasa, línea de referencia «Cartera», leyenda del semáforo con las reglas de alerta, fecha de actualización en cada pantalla y fuente al pie. El diagrama completo del flujo está en el documento de diseño. | Analista › Resumen; encabezado de todas las pantallas; `app.py` (`cargar`, `segmentos`, `leyenda`). |
| Flujo de pantallas no constante. | Cerrada | Un solo recorrido: inicio de sesión → pantalla del rol → detalle y regreso. Los filtros aplican igual en todas las pantallas. | Menú lateral y botón «Filtros» (arriba a la derecha). |
| El analista debe ver el desempeño del modelo. | Cerrada (falta la matriz) | Pantalla con AUC, recall, precisión, umbral y matriz de confusión, con una frase que explica cada métrica y la meta del equipo. Alcance: apoyo, no aprueba ni rechaza. | Analista › Desempeño del modelo; valores en `modelo_sas.json`. La matriz de confusión sigue «Pendiente». |
| Faltaba el recorrido del gerente. | Parcial | KPIs → gráfico de puntos con la cartera como referencia → tabla de segmentos ordenada por casos de más → descarga CSV. Sin créditos individuales. El detalle por segmento se ve en el tooltip y en las barras desplegables. | Gerente › Comparativo de cartera. |
| Faltaba el recorrido del supervisor. | Cerrada | Tabla con tasa contra la cartera, solicitudes y alerta; selección múltiple; marcar o quitar de seguimiento; descarga CSV. Sin gráficas en el tiempo (la base no tiene fechas). | Supervisor › Seguimiento de cartera. |

Observaciones adicionales de la retro y de la revisión del 4 de noviembre:

| Observación | Estado | Qué cambió / dónde |
|---|---|---|
| Filtros arriba, no tan visibles. | Cerrada | Botón «Filtros» discreto, arriba a la derecha, con el número de filtros activos. |
| Arriba siempre va lo más importante. | Cerrada | Indicadores (KPI) en la parte superior de cada pantalla. |
| Preguntas clave. | Cerrada | Cada pantalla tiene su pregunta bajo el título. |
| No incluir títulos en grande. | Cerrada | Títulos de sección de tamaño moderado. |
| Dashboard dinámico, botones a la granularidad. | Parcial | Clic en una fila de «Perfiles a revisar» abre su detalle. |
| No mezclar snapshots con gráficas en el tiempo. | Cerrada | No hay series de tiempo. |
| ¿Por qué no pensar en el solicitante? | Pendiente | No hay pantalla de solicitud individual. |
| Cambiar los nombres de variables para quien no los conoce. | Cerrada | «Deuda sobre ingreso», «Líneas de crédito morosas», etc., más glosario en el menú lateral. |
| Un ratio para los datos. | Cerrada | «1 de cada N» y «× la cartera». |
| Identidad visual. | Cerrada | Paleta azul y blanca, tipografía serif en títulos, sin emojis. |
| Cada KPI contra un benchmark, con semáforo. | Cerrada | Punto de color y referencia en cada indicador. |
| Cifras que se explican solas; relaciones de un vistazo. | Cerrada | Subtítulo con la pregunta, leyenda del semáforo, cadena solicitudes → incumplen → tasa. |
| Analista en varias pantallas. | Cerrada | Cuatro pantallas. |
| Gerente simplificado. | Cerrada | Tres KPIs, un gráfico y una tabla. |
| Casos en tabla en lugar de scroll. | Cerrada | Tablas con todas las filas visibles. |

## Archivos

- `app.py`: aplicación Streamlit.
- `hmeq_preparado_1_con_motivo.csv`: datos (HMEQ preparado, con `REASON_FALTANTE`).
- `modelo_sas.json`: resultados del modelo de SAS que se muestran en la pantalla del analista.
- `contrato-prompt.md`: especificación del producto (qué muestra y qué forma tiene la salida).
- `prompts/contrato-prompts.md`: registro de prompts por etapa.
- `.streamlit/config.toml`, `requirements.txt`, `logo.png`.

## Límites

El acceso por rol es una simulación y el repositorio es público (incluye los datos y las credenciales de demostración). Las decisiones y el seguimiento solo viven en la sesión del navegador.
