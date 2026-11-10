# Contrato del prompt — equipo 2

Producto: dashboard Streamlit «Banco Siete · Plataforma de Créditos Hipotecarios» sobre HMEQ (5,960 solicitudes; `BAD` = incumplimiento).

## Qué debe mostrar

Acceso simulado por rol (usuario y contraseña `demo123`). Cada pantalla abre con una pregunta, indicadores con semáforo y, debajo, la evidencia (gráfica o tabla). Todas muestran la fecha de actualización (hoy, hora de Ciudad de México) y la fuente con el número de solicitudes.

| Pantalla (rol) | Componentes | Estados | Decisión que habilita |
|---|---|---|---|
| Inicio de sesión (todos) | Usuario, contraseña, botón «Iniciar sesión», ayuda con los usuarios de demostración. | Error de credenciales. | Acceso a la pantalla del rol. |
| Resumen (Analista) | 4 indicadores con semáforo (solicitudes, tasa de incumplimiento, perfiles prioritarios, solicitudes sin dato de deuda/ingreso); cadena solicitudes → incumplen → tasa; tabla «Dónde mirar primero» (8 grupos). | Con filtros activos: aviso «Estás viendo X de Y». Sin ningún grupo en alerta: mensaje. Sin resultados: advertencia. | ¿Dónde enfoco la revisión hoy? |
| Mapa de riesgo (Analista) | Mapa de calor deuda sobre ingreso (6 filas) × líneas morosas (5 columnas) con totales; «Lectura rápida» con los 3 perfiles de mayor tasa. | Casilla con menos de 30 solicitudes: gris, «pocos datos». Perfil prioritario: borde negro. | ¿Qué combinación de deuda y morosidad requiere evaluación detallada? |
| Perfiles a revisar (Analista) | Selector (Prioritarios / Prioritarios y a vigilar / Todos); tabla con selección de fila; detalle: tasa, comparación contra la cartera, contra el mismo nivel de deuda y la misma morosidad, desglose por motivo del préstamo, lista de solicitudes (hasta 300), nota, tres botones de decisión, registro de decisiones. | Sin perfiles en la lista; motivo con n < 30: «pocos datos». | Enviar a evaluación detallada, mantener condiciones o solicitar información adicional. |
| Desempeño del modelo (Analista) | AUC, recall, precisión y umbral, cada uno contra su meta; matriz de confusión; frase que explica cada métrica. Lee `modelo_sas.json`. | Valor `null`: «Pendiente». Matriz que no coincide con recall/precisión: advertencia. | ¿Cuánto puedo confiar en el modelo como apoyo? (no aprueba ni rechaza) |
| Comparativo de cartera (Gerente) | 3 indicadores; gráfico de puntos (solicitudes × tasa, con franjas del semáforo y la línea «Cartera»); tabla de grupos con atención; descarga CSV; barras por tipo de grupo en un desplegable. | Sin grupos en alerta: mensaje. | ¿A qué segmentos dirijo la atención? |
| Seguimiento de cartera (Supervisor) | 4 indicadores (prioritarios, a vigilar, normales, en seguimiento); filtro por estado; tabla con selección múltiple; botones «Marcar seleccionados» y «Quitar de seguimiento»; descargas CSV. | Sin selección: botones desactivados. | ¿Qué grupos marco para seguimiento? |
| Transversal | Botón «Filtros» (monto, motivo, ocupación, valor de la propiedad, valor sin dato), con el número de filtros activos y «Restablecer»; glosario en el menú lateral; cerrar sesión. | Sin filtros: toda la cartera. | — |

