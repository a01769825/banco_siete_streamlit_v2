https://github.com/a01769825/banco_siete_streamlit_v2/actions/runs/45732855574

# Entregable 3 · Banco Siete: del tablero de buena calidad al producto

Equipo 2 · TI3008C · Este documento describe la versión del tablero con la que se entrega. Todo lo que aquí se afirma se puede comprobar en `app.py`, `paleta.py`, `scripts/verificar_contraste.py` y `tests/`.

## 1. Gráficas y la pregunta que responde cada una

La pregunta está escrita en la propia app, debajo del título de cada gráfica («Pregunta que responde: …»), tomada del diccionario `PREGUNTA` de `app.py`.

| Gráfica (pantalla) | Pregunta que responde |
|---|---|
| Incumplimiento por líneas morosas y reportes negativos (Hallazgos) | ¿Sube el incumplimiento cuando el cliente tiene más líneas morosas o más reportes negativos? |
| Incumplimiento por deuda sobre ingreso (Hallazgos) | ¿En qué rangos de deuda sobre ingreso se concentra el incumplimiento y qué pasa cuando falta el dato? |
| Incumplimiento por antigüedad crediticia (Hallazgos) | ¿Incumplen menos los clientes con un historial de crédito más antiguo? |
| Dato faltante de deuda sobre ingreso (Hallazgos) | ¿La falta del dato de deuda sobre ingreso concentra incumplimientos o es aleatoria? |
| Mapa de calor (Mapa de riesgo) | ¿Qué combinaciones de deuda sobre ingreso y líneas morosas incumplen más que la cartera? |
| Comparación del perfil (Nueva solicitud) | ¿Cuánto por encima de la cartera está este perfil y cómo se compara con grupos parecidos? |
| Matriz de confusión (Desempeño del modelo) | ¿Cuántos clientes que incumplen detecta el modelo y cuántas falsas alertas genera? |
| Burbujas de grupos (Perfiles a revisar) | ¿Qué grupos de clientes incumplen más que el resto y qué tan grandes son? |

## 2. Paleta inclusiva y contraste calculado

Los colores viven en `paleta.py`. El script `scripts/verificar_contraste.py` calcula la razón de contraste WCAG (L1+0.05)/(L2+0.05) de cada par y **falla el CI si alguno incumple**: 4.5:1 para texto normal (criterio 1.4.3) y 3:1 para elementos gráficos (1.4.11). La ejecución verde enlazada en la línea 1 es la evidencia. Resultado del último cálculo:

| Par | Primer plano | Fondo | Tipo | Razón | Mínimo | Resultado |
|---|---|---|---|---|---|---|
| Texto principal sobre blanco | `#0b1330` | `#ffffff` | texto | 18.26:1 | 4.5:1 | ✅ |
| Texto secundario sobre blanco | `#44506b` | `#ffffff` | texto | 8.06:1 | 4.5:1 | ✅ |
| Texto suave sobre blanco | `#5b6680` | `#ffffff` | texto | 5.74:1 | 4.5:1 | ✅ |
| Texto suave sobre fondo de tarjeta | `#5b6680` | `#f4f5fa` | texto | 5.27:1 | 4.5:1 | ✅ |
| Texto suave sobre azul claro | `#5b6680` | `#e6e9f7` | texto | 4.75:1 | 4.5:1 | ✅ |
| Texto de tarjeta sobre fondo de tarjeta | `#3a4468` | `#f4f5fa` | texto | 8.74:1 | 4.5:1 | ✅ |
| Azul de marca sobre blanco | `#0B1A8C` | `#ffffff` | texto | 13.63:1 | 4.5:1 | ✅ |
| Azul de marca sobre fondo de tarjeta | `#0B1A8C` | `#f4f5fa` | texto | 12.52:1 | 4.5:1 | ✅ |
| Texto blanco sobre azul de marca | `#ffffff` | `#0B1A8C` | texto | 13.63:1 | 4.5:1 | ✅ |
| Fecha del encabezado sobre azul | `#dbe5f5` | `#0B1A8C` | texto | 10.73:1 | 4.5:1 | ✅ |
| Subtítulo del encabezado sobre azul | `#c9d3f2` | `#0B1A8C` | texto | 9.14:1 | 4.5:1 | ✅ |
| Texto sobre etiqueta Prioritario | `#7a1f12` | `#f6cbc5` | texto | 7.02:1 | 4.5:1 | ✅ |
| Texto sobre etiqueta Vigilar | `#6b4e00` | `#fae6b4` | texto | 6.28:1 | 4.5:1 | ✅ |
| Texto sobre etiqueta Normal | `#1d5c3b` | `#d3ebdd` | texto | 6.31:1 | 4.5:1 | ✅ |
| Texto sobre etiqueta Pocos datos | `#4f586e` | `#eceff4` | texto | 6.17:1 | 4.5:1 | ✅ |
| Texto blanco sobre rojo (barras) | `#ffffff` | `#b3261e` | texto | 6.54:1 | 4.5:1 | ✅ |
| Texto blanco sobre gris (barras) | `#ffffff` | `#6b7488` | texto | 4.69:1 | 4.5:1 | ✅ |
| Rojo (Prioritario) como elemento gráfico | `#b3261e` | `#ffffff` | grafico | 6.54:1 | 3.0:1 | ✅ |
| Ámbar (Vigilar) como elemento gráfico | `#b26a00` | `#ffffff` | grafico | 4.24:1 | 3.0:1 | ✅ |
| Verde (Normal) como elemento gráfico | `#1e7b4b` | `#ffffff` | grafico | 5.26:1 | 3.0:1 | ✅ |
| Gris (Pocos datos) como elemento gráfico | `#6b7488` | `#ffffff` | grafico | 4.69:1 | 3.0:1 | ✅ |
| Azul de marca como elemento gráfico | `#0B1A8C` | `#ffffff` | grafico | 13.63:1 | 3.0:1 | ✅ |
| Línea de referencia de la cartera | `#333333` | `#ffffff` | grafico | 12.63:1 | 3.0:1 | ✅ |


**Corrección hecha:** la paleta anterior no cumplía (Ámbar 2.44:1, Verde 4.25:1 y Gris 3.06:1 sobre blanco). Se oscurecieron hasta pasar.

**Daltonismo:** el script simula protanopía, deuteranopía y tritanopía (matrices de Machado) y exige una diferencia de color ΔE (CIE76) ≥ 15 entre los cuatro niveles; el mínimo obtenido es 16.8. Además, **la identidad de la categoría no depende solo del color**: cada nivel lleva un símbolo (▲ Prioritario, ◆ Vigilar, ● Normal, ○ Pocos datos) en leyenda, celdas del mapa, etiquetas de barras, marcadores de burbujas, tablas y la ficha «Estado» de Nueva solicitud.

## 3. Jerarquía visual y su justificación

Aplicada en la app:
1. Lo primero que se ve en cada pantalla es el hallazgo o la métrica principal (título en negrita, mayor tamaño); la hipótesis y la pregunta van debajo en texto secundario más pequeño.
2. El color de énfasis (rojo) se reserva al nivel Prioritario; el resto de la interfaz usa azul de marca y grises neutros, para que lo urgente destaque.
3. Una línea de referencia punteada (promedio de la cartera) da el punto de comparación de todas las barras.
4. La lectura de filtros (cuántas solicitudes se ven) está siempre en la parte superior de la pantalla.

