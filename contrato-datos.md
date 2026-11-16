# Contrato de datos — Tablero Banco Siete (Equipo 2)

Este contrato dice qué columnas trae el archivo del tablero, de qué tipo son, en qué unidad están, de dónde vienen y qué significa un valor vacío. Lo usan dos cosas:

- **La app** (`app.py`): antes de dibujar cualquier pantalla revisa el archivo contra este contrato. Si no cumple, muestra el error y no dibuja nada.
- **El pipeline** (`.github/workflows/validar-datos.yml`): en cada cambio al repositorio corre `validar_datos.py`, que hace la misma revisión. Si falla, la corrida sale en rojo.

Las dos usan la misma función (`validacion.py`), que lee la tabla de la sección 1 de este archivo. **Si se cambia una columna, se cambia aquí primero.**

Archivo: `hmeq_preparado_1_con_motivo.csv` · 5,960 filas · 26 columnas · fuente: base HMEQ (SAS), preparada en la Entrega 2.

## 1. Columnas del archivo

Tipo `entero` = número sin decimales; `decimal` = número con decimales; `bandera` = 0 o 1. Ninguna columna puede venir como texto.

| Columna | Tipo | Unidad | Mín | Máx | Origen | Vacío significa |
|---|---|---|---|---|---|---|
| `BAD` | bandera | 1 = incumplió, 0 = pagó | 0 | 1 | Archivo HMEQ | No permitido: sin esta columna no hay tasa |
| `LOAN` | entero | USD | 1 | | Archivo HMEQ | No permitido: toda solicitud tiene monto |
| `MORTDUE` | decimal | USD | 0 | | Archivo HMEQ, imputado con mediana | No recuperable: no tiene columna `_FALTANTE` |
| `VALUE` | decimal | USD | 0 | | Archivo HMEQ, imputado con mediana | No hay dato si `VALUE_FALTANTE = 1` |
| `YOJ` | decimal | años en el empleo | 0 | 80 | Archivo HMEQ, imputado con mediana | No hay dato si `YOJ_FALTANTE = 1` |
| `DEROG` | entero | reportes negativos | 0 | | Archivo HMEQ, imputado con 0 | No hay dato si `DEROG_FALTANTE = 1` (no es cero) |
| `DELINQ` | entero | líneas de crédito morosas | 0 | | Archivo HMEQ, imputado con 0 | No hay dato si `DELINQ_FALTANTE = 1` (no es cero) |
| `CLAGE` | decimal | meses de la línea más antigua | 0 | | Archivo HMEQ, imputado con mediana | No recuperable: no tiene columna `_FALTANTE` |
| `NINQ` | entero | consultas de crédito recientes | 0 | | Archivo HMEQ, imputado con 0 | No hay dato si `NINQ_FALTANTE = 1` (no es cero) |
| `CLNO` | entero | líneas de crédito | 0 | | Archivo HMEQ, imputado con mediana | No recuperable: no tiene columna `_FALTANTE` |
| `DEBTINC` | decimal | % (deuda sobre ingreso) | 0 | | Archivo HMEQ, imputado con mediana (34.93) | No hay dato si `DEBTINC_FALTANTE = 1`; se asocia con riesgo alto |
| `_PartInd_` | bandera | 1 = entrenamiento, 0 = validación | 0 | 1 | Partición de SAS | No permitido |
| `VALUE_FALTANTE` | bandera | 1 = no había dato | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `DEBTINC_FALTANTE` | bandera | 1 = no había dato | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `NINQ_FALTANTE` | bandera | 1 = no había dato | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `DEROG_FALTANTE` | bandera | 1 = no había dato | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `DELINQ_FALTANTE` | bandera | 1 = no había dato | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `YOJ_FALTANTE` | bandera | 1 = no había dato | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `JOB_FALTANTE` | bandera | 1 = no había ocupación | 0 | 1 | Calculada en la Entrega 2 | No permitido |
| `JOB_Office` | bandera | 1 = oficina | 0 | 1 | Archivo HMEQ (dummy) | No permitido |
| `JOB_Other` | bandera | 1 = otro | 0 | 1 | Archivo HMEQ (dummy) | No permitido |
| `JOB_ProfExe` | bandera | 1 = profesional / ejecutivo | 0 | 1 | Archivo HMEQ (dummy) | No permitido |
| `JOB_Sales` | bandera | 1 = ventas | 0 | 1 | Archivo HMEQ (dummy) | No permitido |
| `JOB_Self` | bandera | 1 = autoempleo | 0 | 1 | Archivo HMEQ (dummy) | No permitido |
| `REASON_HomeImp` | bandera | 1 = mejoras al hogar | 0 | 1 | Archivo HMEQ (dummy) | No permitido |
| `REASON_FALTANTE` | bandera | 1 = no había motivo | 0 | 1 | Calculada a partir del texto original | No permitido |