Reglas de negocio (no negociables):
- Tasa = incumplimientos ÷ solicitudes. Referencia = tasa de la cartera con los filtros actuales.
- Semáforo por `razón = tasa del grupo ÷ tasa de la cartera`: **Prioritario** ≥ 1.5×, **Vigilar** de 1.15× a 1.5×, **Normal** < 1.15×, **Pocos datos** si el grupo tiene menos de 30 solicitudes.
- Casos de más = solicitudes × (tasa del grupo − tasa de la cartera).
- Cortes fijos: deuda sobre ingreso < 30 / 30–35 / 35–40 / 40–45 / > 45 % y «Sin dato»; monto < 15 / 15–25 / 25–40 / > 40 mil; líneas morosas 0 / 1 / 2 / 3 o más / «Sin dato».
- «Sin dato» es una categoría propia: no se imputa ni se mezcla con 0.
- Perfil prioritario = combinación deuda sobre ingreso × líneas morosas con al menos 30 solicitudes y razón ≥ 1.5×.
- Permisos por rol: el gerente y el supervisor no ven créditos individuales.
- Sin emojis; azul profundo y blanco; títulos en serif; semáforo en verde, ámbar y rojo.

## El diseño de lo que debe arrojar

Orden general de cada pantalla: pregunta → indicadores → evidencia (gráfica o tabla) → fuente y número de solicitudes al pie.

| Salida | Columnas, en este orden | Orden de filas | Unidades |
|---|---|---|---|
| Tabla de grupos (Resumen, Gerente) | Alerta · Grupo · (Variable) · Solicitudes · Tasa de incumplimiento · Dicho fácil · × la cartera · Casos de más | Casos de más, de mayor a menor | Solicitudes: entero. Tasa: % sin decimales, con barra. Dicho fácil: «1 de cada N» o «N de cada 10». × la cartera: 1 decimal. Casos de más: entero. |
| Tabla de perfiles | Alerta · Perfil · Solicitudes · Tasa · × cartera · Casos de más | Casos de más, de mayor a menor | Igual que arriba. |
| Tabla del supervisor | Seguimiento · Alerta · Grupo · Variable · Solicitudes · Tasa · Dicho fácil · × la cartera | Tasa, de mayor a menor | Igual que arriba. |
| Indicadores | Título · valor · punto de semáforo con su referencia · una línea de ayuda | Izquierda a derecha por importancia | Tasa con 1 decimal; porcentajes sin decimales. |
| Mapa de calor | Filas: deuda sobre ingreso (6). Columnas: líneas morosas (5) + «Todas». Cada casilla: tasa, × la cartera y n. | Filas de menor a mayor deuda | % sin decimales; × con 1 decimal. |
| Exportaciones CSV | Dimensión · Etiqueta · Solicitudes · Incumplimientos · Tasa · Razón vs cartera · Nivel | Tasa descendente | Tasa como decimal (0–1). |

Cifras de control con la cartera completa y sin filtros: 5,960 solicitudes; 1,189 incumplimientos (19.95 %); 7 grupos prioritarios, 4 a vigilar y 14 normales; 9 perfiles prioritarios con 1,443 solicitudes; sin dato de deuda sobre ingreso: 1,267 solicitudes con 62.0 % de incumplimiento.

## El prompt, literal

Los mensajes que dirigieron esta versión. Se escribieron originalmente en francés y aquí se presentan traducidos al español, sin otra edición:

1. [PEGAR AQUÍ el primer mensaje que pidió el tablero de Streamlit con los roles Analista, Gerente y Supervisor, tal como está en el historial del chat.]

2. «Hay que cambiar el nombre de las variables para alguien que no conoce su significado ... Agregar una razón (ratio) para los datos. Hay que crear una identidad visual para el dashboard. Todos los KPI deben existir en relación con un benchmark (un semáforo o algo así). Las cifras tienen que explicarse solas. Se pueden dividir las pantallas del analista en varias. Los filtros no deben ser tan visibles. La pantalla de los gerentes debe simplificarse, más concisa. Todo debe ser autoexplicativo xD. Hay que poder observar las relaciones entre todas las cifras de un vistazo. Mostrar los casos en una tabla en lugar de hacer scroll.» (el texto completo está en el historial; los puntos suspensivos son un recorte de esta copia)

3. «¿Puedes usar los colores de esta imagen para la identidad visual (y la tipografía también, si es posible) y eliminar los emojis si hay? El profe me dijo que los banqueros eran gente seria y todo eso.»