**Justificación con la investigación 1:** *(el equipo debe verificar que estas fuentes coincidan con su investigación 1 y agregar las suyas; las de abajo se consultaron el 25/11/2026)*
- *Jerarquía visual y dónde mirar:* el Nielsen Norman Group señala que si cuesta trabajo saber dónde mirar en una página, probablemente al diseño le falta una jerarquía visual clara (cita de Kelley Gordon, NN/g, recogida por la Interaction Design Foundation: https://ixdf.org/literature/topics/visual-hierarchy). → Por eso cada pantalla abre con el hallazgo/métrica principal y deja lo secundario en texto menor (puntos 1 y 4).
- *Patrones de lectura:* los estudios de seguimiento ocular de NN/g (2006) muestran que la gente escanea en patrón F en contenido denso y salta entre encabezados («layer-cake»), por lo que los encabezados funcionan como mapa (resumido en https://www.designyourway.net/blog/visual-hierarchy/). → Títulos de hallazgo en negrita y la lectura de filtros al inicio (puntos 1 y 4).
- *Énfasis y proximidad:* los principios de jerarquía (tamaño, color, agrupación por proximidad; origen en la Gestalt) se explican en https://thedecisionlab.com/reference-guide/design/visual-hierarchy y https://www.toptal.com/designers/ui/golden-ratio-in-design. → Rojo reservado al nivel Prioritario y tarjetas agrupadas por tema (punto 2).
- *Contraste y no depender del color:* W3C WCAG 2.2, SC 1.4.3 (texto 4.5:1; texto grande 3:1) https://www.w3.org/wai/wcag22/understanding/contrast-minimum.html y SC 1.4.11 (elementos gráficos significativos 3:1) https://w3.org/WAI/WCAG22/Understanding/non-text-contrast. → Sección 2.

## 4. Estado «nada seleccionado»

Si los filtros dejan cero solicitudes, la app lo **declara por escrito** («Con estos filtros no hay solicitudes, así que no hay nada que mostrar…») y **se detiene con `st.stop()`** para que no se dibuje ninguna gráfica vacía ni se produzca un error. Está en `main()` de `app.py` (bloque `if d.empty:` seguido de `st.stop()`, cerca de la línea 1436). Verificado por la prueba `test_estado_vacio_se_declara_y_se_detiene` en `tests/test_app.py` (se ejecuta en el CI).

## 5. Dos controles ligados a una decisión de negocio

| Control (Filtros) | Decisión que habilita | Filtro activo y conteo visible |
|---|---|---|
| Monto solicitado | Qué tramo de monto revisar primero o qué límite de crédito autorizar por tramo. | Al cambiarlo aparece «Estás viendo N de M solicitudes (X%). Filtros activos (k): Monto…» |
| Ocupación del cliente | En qué segmento de clientes concentrar la revisión de expedientes. | Igual: el aviso lista cada filtro activo y el conteo; sin filtros dice «Filtros activos: ninguno». |

Cada control tiene el texto de ayuda con su decisión (`help=` en `app.py`). El conteo vive en `lectura_filtros()`.

## 6. Acceso por persona: matriz por rol y limitación

| Pantalla | Analista | Gerente | Supervisor |
|---|---|---|---|
| Portafolio | ✔ | | |
| Mapa de riesgo | ✔ | | |
| Perfiles a revisar | ✔ | | |
| Nueva solicitud | ✔ | | |
| Desempeño del modelo | ✔ | | |
| Comparativo de cartera | | ✔ | |
| Seguimiento de cartera | | | ✔ |

**Mecanismo.** Cada persona tiene su propia cuenta. Las cuentas viven en `st.secrets` (configuración del host, **nunca en el repositorio**): usuario, rol y el *hash* de la contraseña (PBKDF2-SHA256 con sal aleatoria y 600 000 iteraciones; comparación con `hmac.compare_digest`). El rol sale de la cuenta, no de un selector. La matriz `PANTALLAS` se aplica en el servidor: el menú solo muestra las pantallas del rol y, además, `main()` se detiene (`st.stop()`) si la pantalla pedida no pertenece al rol. Hay un límite de 5 intentos fallidos por sesión. Sin secretos configurados, la app se detiene con un mensaje.

**Rebanada funcional que distingue dos roles:** un Analista ve cinco pantallas y un Gerente solo «Comparativo de cartera»; lo comprueba `test_roles_ven_menus_distintos`.

**Limitaciones (declaradas):**
- El plan gratuito de Streamlit Community Cloud **no tiene autorización por rol** propia; el control es el de la aplicación, no el de la plataforma.
- El contador de intentos es por sesión: quien recargue la página lo reinicia. No hay bloqueo global por cuenta.
- Quien tenga la URL llega a la pantalla de inicio de sesión: una URL difícil de adivinar no es control de acceso.
- Las cuentas y hashes se administran a mano en los secretos del host; no hay recuperación de contraseña, expiración ni doble factor.
- La contraseña de demostración anterior sigue en el historial de git: por eso las cuentas nuevas usan contraseñas distintas.
- Los datos son el conjunto público HMEQ, sin datos personales reales.

## Prompts e investigación 3
Ver `prompts/B3.md` (incluye las fuentes de autenticación: OWASP, documentación de Streamlit).
