"""Paleta de Banco Siete: única fuente de colores del tablero y de la verificación de contraste del CI.

Los colores se leen desde app.py y desde scripts/verificar_contraste.py. Si cambias un color aquí y baja el
contraste por debajo de WCAG 2.2 AA, el pipeline de GitHub falla y el cambio no se puede fusionar.
"""

# --- Identidad ---------------------------------------------------------------------------------
AZUL, AZUL_CLARO, FONDO, BLANCO = "#0B1A8C", "#e6e9f7", "#f4f5fa", "#ffffff"
TEXTO = "#0b1330"          # texto principal
TEXTO_SEC = "#44506b"      # texto secundario
TEXTO_SUAVE = "#5b6680"    # notas y descripciones
GRIS_TEXTO = "#4f586e"     # texto sobre fondos grises claros

# --- Semáforo (elementos gráficos: se comparan contra el fondo blanco, mínimo 3:1) ---------------
ROJO, AMBAR, VERDE, GRIS = "#b3261e", "#b26a00", "#1e7b4b", "#6b7488"
COLOR_NIVEL = {"Alta": ROJO, "Media": AMBAR, "Sin alerta": VERDE, "Muestra baja": GRIS}

# --- Etiquetas del semáforo: (fondo, texto). Se comparan como texto normal (4.5:1) ----------------
FONDO_NIVEL = {"Alta": ("#f6cbc5", "#7a1f12"), "Media": ("#fae6b4", "#6b4e00"),
               "Sin alerta": ("#d3ebdd", "#1d5c3b"), "Muestra baja": ("#eceff4", GRIS_TEXTO)}

# --- La identidad de una categoría NO depende solo del color: cada nivel tiene su símbolo ----------
ICONO = {"Alta": "▲", "Media": "◆", "Sin alerta": "●", "Muestra baja": "○"}
SIMBOLO_PLOTLY = {"Alta": "triangle-up", "Media": "diamond", "Sin alerta": "circle", "Muestra baja": "circle-open"}

# --- Pares que el pipeline verifica ---------------------------------------------------------------
# (nombre, primer plano, fondo, tipo) con tipo: "texto" (4.5:1), "grande" (3:1) o "grafico" (3:1).
PARES = [
    ("Texto principal sobre blanco", TEXTO, BLANCO, "texto"),
    ("Texto secundario sobre blanco", TEXTO_SEC, BLANCO, "texto"),
    ("Texto suave sobre blanco", TEXTO_SUAVE, BLANCO, "texto"),
    ("Texto suave sobre fondo de tarjeta", TEXTO_SUAVE, FONDO, "texto"),
    ("Texto suave sobre azul claro", TEXTO_SUAVE, AZUL_CLARO, "texto"),
    ("Texto de tarjeta sobre fondo de tarjeta", "#3a4468", FONDO, "texto"),
    ("Azul de marca sobre blanco", AZUL, BLANCO, "texto"),
    ("Azul de marca sobre fondo de tarjeta", AZUL, FONDO, "texto"),
    ("Texto blanco sobre azul de marca", BLANCO, AZUL, "texto"),
    ("Fecha del encabezado sobre azul", "#dbe5f5", AZUL, "texto"),
    ("Subtítulo del encabezado sobre azul", "#c9d3f2", AZUL, "texto"),
    ("Texto sobre etiqueta Prioritario", FONDO_NIVEL["Alta"][1], FONDO_NIVEL["Alta"][0], "texto"),
    ("Texto sobre etiqueta Vigilar", FONDO_NIVEL["Media"][1], FONDO_NIVEL["Media"][0], "texto"),
    ("Texto sobre etiqueta Normal", FONDO_NIVEL["Sin alerta"][1], FONDO_NIVEL["Sin alerta"][0], "texto"),
    ("Texto sobre etiqueta Pocos datos", FONDO_NIVEL["Muestra baja"][1], FONDO_NIVEL["Muestra baja"][0], "texto"),
    ("Texto blanco sobre rojo (barras)", BLANCO, ROJO, "texto"),
    ("Texto blanco sobre gris (barras)", BLANCO, GRIS, "texto"),
    ("Rojo (Prioritario) como elemento gráfico", ROJO, BLANCO, "grafico"),
    ("Ámbar (Vigilar) como elemento gráfico", AMBAR, BLANCO, "grafico"),
    ("Verde (Normal) como elemento gráfico", VERDE, BLANCO, "grafico"),
    ("Gris (Pocos datos) como elemento gráfico", GRIS, BLANCO, "grafico"),
    ("Azul de marca como elemento gráfico", AZUL, BLANCO, "grafico"),
    ("Línea de referencia de la cartera", "#333333", BLANCO, "grafico"),
]

# Niveles del semáforo que deben distinguirse entre sí aun con daltonismo (distancia de color ΔE mínima).
DELTA_E_MIN = 15.0