Reglas que se revisan además de la tabla:

- Que estén las 26 columnas y ninguna venga como texto (por ejemplo, `"abc"` en `LOAN`).
- Que el archivo no traiga celdas vacías: en este archivo los faltantes vienen imputados y marcados con `_FALTANTE`.
- Que cada valor esté dentro de su mínimo y máximo.
- Que una solicitud no tenga dos ocupaciones a la vez (como máximo un `JOB_*` en 1).

## 2. Columnas que publica el tablero

Marca en pantalla: **dato** sin marca · **ƒ calculada** · **⚠ simulado** en gris.

| Columna en pantalla | Tipo | Unidad | De dónde sale | Marca |
|---|---|---|---|---|
| Monto | entero | USD | `LOAN` | dato |
| Valor de la propiedad | decimal | USD | `VALUE` (vacío si `VALUE_FALTANTE = 1`) | dato |
| Ocupación | texto | categoría | `JOB_*` y `JOB_FALTANTE` | dato |
| Motivo | texto | categoría | `REASON_HomeImp` y `REASON_FALTANTE` | dato |
| Incumplió | texto | Sí / No | `BAD` | dato |
| Deuda sobre ingreso (rango) | texto | rango de % | `DEBTINC` y `DEBTINC_FALTANTE` | ƒ calculada |
| Líneas morosas (grupo) | texto | 0, 1, 2, 3 o más | `DELINQ` y `DELINQ_FALTANTE` | ƒ calculada |
| Solicitudes | entero | número de solicitudes | Conteo por grupo | ƒ calculada |
| Tasa | decimal | % | `BAD` promedio del grupo | ƒ calculada |
| × la cartera | decimal | veces | Tasa del grupo / tasa de la cartera | ƒ calculada |
| Casos de más | decimal | incumplimientos | Incumplimientos − solicitudes × tasa de la cartera | ƒ calculada |
| AUC, KS, recall, precisión | decimal | 0–1 | `modelo_sas.json` (modelo de SAS, captura manual) | ƒ calculada |
| Matriz de confusión | entero | solicitudes | Reconstruida a partir de recall y precisión | ⚠ simulado |

## 3. Valores que marcan «sin dato» y cómo se convierten

En este archivo **no hay celdas vacías**: los faltantes se rellenaron en la Entrega 2 y se marcaron con una columna `_FALTANTE`. Por eso el valor que significa «no hay dato» es la combinación *valor imputado + `_FALTANTE = 1`*:

| Columna | Valor que trae el faltante | Solicitudes | Se convierte a |
|---|---|---|---|
| `DEBTINC` | 34.93 (mediana) | 1,267 | vacío |
| `DEROG` | 0 | 708 | vacío |
| `DELINQ` | 0 | 580 | vacío |
| `YOJ` | 7 (mediana) | 515 | vacío |
| `NINQ` | 0 | 510 | vacío |
| `VALUE` | 89,245 (mediana) | 112 | vacío |

El caso más delicado es `DELINQ`, `DEROG` y `NINQ`: el faltante viene como **0**, así que sin la conversión el tablero diría «cero líneas morosas» cuando en realidad no se sabe. La app convierte esos valores a vacío al cargar el archivo (`convertir_faltantes` en `validacion.py`) y en las categorías los muestra como «Sin dato».

Excepciones:

- **Ocupación con todos los `JOB_*` en 0 (767 solicitudes) significa «Gerencia»**, la categoría de referencia de las dummies. No es un faltante. El faltante real es `JOB_FALTANTE = 1`.
- **`MORTDUE`, `CLAGE` y `CLNO` no se pueden recuperar**: se imputaron sin dejar columna `_FALTANTE`. El tablero no las publica.

## 4. Decisiones del equipo

1. **Qué columnas se publican:** las de la sección 2. No se publican `MORTDUE`, `CLAGE`, `CLNO`, `YOJ`, `NINQ`, `DEROG` ni `_PartInd_`, porque no responden a ninguna decisión de los tres roles.
2. **Qué significa cada vacío:** en `VALUE`, `DEBTINC`, `DELINQ`, `DEROG`, `NINQ` y `YOJ`, «no hay dato», nunca cero. Todos los `JOB_*` en 0 es «Gerencia». `BAD`, `LOAN` y las banderas no pueden venir vacíos.
3. **Herramienta del pipeline:** GitHub Actions con Python, porque el repositorio ya está en GitHub y la validación está escrita en Python.
4. **Cómo se distingue la cifra:** dato del archivo sin marca; cifra calculada con «ƒ»; cifra simulada con «⚠ simulado» en gris.