### Prompt de especificación (para reproducir el tablero desde cero)

> Construye una aplicación Streamlit de un solo archivo `app.py` (con `streamlit`, `plotly`, `pandas`, `numpy`) llamada «Banco Siete · Plataforma de Créditos Hipotecarios», que lee `hmeq_preparado_1_con_motivo.csv` (5,960 filas; `BAD` = incumplimiento; columnas `*_FALTANTE` marcan valores que venían vacíos). Implementa acceso simulado por rol (`analista`, `gerente`, `supervisor`, contraseña `demo123`) y las pantallas y reglas descritas arriba en «Qué debe mostrar» y «El diseño de lo que debe arrojar». Usa lenguaje claro para nombres de variables («Deuda sobre ingreso», «Líneas de crédito morosas», «Ocupación del cliente», «Motivo del préstamo», «Monto solicitado»), muestra cada tasa también como «1 de cada N» y como «× la cartera», compara cada indicador con una referencia y un punto de semáforo, pon los filtros en un botón discreto, muestra los casos en tablas completas sin scroll interno, no uses emojis y usa azul profundo y blanco con títulos en serif. La fecha de actualización es la del día. La pantalla de desempeño del modelo lee `modelo_sas.json` y muestra «Pendiente» donde un valor sea `null`. Antes de responder, verifica con las cifras de control que la cartera sin filtros da 5,960 solicitudes y 19.95 %.

## Qué devolvió

Un `app.py` de unas 800 líneas con las siete pantallas, el semáforo, los filtros en un botón, el glosario y las tablas con selección de filas. Pasó las pruebas automáticas por rol y las capturas de pantalla.

## Qué cambiamos de lo que devolvió

- La primera versión mezclaba el dato imputado de morosidad con «0» y usaba un umbral de 1.2 en lugar de 1.15; se corrigió a 1.15 y «Sin dato» pasó a ser una categoría.
- El control de valor de la propiedad excluía las solicitudes de mayor valor (la app en línea mostraba 5,953 en lugar de 5,960); se redondean los límites al paso del control y no se filtra si no se toca.
- La leyenda «Cómo leer las gráficas» nunca se mostraba por una condición mal escrita.
- El logo salía con fondo negro al convertirlo de RGBA; se compuso sobre blanco.
- Etiquetas ambiguas («1», «3 o más») se reemplazaron por nombres completos.
- Se quitaron los emojis del semáforo y de los botones; las columnas de las tablas se ajustaron para que no se corten.
- Los resultados del modelo se tomaron del reporte de SAS; precisión y recall se calcularon a partir de FDR y F1, no se leyeron directamente, y la matriz de confusión sigue pendiente.

## Qué decidimos nosotros y no el modelo

- Usar Streamlit como entrega y desplegarlo en Streamlit Cloud desde GitHub.
- Mostrar datos reales de HMEQ en lugar de las cifras del mockup (el mockup decía 5,123 solicitudes y 19.8 %; los datos dan 5,960 y 19.95 %).
- Las reglas de alerta (≥ 1.5× prioritario; 1.15–1.5× vigilar), el mínimo de 30 solicitudes y los cortes fijos de deuda sobre ingreso y monto, definidos en el Cierre de Condiciones.
- Qué es un «perfil prioritario» y su umbral.
- Mantener «Sin dato» como categoría visible y no imputarla.
- Que el tablero apoya la decisión y no aprueba ni rechaza solicitudes.
- Las metas del modelo (AUC ≥ 0.85, recall ≥ 0.70) y la línea base del 19.95 %.
- Qué hacer con la contradicción entre el informe (5,958 solicitudes, 19.92 %) y la app (5,960, 19.95 %). [EQUIPO: indicar cuál se mantiene.]
- Los umbrales del indicador «Perfiles prioritarios» (verde < 10 %, ámbar < 25 % de las solicitudes) los propuso el asistente. [EQUIPO: confirmar o cambiar en `PESO_PRIORITARIOS`.]
