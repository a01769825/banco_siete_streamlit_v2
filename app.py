"""Banco Siete · Plataforma de Créditos Hipotecarios (Streamlit) — versión 2.

Uso:   streamlit run app.py
Archivos necesarios en la misma carpeta:
    hmeq_preparado_1_con_motivo.csv   datos
    logo.png               logo (opcional)
    modelo_sas.json        resultados del modelo de SAS (se llenan a mano)
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

AQUI = Path(__file__).parent
DATA = AQUI / "hmeq_preparado_1_con_motivo.csv"
LOGO = AQUI / "logo.png"
MODELO = AQUI / "modelo_sas.json"


def ahora() -> datetime:
    """Hora de Ciudad de México; si el sistema no tiene la base de zonas horarias, UTC-6."""
    try:
        return datetime.now(ZoneInfo("America/Mexico_City"))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=-6)))


import plotly.io as pio
pio.templates["bs"] = go.layout.Template(layout={"font": {"family": "Inter, Arial, sans-serif", "color": "#0b1330"}})
pio.templates.default = "plotly+bs"

st.set_page_config(page_title="Banco Siete", page_icon=str(LOGO) if LOGO.exists() else None,
                   layout="wide", initial_sidebar_state="expanded")

# --- Reglas del "Cierre de Condiciones" y metas del equipo (se pueden ajustar aquí) ------------
FUENTE = "HMEQ_Preparado"
MIN_N = 30                 # con menos solicitudes no se calcula alerta
UMBRAL_ALTA = 1.5          # tasa del segmento / tasa de la cartera
UMBRAL_MEDIA = 1.15
META_AUC = 0.85            # hipótesis H4a del plan de trabajo
META_RECALL = 0.70
PESO_PRIORITARIOS = (0.10, 0.25)   # % de solicitudes en perfiles prioritarios: verde < 10 %, ámbar < 25 %

# Acceso por persona. NO hay contraseñas en el código ni en el repositorio: las cuentas viven en los
# "secrets" del host (Streamlit Cloud > Settings > Secrets) o, en tu computadora, en .streamlit/secrets.toml
# (ignorado por git). Cada cuenta guarda el HASH de la contraseña (PBKDF2), nunca la contraseña.
# Formato y generación del hash: ver .streamlit/secrets.toml.example y scripts/generar_hash.py.
ITERACIONES_HASH = 600_000
MAX_INTENTOS = 5


def verificar_clave(clave: str, guardado: str) -> bool:
    """`guardado` tiene la forma 'sal$hash' (ambos en hexadecimal)."""
    try:
        sal, esperado = guardado.split("$", 1)
        calculado = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), ITERACIONES_HASH).hex()
    except ValueError:
        return False
    return hmac.compare_digest(calculado, esperado)


def cargar_usuarios() -> dict:
    """Usuarios desde los secrets: {usuario: (hash, rol)}. Sin cuentas configuradas, la app se detiene."""
    try:
        cuentas = dict(st.secrets["usuarios"])
        return {u: (str(c["password_hash"]), str(c["rol"])) for u, c in cuentas.items()}
    except Exception:  # sin secrets, sin sección [usuarios] o con formato incorrecto
        st.error("Faltan las cuentas de acceso. Configura la sección [usuarios] en los secrets "
                 "(ver .streamlit/secrets.toml.example).")
        st.stop()


PANTALLAS = {
    "Analista":   ["Portafolio", "Mapa de riesgo", "Perfiles a revisar", "Nueva solicitud", "Desempeño del modelo"],
    "Gerente":    ["Comparativo de cartera"],
    "Supervisor": ["Seguimiento de cartera"],
}

ORD_DELINQ = ["0", "1", "2", "3 o más", "Sin dato"]
ORD_DEBTINC = ["< 30 %", "30–35 %", "35–40 %", "40–45 %", "> 45 %", "Sin dato"]
ORD_JOB = ["Gerencia", "Oficina", "Prof. / Ejecutivo", "Ventas", "Autoempleo", "Otro", "Sin dato"]
ORD_MOTIVO = ["Mejoras al hogar", "Consolidación", "Sin dato"]
ORD_MONTO = ["< $15 mil", "$15–25 mil", "$25–40 mil", "> $40 mil"]
ORD_DEROG = ["0", "1", "2", "3 o más", "Sin dato"]
ORD_ANTIG = ["< 100", "100–150", "150–200", "200–250", "≥ 250"]   # meses de antigüedad del crédito más antiguo

# columna interna -> (nombre para personas, orden)
DIMS = {
    "Ocupación": ("Ocupación del cliente", ORD_JOB),
    "Endeudamiento": ("Deuda sobre ingreso", ORD_DEBTINC),
    "Morosidad": ("Líneas de crédito morosas", ORD_DELINQ),
    "Motivo": ("Motivo del préstamo", ORD_MOTIVO),
    "Monto": ("Monto solicitado", ORD_MONTO),
}

# Identidad visual: los colores viven en paleta.py (el CI verifica su contraste, ver scripts/verificar_contraste.py)
from paleta import (AZUL, AZUL_CLARO, FONDO, ROJO, AMBAR, VERDE, GRIS, GRIS_TEXTO, COLOR_NIVEL,  # noqa: E402
                    FONDO_NIVEL, ICONO, SIMBOLO_PLOTLY)
CELESTE, NARANJA_MARCA = "#5aa9f0", "#f2b36b"   # decorativos: no llevan información ni texto
ESTADO = {"Alta": "Prioritario", "Media": "Vigilar", "Sin alerta": "Normal", "Muestra baja": "Pocos datos"}
# Con símbolo: el nivel nunca se distingue solo por el color (▲ Prioritario, ◆ Vigilar, ● Normal, ○ Pocos datos)
ESTADO_ICONO = {k: f"{ICONO[k]} {v}" for k, v in ESTADO.items()}

# Pregunta que responde cada gráfica (también se copia en docs/entregable-3.md)
PREGUNTA = {
    "h1_morosidad": "¿Sube el incumplimiento cuando el cliente tiene más líneas morosas o más reportes negativos?",
    "h1_deuda": "¿En qué rangos de deuda sobre ingreso se concentra el incumplimiento y qué pasa cuando falta el dato?",
    "h2_antiguedad": "¿Incumplen menos los clientes con un historial de crédito más antiguo?",
    "h3_faltante": "¿La falta del dato de deuda sobre ingreso concentra incumplimientos o es aleatoria?",
    "mapa": "¿Qué combinaciones de deuda sobre ingreso y líneas morosas incumplen más que la cartera?",
    "perfil": "¿Cuánto por encima de la cartera está este perfil y cómo se compara con grupos parecidos?",
    "matriz": "¿Cuántos clientes que incumplen detecta el modelo y cuántas falsas alertas genera?",
    "burbujas": "¿Qué grupos de clientes incumplen más que el resto y qué tan grandes son?",
}


def pregunta(clave: str):
    st.markdown(f"<p class='preg'><b>Pregunta que responde:</b> {escape(PREGUNTA[clave])}</p>", unsafe_allow_html=True)

TIP_COLOR = {
    VERDE: f"Verde · Normal: la tasa del grupo es menos de {UMBRAL_MEDIA}× la de la cartera. No requiere atención especial.",
    AMBAR: f"Ámbar · Vigilar: la tasa del grupo está entre {UMBRAL_MEDIA}× y {UMBRAL_ALTA}× la de la cartera.",
    ROJO: f"Rojo · Prioritario: la tasa del grupo es {UMBRAL_ALTA}× la de la cartera o más. Conviene revisarlo primero.",
    GRIS: f"Gris · Pocos datos: menos de {MIN_N} solicitudes, no se calcula alerta.",
    AZUL: "Indicador de volumen: no lleva semáforo.",
}


def tip_meta(meta: str) -> str:
    return (f"Verde: cumple la meta del equipo ({meta}). Ámbar: a menos de 0.05 de la meta. Rojo: más lejos. "
            f"Gris: sin dato.")


TERMINOS = [
    ("Incumplimiento", "BAD", "El cliente dejó de pagar o cayó en mora grave."),
    ("Tasa de incumplimiento", "—", "De cada 100 solicitudes, cuántas terminaron en incumplimiento."),
    ("Cartera", "—", "El conjunto de solicitudes que se está viendo (con los filtros aplicados)."),
    ("Veces la cartera (×)", "—", "La tasa del grupo dividida entre la tasa de la cartera. 2× = incumple el doble."),
    ("Casos de más", "—", "Incumplimientos que tiene el grupo por encima de lo esperado si se comportara "
                          "como la cartera."),
    ("Deuda sobre ingreso", "DEBTINC", "Qué parte del ingreso del cliente ya se va en pagar deudas."),
    ("Líneas de crédito morosas", "DELINQ", "Cuántas líneas de crédito del cliente tienen pagos atrasados."),
    ("Reportes negativos graves", "DEROG", "Cuántos reportes negativos importantes tiene el cliente en su historial."),
    ("Antigüedad del crédito", "CLAGE", "Meses que tiene la línea de crédito más antigua del cliente."),
    ("Ocupación del cliente", "JOB", "A qué se dedica el cliente (gerencia, oficina, ventas…)."),
    ("Motivo del préstamo", "REASON", "Mejoras al hogar o consolidación de deudas."),
    ("Monto solicitado", "LOAN", "Cuánto dinero pide el cliente."),
    ("Valor de la propiedad", "VALUE", "Cuánto vale la propiedad que respalda el crédito."),
    ("Sin dato", "*_FALTANTE", "La información no se capturó. No es lo mismo que cero."),
    ("Perfil", "—", "Combinación de deuda sobre ingreso y líneas morosas (por ejemplo: deuda 40–45 % y "
                    "2 líneas morosas)."),
    ("Perfil prioritario", "—", f"Perfil con al menos {MIN_N} solicitudes cuya tasa es {UMBRAL_ALTA}× la "
                                f"cartera o más."),
    ("Semáforo", "—", f"Verde, normal: menos de {UMBRAL_MEDIA}× la cartera · ámbar, vigilar: de {UMBRAL_MEDIA}× a "
                      f"{UMBRAL_ALTA}× · rojo, prioritario: {UMBRAL_ALTA}× o más · gris, pocos datos: menos de "
                      f"{MIN_N} solicitudes."),
]


# --------------------------------------------------------------------------- datos
@st.cache_data
def cargar() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    # Ocupación: las dummies JOB_* omiten una categoría; la que queda con todo en 0 (767 casos)
    # es la categoría de referencia de HMEQ, "Mgr" (gerencia).
    df["Ocupación"] = np.select(
        [df.JOB_FALTANTE == 1, df.JOB_Office == 1, df.JOB_Other == 1,
         df.JOB_ProfExe == 1, df.JOB_Sales == 1, df.JOB_Self == 1],
        ["Sin dato", "Oficina", "Otro", "Prof. / Ejecutivo", "Ventas", "Autoempleo"],
        default="Gerencia")
    # Los valores faltantes vienen imputados en el CSV; las columnas *_FALTANTE dicen cuáles eran.
    bins = pd.cut(df["DEBTINC"], [-np.inf, 30, 35, 40, 45, np.inf],
                  labels=ORD_DEBTINC[:5], right=False).astype(str)
    df["Endeudamiento"] = np.where(df.DEBTINC_FALTANTE == 1, "Sin dato", bins)
    mor = np.where(df["DELINQ"] >= 3, "3 o más", df["DELINQ"].round().astype(int).astype(str))
    df["Morosidad"] = np.where(df.DELINQ_FALTANTE == 1, "Sin dato", mor)
    # REASON: REASON_FALTANTE se agregó a partir de la base con el texto original (252 sin motivo).
    df["Motivo"] = np.select([df.REASON_FALTANTE == 1, df.REASON_HomeImp == 1],
                             [ORD_MOTIVO[2], ORD_MOTIVO[0]], default=ORD_MOTIVO[1])
    der = np.where(df["DEROG"] >= 3, "3 o más", df["DEROG"].round().astype(int).astype(str))
    df["Negativos"] = np.where(df.DEROG_FALTANTE == 1, "Sin dato", der)
    df["Antigüedad"] = pd.cut(df["CLAGE"], [-np.inf, 100, 150, 200, 250, np.inf],
                              labels=ORD_ANTIG, right=False).astype(str)
    df["Monto"] = pd.cut(df["LOAN"], [0, 15_000, 25_000, 40_000, np.inf],
                         labels=ORD_MONTO, right=False).astype(str)
    return df


def nivel(razon: float, n: int) -> str:
    if n < MIN_N:
        return "Muestra baja"
    if razon >= UMBRAL_ALTA:
        return "Alta"
    if razon >= UMBRAL_MEDIA:
        return "Media"
    return "Sin alerta"


def en_palabras(t: float) -> str:
    """Tasa como frase: 0.199 -> '1 de cada 5'; 0.67 -> '7 de cada 10'."""
    if t is None or np.isnan(t):
        return "—"
    if t <= 0:
        return "ninguno"
    if t >= 0.25:
        return f"{round(t * 10)} de cada 10"
    return f"1 de cada {round(1 / t)}"


def etiqueta(dim: str, seg: str) -> str:
    """Nombre del grupo entendible sin conocer las columnas."""
    if dim == "Morosidad":
        if seg == "Sin dato":
            return "Líneas morosas: sin dato"
        return {"0": "0 líneas morosas", "1": "1 línea morosa", "2": "2 líneas morosas"}.get(
            seg, "3 o más líneas morosas")
    if dim == "Endeudamiento":
        return "Deuda/ingreso: sin dato" if seg == "Sin dato" else f"Deuda/ingreso {seg}"
    if dim == "Ocupación":
        return "Ocupación: sin dato" if seg == "Sin dato" else f"Ocupación: {seg}"
    if dim == "Motivo":
        return "Motivo: sin dato" if seg == "Sin dato" else f"Motivo: {seg.lower()}"
    return f"Monto {seg}"


def segmentos(d: pd.DataFrame) -> pd.DataFrame:
    base = d["BAD"].mean()
    filas = []
    for dim, (titulo, orden) in DIMS.items():
        g = d.groupby(dim)["BAD"].agg(["mean", "size", "sum"])
        for seg in orden:
            if seg not in g.index:
                continue
            r = g.loc[seg]
            n, tasa = int(r["size"]), float(r["mean"])
            razon = tasa / base if base > 0 else np.nan
            filas.append({"Dimensión": dim, "Variable": titulo, "Segmento": seg,
                          "Etiqueta": etiqueta(dim, seg), "Solicitudes": n,
                          "Incumplimientos": int(r["sum"]), "Tasa": tasa, "Razón vs cartera": razon,
                          "Casos en exceso": n * (tasa - base), "Nivel": nivel(razon, n)})
    return pd.DataFrame(filas)


def perfiles(d: pd.DataFrame, base: float) -> pd.DataFrame:
    g = d.groupby(["Endeudamiento", "Morosidad"])["BAD"].agg(["mean", "size", "sum"]).reset_index()
    g = g[g["size"] >= MIN_N].copy()
    deuda = np.where(g["Endeudamiento"] == "Sin dato", "Deuda/ingreso sin dato", "Deuda/ingreso " + g["Endeudamiento"])
    mora = np.where(g["Morosidad"] == "Sin dato", "morosidad sin dato",
                    np.where(g["Morosidad"] == "1", "1 línea morosa",
                             np.where(g["Morosidad"] == "3 o más", "3 o más líneas morosas",
                                      g["Morosidad"] + " líneas morosas")))
    g["Perfil"] = deuda + " · " + mora
    g["Razón"] = g["mean"] / base
    g["Nivel"] = [nivel(r, n) for r, n in zip(g["Razón"], g["size"])]
    g["Casos en exceso"] = g["size"] * (g["mean"] - base)
    return g.rename(columns={"mean": "Tasa", "size": "Solicitudes", "sum": "Incumplen"})


def fuente(d: pd.DataFrame):
    st.caption(f"Fuente: {FUENTE} · {len(d):,} solicitudes con los filtros actuales.")


# --------------------------------------------------------------------------- identidad visual
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
.stApp, .stApp p, .stApp label, .stApp li, .stApp input, .stApp textarea, .stApp button {{
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;}}
span[data-testid="stIconMaterial"], .material-symbols-rounded {{
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;}}
.hdr-title {{font-family: 'Source Serif 4', Georgia, serif; font-size: 26px; font-weight: 700; color: #ffffff !important;}}
.hdr-sub {{color: #c9d3f2 !important;}}
.block-container {{padding-top: 3.6rem; max-width: 1400px;}}
h1, h2, h3, .serif {{font-family: 'Source Serif 4', Georgia, serif !important; color: {AZUL}; letter-spacing: -0.01em;
    font-weight: 700;}}
h3 {{font-size: 1.45rem !important; margin-bottom: 0.1rem;}}
div[data-testid="stHorizontalBlock"]:has(.hdr-marker) {{
    background: {AZUL}; border-radius: 14px; padding: 12px 20px; align-items: center; margin-bottom: 12px;}}
div[data-testid="stHorizontalBlock"]:has(.hdr-marker) img {{background: #fff; border-radius: 10px; padding: 4px;}}
.tile {{background:{FONDO}; border:0; border-radius:14px; padding:14px 16px; min-height:150px;}}
.tile .t {{font-size:13px; font-weight:600; color:#3a4468;}}
.tile .v {{font-family:'Source Serif 4', Georgia, serif; font-size:36px; font-weight:700; color:{AZUL}; line-height:1.15;}}
.tile .r {{font-size:13px; margin-top:2px; color:#0b1330;}}
.tile .a {{font-size:12px; color:#5b6680; margin-top:4px;}}
.dot {{display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:middle;}}
.sub {{color:#5b6680; font-size:14px; margin: -6px 0 8px 0;}}
.paso {{background:{AZUL_CLARO}; border-radius:12px; padding:10px 14px; text-align:center;}}
.paso b {{font-family:'Source Serif 4', Georgia, serif; font-size:24px; color:{AZUL};}}
.hall {{font-family:'Source Serif 4', Georgia, serif; font-size:17px; font-weight:700; color:{AZUL}; line-height:1.25;
    min-height:4.1em; margin:4px 0 0 0;}}
.hip {{font-size:12px; color:#5b6680; margin:0 0 2px 0;}}
.preg {{font-size:12.5px; color:#44506b; margin:0 0 4px 0;}}
.tip {{position:relative; cursor:help;}}
.tip[data-tip]:not([data-tip='']):hover::after {{content:attr(data-tip); position:absolute; z-index:99999; left:50%;
    bottom:calc(100% + 8px); transform:translateX(-50%); width:max-content; max-width:270px; background:#0b1330;
    color:#fff; padding:8px 10px; border-radius:8px; font-size:12px; line-height:1.35; font-weight:400;
    text-align:left; white-space:normal; box-shadow:0 4px 14px rgba(0,0,0,.28); pointer-events:none;}}
.tip[data-tip]:not([data-tip='']):hover::before {{content:''; position:absolute; z-index:99999; left:50%;
    bottom:calc(100% + 2px); transform:translateX(-50%); border:6px solid transparent; border-top-color:#0b1330;
    pointer-events:none;}}
.chip {{display:inline-block; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600;}}
</style>
"""


def tile(titulo: str, valor: str, ref: str, color: str, ayuda: str = "", tip: str | None = None):
    """Indicador con punto de semáforo y su comparación contra una referencia (explicación al pasar el mouse)."""
    tip = TIP_COLOR.get(color, "") if tip is None else tip
    st.markdown(
        f"<div class='tile' style='border-left:6px solid {color}'><div class='t'>{escape(titulo)}</div>"
        f"<div class='v'>{escape(valor)}</div>"
        f"<div class='r tip' data-tip='{escape(tip)}'><span class='dot' style='background:{color}'></span>{escape(ref)}</div>"
        f"<div class='a'>{escape(ayuda)}</div></div>", unsafe_allow_html=True)


def fila_tiles(items):
    for col, it in zip(st.columns(len(items)), items):
        with col:
            tile(*it)


def seccion(titulo: str, pregunta: str):
    st.subheader(titulo)
    st.markdown(f"<p class='sub'>{pregunta}</p>", unsafe_allow_html=True)


def leyenda():
    simbolo = {VERDE: ICONO["Sin alerta"], AMBAR: ICONO["Media"], ROJO: ICONO["Alta"], GRIS: ICONO["Muestra baja"]}

    def it(color, texto):
        return (f"<span class='tip' data-tip='{escape(TIP_COLOR[color])}'><span class='dot' "
                f"style='background:{color}'></span>{simbolo[color]} {texto}</span>")
    st.markdown(
        "<div style='font-size:12.5px;color:#44506b;margin:2px 0 8px 0'><b>Semáforo</b> (compara cada grupo con la "
        "tasa de la cartera; pasa el mouse sobre cada color): "
        + it(VERDE, f"normal &lt; {UMBRAL_MEDIA}×") + " &nbsp; " + it(AMBAR, f"vigilar {UMBRAL_MEDIA}–{UMBRAL_ALTA}×")
        + " &nbsp; " + it(ROJO, f"prioritario ≥ {UMBRAL_ALTA}×") + " &nbsp; "
        + it(GRIS, f"pocos datos (&lt; {MIN_N} solicitudes)") + "</div>", unsafe_allow_html=True)


def barra_html(texto: str, valor: float, color: str, extra: str = "", marca: float | None = None):
    ancho = max(0.0, min(valor, 1.0)) * 100
    tick = (f"<div style='position:absolute;left:{min(marca, 1) * 100:.1f}%;top:-2px;width:2px;height:12px;"
            f"background:#222'></div>" if marca is not None else "")
    return (f"<div style='display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px'>"
            f"<div style='width:38%'>{escape(texto)}</div>"
            f"<div style='position:relative;flex:1;height:8px;background:#e6e9f0;border-radius:4px'>"
            f"<div style='width:{ancho:.1f}%;height:8px;background:{color};border-radius:4px'></div>{tick}</div>"
            f"<div style='width:24%;text-align:right'><b>{valor:.0%}</b> {escape(extra)}</div></div>")


def mapa_calor(d: pd.DataFrame, base: float, medida: str = "Tasa"):
    celdas = d.groupby(["Endeudamiento", "Morosidad"])["BAD"].agg(["mean", "size"])
    filas = d.groupby("Endeudamiento")["BAD"].agg(["mean", "size"])
    cols = d.groupby("Morosidad")["BAD"].agg(["mean", "size"])
    th = "style='padding:4px;font-size:12px;color:#44506b;text-align:center'"
    nom_col = {"0": "0", "1": "1", "2": "2", "3 o más": "3 o más", "Sin dato": "Sin dato"}

    def tip(t, n, quien):
        if n < MIN_N:
            return f"{quien}: solo {n} solicitudes (menos de {MIN_N}); no se calcula alerta."
        niv = nivel(t / base, n)
        return (f"{quien}: incumplen {t:.0%} ({en_palabras(t)}). Es {t / base:.1f}× la cartera ({base:.0%}). "
                f"{n:,} solicitudes, {round(t * n):,} incumplieron. Estado: {ESTADO_ICONO[niv]}.")

    def grande(t, n):
        if medida == "× la cartera":
            return f"{t / base:.1f}×", f"{t:.0%} · n = {n:,}"
        if medida == "Casos de más":
            return f"{n * (t - base):+,.0f}", f"{t:.0%} · n = {n:,}"
        return f"{t:.0%}", f"{t / base:.1f}× · n = {n:,}"

    def lbl_col(c):
        return "sin dato de líneas morosas" if c == "Sin dato" else f"{c} líneas morosas"

    h = ["<table style='width:100%;border-collapse:separate;border-spacing:4px'>"
         f"<tr><th></th><th colspan='6' {th}>Líneas de crédito morosas del cliente →</th></tr><tr><th></th>"]
    h += [f"<th {th}>{escape(nom_col[c])}</th>" for c in ORD_DELINQ] + [f"<th {th}>Todas</th></tr>"]
    for r in ORD_DEBTINC:
        n_r = int(filas["size"].get(r, 0))
        etq = "Deuda/ingreso sin dato" if r == "Sin dato" else f"Deuda/ingreso {r}"
        h.append(f"<tr><td style='font-size:12px;white-space:nowrap'><b>{escape(etq)}</b><br>"
                 f"<span style='color:#6b7488'>{n_r:,} solicitudes</span></td>")
        for c in ORD_DELINQ:
            if (r, c) in celdas.index:
                t, n = float(celdas.loc[(r, c), "mean"]), int(celdas.loc[(r, c), "size"])
            else:
                t, n = 0.0, 0
            tp = escape(tip(t, n, f"{etq} y {lbl_col(c)}"))
            if n < MIN_N:
                h.append(f"<td class='tip' data-tip='{tp}' style='background:#eceff4;color:{GRIS_TEXTO};text-align:center;"
                         f"border-radius:8px;padding:10px 4px;font-size:12px'>{ICONO['Muestra baja']} n = {n}<br>pocos datos</td>")
                continue
            niv = nivel(t / base, n)
            bg, fg = FONDO_NIVEL[niv]
            borde = "border:2px solid #1b1b1b;" if niv == "Alta" else ""
            g1, g2 = grande(t, n)
            h.append(f"<td class='tip' data-tip='{tp}' style='background:{bg};color:{fg};text-align:center;"
                     f"border-radius:8px;padding:8px 4px;{borde}'><b style='font-size:17px'>{g1}</b><br>"
                     f"<span style='font-size:11px'>{ICONO[niv]} {g2}</span></td>")
        tr = float(filas["mean"].get(r, 0)) if n_r else 0
        tpr = escape(tip(tr, n_r, f"{etq}, todas las líneas morosas")) if n_r else ""
        h.append(f"<td class='tip' data-tip='{tpr}' style='background:#f1f3f8;text-align:center;border-radius:8px;"
                 f"font-weight:700'>{tr:.0%}</td></tr>" if n_r else "<td style='background:#f1f3f8'></td></tr>")
    h.append("<tr><td style='font-size:12px'><b>Todas</b></td>")
    for c in ORD_DELINQ:
        n_c = int(cols["size"].get(c, 0))
        tc = float(cols["mean"].get(c)) if n_c else 0
        tpc = escape(tip(tc, n_c, f"Todas las deudas, {lbl_col(c)}")) if n_c else ""
        h.append(f"<td class='tip' data-tip='{tpc}' style='background:#f1f3f8;text-align:center;border-radius:8px;"
                 f"font-weight:700;padding:8px 4px'>{tc:.0%}"
                 f"<br><span style='font-size:11px;font-weight:400'>n = {n_c:,}</span></td>")
    h.append(f"<td class='tip' data-tip='{escape(f'Toda la cartera: incumple {base:.1%} ({en_palabras(base)}).')}' "
             f"style='background:#f1f3f8;text-align:center;border-radius:8px;font-weight:700'>"
             f"{base:.0%}</td></tr></table>")
    st.markdown("".join(h), unsafe_allow_html=True)


def tabla_segmentos(df_s: pd.DataFrame, key: str, incluir_variable: bool = True, seleccion: str | None = None,
                    compacta: bool = False):
    """Tabla completa (sin scroll interno) de grupos con semáforo."""
    v = pd.DataFrame({
        "Alerta": df_s["Nivel"].map(ESTADO_ICONO),
        "Grupo": df_s["Etiqueta"],
        **({"Variable": df_s["Variable"]} if incluir_variable else {}),
        "Solicitudes": df_s["Solicitudes"],
        "Tasa": df_s["Tasa"] * 100,
        **({} if compacta else {"En palabras": df_s["Tasa"].map(en_palabras)}),
        "Veces la cartera": df_s["Razón vs cartera"],
        "Casos de más": df_s["Casos en exceso"].round().astype(int),
    })
    cfg = {
        "Tasa": st.column_config.ProgressColumn("Tasa de incumplimiento", format="%.0f %%", min_value=0,
                                                max_value=100),
        "Alerta": st.column_config.TextColumn(width=100,
                                                  help=f"Semáforo: Prioritario (rojo) = {UMBRAL_ALTA}× la cartera o más · Vigilar (ámbar) = {UMBRAL_MEDIA}–{UMBRAL_ALTA}× · Normal (verde) = menos · Pocos datos (gris) = menos de {MIN_N} solicitudes."),
        "Solicitudes": st.column_config.NumberColumn(format="%d", width=90, help="Cuántas solicitudes tiene el grupo."),
        "Veces la cartera": st.column_config.NumberColumn(
            "× la cartera", format="%.1f ×", help="Tasa del grupo ÷ tasa de la cartera. 2 × = el doble."),
        "Casos de más": st.column_config.NumberColumn(
            help="Incumplimientos por encima de lo esperado si el grupo se comportara como la cartera."),
        "En palabras": st.column_config.TextColumn("Dicho fácil"),
    }
    if compacta:
        cfg["Tasa"] = st.column_config.NumberColumn("Tasa", format="%.0f %%", width=65)
        cfg["Veces la cartera"] = st.column_config.NumberColumn("× cartera", format="%.1f ×", width=75)
        cfg["Casos de más"] = st.column_config.NumberColumn("De más", width=65,
                                                            help="Incumplimientos por encima de lo esperado.")
        cfg["Solicitudes"] = st.column_config.NumberColumn("Solic.", format="%d", width=65)
    alto = min(36 * (len(v) + 1) + 8, 640)
    kw = {}
    if seleccion:
        kw = {"on_select": "rerun", "selection_mode": seleccion, "key": key}
    return st.dataframe(v, hide_index=True, height=alto, column_config=cfg, **kw)


# --------------------------------------------------------------------------- encabezado y filtros
def limites_valor(df):
    """Límites del control de valor, redondeados al paso del slider para que incluyan todos los casos."""
    paso = 5000
    return (int(df["VALUE"].min()) // paso * paso, -(-int(df["VALUE"].max()) // paso) * paso)


def valores_iniciales(df):
    return {"f_monto": ORD_MONTO, "f_motivo": ORD_MOTIVO, "f_job": ORD_JOB,
            "f_valor": limites_valor(df), "f_valor_nd": True}


def restablecer(df):
    for k, v in valores_iniciales(df).items():
        st.session_state[k] = v


def n_filtros_activos(df) -> int:
    ini = valores_iniciales(df)
    return sum(1 for k, v in ini.items() if list(np.atleast_1d(st.session_state.get(k, v))) != list(np.atleast_1d(v)))


def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    vmin, vmax = limites_valor(df)
    rango = tuple(st.session_state["f_valor"])
    if rango == (vmin, vmax) and st.session_state["f_valor_nd"]:
        en_valor = pd.Series(True, index=df.index)  # control sin tocar: no se filtra ninguna solicitud
    else:
        en_valor = df["VALUE"].between(*rango) & (df.VALUE_FALTANTE == 0)
        if st.session_state["f_valor_nd"]:
            en_valor |= df.VALUE_FALTANTE == 1
    m = (df["Monto"].isin(st.session_state["f_monto"]) & df["Motivo"].isin(st.session_state["f_motivo"])
         & df["Ocupación"].isin(st.session_state["f_job"]) & en_valor)
    return df[m]


def encabezado(df: pd.DataFrame, con_filtros: bool):
    for k, v in valores_iniciales(df).items():
        st.session_state.setdefault(k, v)
    hoy = ahora().strftime("%d/%m/%Y")
    c1, c2, c3, c4 = st.columns([0.9, 5, 2.2, 1.4], vertical_alignment="center")
    if LOGO.exists():
        c1.image(str(LOGO), width=80)
    c2.markdown("<span class='hdr-marker'></span><span class='hdr-title'>"
                "Banco Siete</span><br><span class='hdr-sub'>Plataforma de Créditos Hipotecarios</span>",
                unsafe_allow_html=True)
    c3.markdown(f"<div style='text-align:right;color:#dbe5f5;font-size:13px'>Fecha de actualización<br>"
                f"<b style='color:#fff;font-size:16px'>{hoy}</b></div>", unsafe_allow_html=True)
    if con_filtros:
        act = n_filtros_activos(df)
        with c4.popover(f"Filtros ({act})" if act else "Filtros", use_container_width=True):
            st.caption("Acotan todas las pantallas. Si no tocas nada, se ve toda la cartera.")
            st.multiselect("Monto solicitado", ORD_MONTO, key="f_monto",
                           help="Decisión: qué tramo de monto revisar primero o qué límite de crédito autorizar por tramo.")
            st.multiselect("Motivo del préstamo", ORD_MOTIVO, key="f_motivo")
            st.multiselect("Ocupación del cliente", ORD_JOB, key="f_job",
                           help="Decisión: en qué segmento de clientes concentrar la revisión de expedientes.")
            vmin, vmax = limites_valor(df)
            st.slider("Valor de la propiedad", vmin, vmax, key="f_valor", step=5000)
            st.checkbox("Incluir valor sin dato", key="f_valor_nd")
            st.button("Restablecer", on_click=restablecer, args=(df,))


def lectura_filtros(df, d):
    """Siempre visible: cuántas solicitudes se ven y qué filtros están activos."""
    ini = valores_iniciales(df)
    nombres = {"f_monto": "Monto", "f_motivo": "Motivo", "f_job": "Ocupación", "f_valor": "Valor de la propiedad",
               "f_valor_nd": "Valor sin dato"}
    activos = [n for k, n in nombres.items()
               if list(np.atleast_1d(st.session_state.get(k, ini[k]))) != list(np.atleast_1d(ini[k]))]
    if activos:
        st.info(f"Estás viendo {len(d):,} de {len(df):,} solicitudes ({len(d) / len(df):.0%}). "
                f"Filtros activos ({len(activos)}): {', '.join(activos)}. Se cambian en Filtros, arriba a la derecha.")
    else:
        st.caption(f"Viendo las {len(d):,} solicitudes de la cartera completa. Filtros activos: ninguno.")


# --------------------------------------------------------------------------- hallazgos (hipótesis H1 a H3)
def tasas(d: pd.DataFrame, col: str, orden: list) -> pd.DataFrame:
    return d.groupby(col)["BAD"].agg(["mean", "size"]).reindex(orden).dropna()


def patron(g: pd.DataFrame) -> dict:
    """Describe cómo cambia la tasa a lo largo de las categorías ordenadas (sin contar 'Sin dato' ni grupos chicos)."""
    v = g[(g["size"] >= MIN_N) & (g.index != "Sin dato")]
    if len(v) < 2:
        return {"dir": "pocos"}
    r = v["mean"].to_numpy()
    if np.all(np.diff(r) >= -1e-9) and r[-1] > r[0]:
        d_ = "sube"
    elif np.all(np.diff(r) <= 1e-9) and r[-1] < r[0]:
        d_ = "baja"
    else:
        d_ = "mixto"
    return {"dir": d_, "r0": r[0], "r1": r[-1], "l0": v.index[0], "l1": v.index[-1], "rmin": r.min(), "rmax": r.max()}


def hover_barras(g: pd.DataFrame, base: float) -> list:
    return [f"<b>{i}</b><br>Incumplen {m:.1%} ({en_palabras(m)})<br>{m / base:.1f}× la cartera<br>{int(n):,} solicitudes"
            if base else f"<b>{i}</b>" for i, m, n in zip(g.index, g["mean"], g["size"])]


def etiquetas_barra(g: pd.DataFrame, base: float) -> list:
    """Etiqueta de cada barra con el símbolo de su nivel (no solo color)."""
    return [f"{ICONO[nivel(m / base if base else 0, int(n))]} {m:.0%}" for m, n in zip(g["mean"], g["size"])]


def colores(g: pd.DataFrame, base: float) -> list:
    return [COLOR_NIVEL[nivel(m / base if base else 0, int(n))] for m, n in zip(g["mean"], g["size"])]


def hallazgo(titulo: str, hipotesis: str, clave: str):
    st.markdown(f"<p class='hall'>{escape(titulo)}</p><p class='hip'>{escape(hipotesis)}</p>", unsafe_allow_html=True)
    pregunta(clave)


def figura_barras(g: pd.DataFrame, base: float, eje: str):
    fig = go.Figure(go.Bar(
        x=list(g.index), y=g["mean"], marker_color=colores(g, base),
        text=etiquetas_barra(g, base), textposition="outside", cliponaxis=False,
        hovertext=hover_barras(g, base), hovertemplate="%{hovertext}<extra></extra>"))
    fig.add_hline(y=base, line_dash="dash", line_color="#333",
                  annotation_text=f"Cartera {base:.0%}", annotation_position="top left")
    fig.update_xaxes(type="category", title=eje)
    fig.update_yaxes(tickformat=".0%", range=[0, min(1.0, max(g["mean"].max() * 1.2, base * 1.6))],
                     title="Tasa de incumplimiento")
    fig.update_layout(height=300, bargap=0.3, margin={"t": 10, "b": 10, "l": 10, "r": 10}, showlegend=False)
    return fig


def graficas_hallazgos(d: pd.DataFrame, base: float):
    """Cuatro gráficas, una por hallazgo, con el título escrito a partir de los datos que se están viendo."""
    seccion("Qué dicen los datos", "Cuatro hallazgos del análisis. Los títulos se recalculan con los filtros activos.")
    c1, c2 = st.columns(2, gap="large")
    c3, c4 = st.columns(2, gap="large")

    # H1 · morosidad y reportes negativos
    with c1:
        gd, gg = tasas(d, "Morosidad", ORD_DELINQ), tasas(d, "Negativos", ORD_DEROG)
        pd_, pg = patron(gd), patron(gg)
        if pd_["dir"] == "sube" and pg["dir"] == "sube":
            t = (f"Con más líneas morosas y más reportes negativos, más incumplimiento: {pd_['r0']:.0%} con "
                 f"{pd_['l0']} líneas morosas contra {pd_['r1']:.0%} con {pd_['l1']}")
        elif pd_["dir"] == "pocos" and pg["dir"] == "pocos":
            t = "Pocos datos para comparar la morosidad con estos filtros"
        else:
            lo = min(x for x in (pd_.get("rmin"), pg.get("rmin")) if x is not None)
            hi = max(x for x in (pd_.get("rmax"), pg.get("rmax")) if x is not None)
            t = f"El incumplimiento va de {lo:.0%} a {hi:.0%} según las líneas morosas y los reportes negativos"
        hallazgo(t, "H1 · Entrega 2: a más morosidad, más incumplimiento", "h1_morosidad")
        if not gd.empty and not gg.empty:
            from plotly.subplots import make_subplots
            fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                                subplot_titles=("Líneas de crédito morosas", "Reportes negativos graves"))
            for i, g in ((1, gd), (2, gg)):
                fig.add_trace(go.Bar(
                    x=list(g.index), y=g["mean"], marker_color=colores(g, base),
                    text=etiquetas_barra(g, base), textposition="outside", cliponaxis=False,
                    hovertext=hover_barras(g, base), hovertemplate="%{hovertext}<extra></extra>"), row=1, col=i)
            fig.add_hline(y=base, line_dash="dash", line_color="#333")
            fig.update_xaxes(type="category")
            fig.update_yaxes(tickformat=".0%", range=[0, min(1.0, max(gd["mean"].max(), gg["mean"].max()) * 1.2)])
            fig.update_layout(height=300, bargap=0.3, showlegend=False, margin={"t": 30, "b": 10, "l": 10, "r": 10})
            st.plotly_chart(fig, use_container_width=True)

    # H1 · deuda sobre ingreso
    with c2:
        g = tasas(d, "Endeudamiento", ORD_DEBTINC)
        v = g[g["size"] >= MIN_N].sort_values("mean", ascending=False)
        if len(v) >= 3:
            n_ = lambda c: "sin dato de deuda sobre ingreso" if c == "Sin dato" else f"deuda sobre ingreso {c}"
            a, b = v.index[0], v.index[1]
            resto = d[~d["Endeudamiento"].isin([a, b])]["BAD"].mean()
            t = (f"El incumplimiento se concentra en las solicitudes con {n_(a)} ({v['mean'].iloc[0]:.0%}) y "
                 f"{n_(b)} ({v['mean'].iloc[1]:.0%}); en el resto es {resto:.0%}")
        else:
            t = "Pocos datos para comparar la deuda sobre ingreso con estos filtros"
        hallazgo(t, "H1 · Entrega 2: a más deuda sobre ingreso, o cuando falta el dato, más incumplimiento", "h1_deuda")
        if not g.empty:
            st.plotly_chart(figura_barras(g, base, "Deuda sobre ingreso"), use_container_width=True)

    # H2 · antigüedad del crédito
    with c3:
        g = tasas(d, "Antigüedad", ORD_ANTIG)
        p = patron(g)
        if p["dir"] == "baja":
            t = (f"A mayor antigüedad del historial de crédito, menor incumplimiento: {p['r0']:.0%} con "
                 f"{p['l0']} meses contra {p['r1']:.0%} con {p['l1']} meses")
        elif p["dir"] == "pocos":
            t = "Pocos datos para comparar la antigüedad con estos filtros"
        else:
            t = f"El incumplimiento va de {p['rmin']:.0%} a {p['rmax']:.0%} según la antigüedad del crédito"
        hallazgo(t, "H2 · Entrega 2: a más antigüedad crediticia, menos incumplimiento", "h2_antiguedad")
        if not g.empty:
            st.plotly_chart(figura_barras(g, base, "Antigüedad del crédito más antiguo (meses)"),
                            use_container_width=True)

    # H3 · la falta de deuda sobre ingreso no es aleatoria
    with c4:
        nd = d[d["Endeudamiento"] == "Sin dato"]
        n_bad = int(d["BAD"].sum())
        if len(nd) >= MIN_N and n_bad:
            t = (f"Las solicitudes sin deuda sobre ingreso son el {len(nd) / len(d):.0%} de la cartera y "
                 f"concentran el {nd['BAD'].sum() / n_bad:.0%} de los incumplimientos")
        else:
            t = "Pocas solicitudes sin deuda sobre ingreso con estos filtros"
        hallazgo(t, "H3 · Entrega 2: la falta de este dato no es aleatoria", "h3_faltante")
        if len(nd) >= MIN_N and n_bad:
            sd = [len(nd) / len(d), nd["BAD"].sum() / n_bad]
            fig = go.Figure()
            fig.add_trace(go.Bar(y=["Solicitudes", "Incumplimientos"], x=sd, orientation="h", name="Sin dato",
                                 marker_color=ROJO, text=[f"{x:.0%}" for x in sd], textposition="inside",
                                 insidetextfont={"color": "#fff"},
                                 hovertemplate="%{y}: %{x:.1%} son solicitudes sin dato de deuda/ingreso<extra></extra>"))
            fig.add_trace(go.Bar(y=["Solicitudes", "Incumplimientos"], x=[1 - x for x in sd], orientation="h",
                                 name="Con dato", marker_color=GRIS,
                                 text=[f"{1 - x:.0%}" for x in sd], textposition="inside",
                                 insidetextfont={"color": "#fff"},
                                 hovertemplate="%{y}: %{x:.1%} tienen el dato<extra></extra>"))
            fig.update_layout(barmode="stack", height=230, margin={"t": 10, "b": 10, "l": 10, "r": 10},
                              legend={"orientation": "h", "y": -0.25})
            fig.update_xaxes(tickformat=".0%", range=[0, 1])
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
            st.warning("**Cuando falte la deuda sobre ingreso:** solicitar comprobante de ingresos y deudas "
                       "antes de decidir.")


# --------------------------------------------------------------------------- pantallas del Analista
def pag_resumen(d: pd.DataFrame, df: pd.DataFrame):
    base, base_total = d["BAD"].mean(), df["BAD"].mean()
    p = perfiles(d, base)
    prio = p[p["Nivel"] == "Alta"]
    n_prio = int(prio["Solicitudes"].sum())
    peso = n_prio / len(d)
    nd = d[d["Endeudamiento"] == "Sin dato"]
    razon_tasa = base / base_total if base_total else 1.0
    col_peso = VERDE if peso < PESO_PRIORITARIOS[0] else AMBAR if peso < PESO_PRIORITARIOS[1] else ROJO

    seccion("Portafolio de la cartera", "¿Cuántas solicitudes hay, cuántas incumplen y dónde está el riesgo?")
    leyenda()
    fila_tiles([
        ("Solicitudes analizadas", f"{len(d):,}", f"{len(d) / len(df):.0%} de la cartera completa", AZUL,
         "Tamaño de lo que estás viendo."),
        ("Tasa de incumplimiento", f"{base:.1%}",
         f"{en_palabras(base)} · cartera completa: {base_total:.1%}",
         COLOR_NIVEL[nivel(razon_tasa, len(d))], "Verde si no supera a la cartera completa en más de 15 %."),
        ("Perfiles prioritarios", f"{len(prio)}", f"{n_prio:,} solicitudes ({peso:.0%} de lo analizado)",
         col_peso, f"Verde < {PESO_PRIORITARIOS[0]:.0%} · ámbar < {PESO_PRIORITARIOS[1]:.0%} · rojo más.",
         f"Verde: menos de {PESO_PRIORITARIOS[0]:.0%} de las solicitudes están en perfiles prioritarios · ámbar: menos "
         f"de {PESO_PRIORITARIOS[1]:.0%} · rojo: más. Un perfil es prioritario si tiene al menos {MIN_N} solicitudes y "
         f"una tasa de {UMBRAL_ALTA}× la cartera o más."),
        ("Sin dato de deuda/ingreso", f"{len(nd) / len(d):.0%}",
         (f"incumplen {nd['BAD'].mean():.0%} vs {base:.0%} de la cartera" if len(nd) >= MIN_N else "pocos datos"),
         COLOR_NIVEL[nivel(nd["BAD"].mean() / base if len(nd) else 0, len(nd))],
         "No se capturó. Acción: pedir comprobante de ingresos y deudas."),
    ])
    st.write("")
    n_bad = int(d["BAD"].sum())
    a, b, c, e, f = st.columns([3, 0.4, 3, 0.4, 3], vertical_alignment="center")
    a.markdown(f"<div class='paso'>Solicitudes<br><b>{len(d):,}</b></div>", unsafe_allow_html=True)
    b.markdown("<div style='text-align:center;font-size:24px;color:#6b7488'>→</div>", unsafe_allow_html=True)
    c.markdown(f"<div class='paso'>Incumplen<br><b>{n_bad:,}</b></div>", unsafe_allow_html=True)
    e.markdown("<div style='text-align:center;font-size:24px;color:#6b7488'>→</div>", unsafe_allow_html=True)
    f.markdown(f"<div class='paso'>Tasa<br><b>{base:.1%}</b> · {en_palabras(base)}</div>", unsafe_allow_html=True)
    st.write("")
    graficas_hallazgos(d, base)
    st.write("")
    s = segmentos(d)
    top = s[s["Nivel"].isin(["Alta", "Media"])].sort_values("Casos en exceso", ascending=False).head(8)
    seccion("Dónde mirar primero", "Los grupos que concentran más incumplimientos por encima de lo esperado.")
    if top.empty:
        st.info("Con estos filtros ningún grupo supera el umbral de alerta.")
    else:
        tabla_segmentos(top, "top")
    fuente(d)


def pag_mapa(d: pd.DataFrame, df: pd.DataFrame):
    base = d["BAD"].mean()
    seccion("Mapa de riesgo", "¿Cómo cambia el incumplimiento al combinar la deuda del cliente con sus pagos atrasados?")
    leyenda()
    izq, der = st.columns([1.9, 1], gap="large")
    with izq:
        medida = st.radio("Mostrar en cada casilla", ["Tasa", "× la cartera", "Casos de más"], horizontal=True,
                          key="medida_mapa",
                          help="Tasa: % que incumple. × la cartera: cuántas veces la tasa de la cartera. "
                               "Casos de más: incumplimientos por encima de lo esperado.")
        pregunta("mapa")
        mapa_calor(d, base, medida)
        st.caption(f"Pasa el mouse sobre una casilla para ver el detalle. La cartera completa incumple {base:.1%}. "
                   f"Borde negro = perfil prioritario.")
    with der:
        st.markdown("**Lectura rápida**")
        p = perfiles(d, base).sort_values("Tasa", ascending=False)
        for _, r in p.head(3).iterrows():
            st.markdown(f"- **{r['Perfil']}**: incumple {r['Tasa']:.0%} ({en_palabras(r['Tasa'])}), "
                        f"{r['Razón']:.1f}× la cartera, {int(r['Solicitudes']):,} solicitudes.")
        nd = d[d["Endeudamiento"] == "Sin dato"]
        if len(nd) >= MIN_N:
            st.markdown(f"- Las solicitudes **sin dato de deuda/ingreso** ({len(nd):,}) incumplen "
                        f"{nd['BAD'].mean():.0%}: no tener el dato ya es una señal de riesgo.")
        st.caption("Más oscuro/rojo = más riesgo. El verde significa que el grupo se comporta como la cartera "
                   "o mejor.")
    fuente(d)


def pag_perfiles(d: pd.DataFrame, df: pd.DataFrame):
    base = d["BAD"].mean()
    p = perfiles(d, base)
    seccion("Perfiles a revisar", "¿Qué combinaciones de deuda y morosidad conviene revisar y qué hago con ellas?")
    leyenda()
    modo = st.radio("Mostrar", ["Prioritarios", "Prioritarios y a vigilar", "Todos"], horizontal=True,
                    index=1, label_visibility="collapsed")
    niveles = {"Prioritarios": ["Alta"], "Prioritarios y a vigilar": ["Alta", "Media"],
               "Todos": ["Alta", "Media", "Sin alerta"]}[modo]
    t = p[p["Nivel"].isin(niveles)].sort_values("Casos en exceso", ascending=False).reset_index(drop=True)
    if t.empty:
        st.info("Con estos filtros ningún perfil entra en esta lista.")
        return
    if True:
        v = pd.DataFrame({
            "Alerta": t["Nivel"].map(ESTADO_ICONO), "Perfil": t["Perfil"],
            "Solicitudes": t["Solicitudes"], "Tasa": t["Tasa"] * 100, "Veces la cartera": t["Razón"],
            "Casos de más": t["Casos en exceso"].round().astype(int)})
        ev = st.dataframe(
            v, hide_index=True, on_select="rerun", selection_mode="single-row", key="tabla_perfiles",
            height=min(36 * (len(v) + 1) + 8, 640),
            column_config={
                "Alerta": st.column_config.TextColumn(width=105,
                                                  help=f"Semáforo: Prioritario (rojo) = {UMBRAL_ALTA}× la cartera o más · Vigilar (ámbar) = {UMBRAL_MEDIA}–{UMBRAL_ALTA}× · Normal (verde) = menos · Pocos datos (gris) = menos de {MIN_N} solicitudes."),
                "Perfil": st.column_config.TextColumn(width="large"),
                "Solicitudes": st.column_config.NumberColumn(width=85),
                "Tasa": st.column_config.ProgressColumn("Tasa", format="%.0f %%", min_value=0, max_value=100,
                                                        width=95),
                "Veces la cartera": st.column_config.NumberColumn("× cartera", format="%.1f ×", width=75),
                "Casos de más": st.column_config.NumberColumn(width=80,
                    help="Incumplimientos por encima de lo esperado si el perfil se comportara como la cartera.")})
        st.caption("Haz clic en una fila para ver su detalle abajo.")
        fuente(d)
    filas = ev.selection.rows
    detalle(d, base, t.iloc[filas[0] if filas and filas[0] < len(t) else 0])


def detalle(d: pd.DataFrame, base: float, fila: pd.Series):
    sub = d[(d["Endeudamiento"] == fila["Endeudamiento"]) & (d["Morosidad"] == fila["Morosidad"])]
    col = COLOR_NIVEL[fila["Nivel"]]
    bg, fg = FONDO_NIVEL[fila["Nivel"]]
    banda = d[d["Endeudamiento"] == fila["Endeudamiento"]]["BAD"].mean()
    mismo = d[d["Morosidad"] == fila["Morosidad"]]["BAD"].mean()
    st.divider()
    izq, der = st.columns([1, 1], gap="large")
    with izq:
        st.markdown(
            f"<div style='font-size:13px'><b>{escape(fila['Perfil'])}</b></div>"
            f"<div style='font-size:38px;font-weight:700;color:{col}'>{fila['Tasa']:.0%} "
            f"<span class='chip' style='background:{bg};color:{fg}'>{ESTADO_ICONO[fila['Nivel']]}</span></div>"
            f"<div style='font-size:13px;color:#44506b'>{en_palabras(fila['Tasa'])} incumple · "
            f"{fila['Razón']:.1f}× la cartera · {int(fila['Solicitudes']):,} solicitudes</div>", unsafe_allow_html=True)
        pregunta("perfil")
        h = ["<div style='margin-top:8px;font-weight:600;font-size:13px'>¿Cómo se compara?</div>",
             barra_html("Este perfil", fila["Tasa"], col),
             barra_html("Toda la cartera", base, GRIS),
             barra_html("Misma deuda/ingreso", banda, GRIS),
             barra_html("Misma morosidad", mismo, GRIS),
             "<div style='margin-top:8px;font-weight:600;font-size:13px'>Según el motivo del préstamo</div>"]
        for m in ORD_MOTIVO:
            s = sub[sub["Motivo"] == m]
            if len(s) >= MIN_N:
                h.append(barra_html(m, s["BAD"].mean(), AMBAR, f"n={len(s)}"))
            else:
                h.append(f"<div style='font-size:13px;margin:3px 0'>{escape(m)}: n = {len(s)} "
                         f"(pocos datos, no se calcula)</div>")
        st.markdown("".join(h), unsafe_allow_html=True)
        with st.expander("Ver las solicitudes de este perfil"):
            vista = pd.DataFrame({
                "Monto": sub["LOAN"], "Valor propiedad": sub["VALUE"].where(sub.VALUE_FALTANTE == 0),
                "Ocupación": sub["Ocupación"], "Motivo": sub["Motivo"],
                "Incumplió": np.where(sub["BAD"] == 1, "Sí", "No")}).sort_values("Incumplió", ascending=False)
            st.dataframe(vista.head(300), hide_index=True, height=260)
            st.caption(f"Se muestran hasta 300 de {len(vista):,}. Primero las que incumplieron.")
    with der:
        if fila["Endeudamiento"] == "Sin dato":
            st.warning("**Falta la deuda sobre ingreso en este perfil:** solicitar comprobante de ingresos y "
                       "deudas antes de decidir.")
        nota = st.text_area("Nota para el expediente (opcional)", key=f"nota_{fila['Perfil']}", height=68)
        registro = None
        if st.button("Enviar a evaluación detallada", type="primary", key=f"b1_{fila['Perfil']}",
                     use_container_width=True):
            registro = "Enviar a evaluación detallada"
        b2, b3 = st.columns(2)
        if b2.button("Mantener condiciones", key=f"b2_{fila['Perfil']}", use_container_width=True):
            registro = "Mantener condiciones estándar"
        if b3.button("Pedir más información", key=f"b3_{fila['Perfil']}", use_container_width=True):
            registro = "Solicitar información adicional"
        if registro:
            st.session_state.setdefault("decisiones", []).append({
                "Hora": ahora().strftime("%H:%M:%S"),
                "Perfil": fila["Perfil"], "Decisión": registro, "Nota": nota})
        if st.session_state.get("decisiones"):
            with st.expander(f"Decisiones registradas en esta sesión ({len(st.session_state['decisiones'])})"):
                st.dataframe(pd.DataFrame(st.session_state["decisiones"]), hide_index=True)
                st.caption("Demostración: las decisiones solo viven en esta sesión; no se envían a ningún sistema.")


def pantalla_modelo(df=None):
    seccion("Desempeño del modelo", "¿Qué tan bien detecta el modelo a los clientes que no van a pagar?")
    st.caption("El tablero muestra el desempeño del modelo como apoyo; no aprueba ni rechaza solicitudes.")
    try:
        m = json.loads(MODELO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st.error("No se pudo leer modelo_sas.json. Revisa que exista y que el JSON sea válido.")
        return
    mc = m.get("matriz_confusion") or {}
    vn, fp, fn, vp = (mc.get(k) for k in ("verdaderos_negativos", "falsos_positivos",
                                          "falsos_negativos", "verdaderos_positivos"))
    hay_matriz = None not in (vn, fp, fn, vp)

    def semaforo(valor, meta):
        if valor is None:
            return GRIS
        return VERDE if valor >= meta else AMBAR if valor >= meta - 0.05 else ROJO

    def ref(valor, meta, fmt):
        if valor is None:
            return f"meta del equipo: {fmt(meta)}"
        return f"meta del equipo: {fmt(meta)} · {'cumple' if valor >= meta else 'no llega'}"

    auc, rec, pre, umb = m.get("auc"), m.get("recall"), m.get("precision"), m.get("umbral")
    fila_tiles([
        ("AUC", "Pendiente" if auc is None else f"{auc:.3f}", ref(auc, META_AUC, lambda x: f"{x:.2f}"),
         semaforo(auc, META_AUC), "Qué tan bien separa a quien paga de quien no (0.5 = azar, 1 = perfecto).",
         tip_meta(f"AUC {META_AUC:.2f}")),
        ("Recall (detección)", "Pendiente" if rec is None else f"{rec:.1%}",
         ref(rec, META_RECALL, lambda x: f"{x:.0%}"), semaforo(rec, META_RECALL),
         "De los que sí incumplieron, qué porcentaje detectó el modelo.", tip_meta(f"recall {META_RECALL:.0%}")),
        ("Precisión", "Pendiente" if pre is None else f"{pre:.1%}",
         "sin meta definida" if pre is None else f"{pre:.0%} de las alertas son reales", GRIS,
         "De los que el modelo marcó como riesgosos, cuántos sí incumplieron.",
         "Sin meta definida por el equipo, por eso no lleva semáforo."),
        ("Umbral", "Pendiente" if umb is None else f"{umb:.2f}", "referencia: 0.50 (SAS)", GRIS,
         "Probabilidad desde la cual el modelo marca a un cliente como riesgoso.",
         "Referencia de SAS: 0.50. Con un umbral más bajo se detectan más morosos, pero hay más falsas alertas."),
    ])
    if m.get("nombre_modelo") or m.get("conjunto_evaluacion"):
        st.caption(f"Modelo: {m.get('nombre_modelo') or '—'} · Conjunto de evaluación: "
                   f"{m.get('conjunto_evaluacion') or '—'}")
    st.write("")
    st.markdown("**Matriz de confusión** — aciertos y errores del modelo")
    pregunta("matriz")
    st.caption("Pasa el mouse sobre cada casilla para ver qué significa.")
    if hay_matriz:
        z = [[vn, fp], [fn, vp]]
        info = [[f"<b>Verdaderos negativos: {vn:,}</b><br>Pagan y el modelo lo anticipó<br>"
                 f"({vn / (vn + fp):.1%} de quienes pagan)",
                 f"<b>Falsos positivos: {fp:,}</b><br>Pagan, pero el modelo dio alerta<br>"
                 f"Costo: tiempo de revisión de más"],
                [f"<b>Falsos negativos: {fn:,}</b><br>Incumplen y el modelo no los detectó<br>"
                 f"El error más caro: aprobar a quien no paga",
                 f"<b>Verdaderos positivos: {vp:,}</b><br>Incumplen y el modelo los detectó<br>"
                 f"({vp / (vp + fn):.1%} de quienes incumplen)"]]
        fig = go.Figure(go.Heatmap(z=z, x=["Modelo dice: paga", "Modelo dice: incumple"],
                                   y=["Realidad: paga", "Realidad: incumple"], text=z, texttemplate="%{text:,}",
                                   hovertext=info, hovertemplate="%{hovertext}<extra></extra>",
                                   colorscale=[[0, "#eaf0f9"], [1, AZUL]], showscale=False))
        fig.update_yaxes(autorange="reversed", type="category")
        fig.update_xaxes(type="category")
        fig.update_layout(height=320, margin={"t": 10, "b": 10})
        st.plotly_chart(fig, config={"displayModeBar": False})
        r_, p_ = vp / (vp + fn), vp / (vp + fp)
        st.caption(f"Con esta matriz: recall {r_:.1%}, precisión {p_:.1%}, "
                   f"exactitud {(vp + vn) / (vp + vn + fp + fn):.1%}.")
        for nombre, calc, dado in (("recall", r_, rec), ("precisión", p_, pre)):
            if dado is not None and abs(calc - dado) > 0.005:
                st.warning(f"Revisa {nombre}: el valor del archivo ({dado:.1%}) no coincide con el que sale "
                           f"de la matriz ({calc:.1%}).")
    else:
        st.info("Pendiente: escribe los números de SAS en el archivo modelo_sas.json (junto a app.py) "
                "y recarga la página.")
    st.caption("Fuente: modelo desarrollado en SAS por el equipo (valores capturados en modelo_sas.json).")


# --------------------------------------------------------------------------- nueva solicitud (modelo preliminar)
# Modelo preliminar en Python (regresión logística con regularización). NO es el campeón de SAS:
# sirve para probar el flujo "capturar solicitud -> probabilidad de incumplimiento" mientras no
# se conecta el código de scoring de SAS. Se entrena con las filas de entrenamiento de SAS
# (_PartInd_ = 1) y se valida con las demás (_PartInd_ = 0, n = 1,788, el mismo conjunto de SAS).
COLS_FALTANTE = ["VALUE_FALTANTE", "DEBTINC_FALTANTE", "NINQ_FALTANTE", "DEROG_FALTANTE",
                 "DELINQ_FALTANTE", "YOJ_FALTANTE", "JOB_FALTANTE", "REASON_FALTANTE"]
COLS_CAT = ["JOB_Office", "JOB_Other", "JOB_ProfExe", "JOB_Sales", "JOB_Self", "REASON_HomeImp"]
NOMBRE_FACTOR = {
    "LOAN": "Monto del préstamo", "MORTDUE": "Deuda hipotecaria", "VALUE": "Valor de la propiedad",
    "YOJ": "Años en el empleo", "DEROG": "Reportes negativos", "DELINQ": "Líneas morosas",
    "CLAGE": "Antigüedad del crédito", "NINQ": "Consultas de crédito recientes",
    "CLNO": "Número de líneas de crédito", "DEBTINC": "Deuda sobre ingreso",
    "DEBT_hi": "Deuda sobre ingreso mayor a 45 %", "LTV": "Deuda hipotecaria sobre valor de la casa",
    "DELINQ_any": "Tiene líneas morosas", "DEROG_any": "Tiene reportes negativos",
    "CLAGE_lo": "Crédito con menos de 100 meses", "VALUE_FALTANTE": "Falta el valor de la propiedad",
    "DEBTINC_FALTANTE": "Falta la deuda sobre ingreso", "NINQ_FALTANTE": "Faltan las consultas recientes",
    "DEROG_FALTANTE": "Faltan los reportes negativos", "DELINQ_FALTANTE": "Faltan las líneas morosas",
    "YOJ_FALTANTE": "Falta la antigüedad en el empleo", "JOB_FALTANTE": "Falta la ocupación",
    "REASON_FALTANTE": "Falta el motivo", "JOB_Office": "Ocupación: oficina", "JOB_Other": "Ocupación: otra",
    "JOB_ProfExe": "Ocupación: profesional / ejecutivo", "JOB_Sales": "Ocupación: ventas",
    "JOB_Self": "Ocupación: autoempleo", "REASON_HomeImp": "Motivo: mejoras al hogar",
}


def caracteristicas(df: pd.DataFrame) -> pd.DataFrame:
    """Variables del modelo (transformaciones sencillas para que valores extremos no dominen)."""
    x = pd.DataFrame(index=df.index)
    for c in ("LOAN", "MORTDUE", "VALUE"):
        x[c] = np.log1p(df[c])
    x["YOJ"] = np.log1p(df["YOJ"])
    x["DEROG"] = df["DEROG"].clip(0, 4)
    x["DELINQ"] = df["DELINQ"].clip(0, 6)
    x["CLAGE"] = df["CLAGE"].clip(0, 400)
    x["NINQ"] = df["NINQ"].clip(0, 8)
    x["CLNO"] = df["CLNO"]
    x["DEBTINC"] = df["DEBTINC"].clip(0, 80)
    x["DEBT_hi"] = (df["DEBTINC"] > 45) * 1.0
    x["LTV"] = (df["MORTDUE"] / df["VALUE"]).clip(0, 3)
    x["DELINQ_any"] = (df["DELINQ"] > 0) * 1.0
    x["DEROG_any"] = (df["DEROG"] > 0) * 1.0
    x["CLAGE_lo"] = (df["CLAGE"] < 100) * 1.0
    for c in COLS_FALTANTE + COLS_CAT:
        x[c] = df[c]
    return x


def auc_rangos(y: np.ndarray, p: np.ndarray) -> float:
    r = pd.Series(p).rank().to_numpy()
    n1 = float(y.sum())
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


@st.cache_resource
def modelo_preliminar() -> dict:
    df = cargar()
    tr, va = df[df["_PartInd_"] == 1], df[df["_PartInd_"] == 0]
    xt = caracteristicas(tr)
    mu, sd = xt.mean(axis=0), xt.std(axis=0).replace(0, 1)
    z = np.c_[np.ones(len(xt)), ((xt - mu) / sd).to_numpy()]
    y = tr["BAD"].to_numpy(dtype=float)
    reg = 1.0 * np.eye(z.shape[1])
    reg[0, 0] = 0
    w = np.zeros(z.shape[1])
    for _ in range(50):                       # Newton–Raphson (regresión logística regularizada)
        p = 1 / (1 + np.exp(-z @ w))
        paso = np.linalg.solve((z * (p * (1 - p))[:, None]).T @ z + reg, z.T @ (p - y) + reg @ w)
        w -= paso
        if np.abs(paso).max() < 1e-8:
            break
    m = {"w": w, "mu": mu, "sd": sd, "cols": list(xt.columns), "n_entrena": len(tr), "n_valida": len(va)}
    pv = predecir(m, va)
    m["auc"] = auc_rangos(va["BAD"].to_numpy(), pv)
    marca = pv >= 0.5
    m["recall"] = float((marca & (va["BAD"] == 1)).sum() / (va["BAD"] == 1).sum())
    m["precision"] = float((marca & (va["BAD"] == 1)).sum() / max(marca.sum(), 1))
    # valores con los que el CSV imputó cada dato faltante (para solicitudes con "no disponible")
    m["imputado"] = {c: float(df.loc[df[f"{c}_FALTANTE"] == 1, c].median())
                     for c in ("DEBTINC", "DEROG", "DELINQ", "NINQ", "YOJ")}
    return m


def predecir(m: dict, filas: pd.DataFrame) -> np.ndarray:
    x = caracteristicas(filas)[m["cols"]]
    z = np.c_[np.ones(len(x)), ((x - m["mu"]) / m["sd"]).to_numpy()]
    return 1 / (1 + np.exp(-z @ m["w"]))


BINARIAS = set(COLS_FALTANTE + COLS_CAT + ["DEBT_hi", "DELINQ_any", "DEROG_any", "CLAGE_lo"])


def texto_factor(c: str, f: pd.Series) -> str:
    """Nombre del factor con el valor capturado (ej. «Deuda sobre ingreso: 50 %»)."""
    v = {"DEBTINC": f"{f.DEBTINC:.0f} %", "DELINQ": f"{f.DELINQ:.0f}", "DEROG": f"{f.DEROG:.0f}",
         "CLAGE": f"{f.CLAGE:.0f} meses", "NINQ": f"{f.NINQ:.0f}", "CLNO": f"{f.CLNO:.0f}",
         "YOJ": f"{f.YOJ:.1f} años", "LOAN": f"${f.LOAN:,.0f}", "MORTDUE": f"${f.MORTDUE:,.0f}",
         "VALUE": f"${f.VALUE:,.0f}", "LTV": f"{f.MORTDUE / f.VALUE:.0%}"}.get(c)
    return f"{NOMBRE_FACTOR.get(c, c)}: {v}" if v else NOMBRE_FACTOR.get(c, c)


def factores(m: dict, fila: pd.DataFrame) -> list:
    """Aportes por variable frente a un solicitante promedio (positivo = sube el riesgo).
    Las variables de tipo sí/no solo cuentan cuando valen 1 (si no, el nombre diría lo contrario)."""
    x = caracteristicas(fila)[m["cols"]].iloc[0]
    aporte = ((x - m["mu"]) / m["sd"]).to_numpy() * m["w"][1:]
    pares = [(c, a) for c, a, v in zip(m["cols"], aporte, x) if c not in BINARIAS or v == 1]
    return sorted(pares, key=lambda t: -abs(t[1]))


def pantalla_solicitud(df: pd.DataFrame):
    seccion("Nueva solicitud", "¿Qué probabilidad de incumplimiento tiene este solicitante?")
    st.caption("Captura los datos de una solicitud y el modelo preliminar estima la probabilidad. "
               "Es un apoyo para el analista: no aprueba ni rechaza.")
    m = modelo_preliminar()
    base = df["BAD"].mean()
    med = df[["LOAN", "MORTDUE", "VALUE", "YOJ", "CLAGE", "CLNO"]].median()
    ocup = ["Gerencia", "Oficina", "Prof. / Ejecutivo", "Ventas", "Autoempleo", "Otro", "Sin dato"]
    motivos = ["Consolidación de deudas", "Mejoras al hogar", "Sin dato"]

    with st.form("solicitud"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**El préstamo**")
            loan = st.number_input("Monto solicitado ($)", 1_000, 100_000, int(med.LOAN), 500)
            mort = st.number_input("Deuda hipotecaria actual ($)", 0, 500_000, int(med.MORTDUE), 1_000)
            valor = st.number_input("Valor de la propiedad ($)", 5_000, 1_000_000, int(med.VALUE), 1_000)
            motivo = st.selectbox("Motivo del préstamo", motivos)
        with c2:
            st.markdown("**El solicitante**")
            job = st.selectbox("Ocupación", ocup)
            yoj = st.number_input("Años en el empleo actual", 0.0, 45.0, float(med.YOJ), 0.5)
            yoj_nd = st.checkbox("Años en el empleo: no disponible")
            deuda = st.number_input("Deuda sobre ingreso (%)", 0.0, 200.0, 35.0, 0.5,
                                    help="Porcentaje del ingreso mensual que ya se va en pagar deudas.")
            deuda_nd = st.checkbox("Deuda sobre ingreso: no disponible")
        with c3:
            st.markdown("**Historial de crédito**")
            delinq = st.number_input("Líneas de crédito morosas", 0, 15, 0)
            delinq_nd = st.checkbox("Líneas morosas: no disponible")
            derog = st.number_input("Reportes negativos", 0, 10, 0)
            derog_nd = st.checkbox("Reportes negativos: no disponible")
            clage = st.number_input("Antigüedad del crédito más antiguo (meses)", 0.0, 650.0, float(med.CLAGE), 5.0)
            ninq = st.number_input("Consultas de crédito recientes", 0, 17, 0)
            ninq_nd = st.checkbox("Consultas recientes: no disponible")
            clno = st.number_input("Número de líneas de crédito", 0, 71, int(med.CLNO))
        enviado = st.form_submit_button("Calcular probabilidad", type="primary")

    if not enviado:
        st.info("Llena el formulario y pulsa **Calcular probabilidad**. "
                "Si marcas «no disponible», se ignora el valor de ese campo.")
        _nota_modelo(m)
        return

    imp = m["imputado"]
    fila = pd.DataFrame([{
        "LOAN": loan, "MORTDUE": mort, "VALUE": valor,
        "YOJ": imp["YOJ"] if yoj_nd else yoj, "DEROG": imp["DEROG"] if derog_nd else derog,
        "DELINQ": imp["DELINQ"] if delinq_nd else delinq, "CLAGE": clage,
        "NINQ": imp["NINQ"] if ninq_nd else ninq, "CLNO": clno,
        "DEBTINC": imp["DEBTINC"] if deuda_nd else deuda,
        "VALUE_FALTANTE": 0, "DEBTINC_FALTANTE": int(deuda_nd), "NINQ_FALTANTE": int(ninq_nd),
        "DEROG_FALTANTE": int(derog_nd), "DELINQ_FALTANTE": int(delinq_nd), "YOJ_FALTANTE": int(yoj_nd),
        "JOB_FALTANTE": int(job == "Sin dato"), "REASON_FALTANTE": int(motivo == "Sin dato"),
        "JOB_Office": int(job == "Oficina"), "JOB_Other": int(job == "Otro"),
        "JOB_ProfExe": int(job == "Prof. / Ejecutivo"), "JOB_Sales": int(job == "Ventas"),
        "JOB_Self": int(job == "Autoempleo"), "REASON_HomeImp": int(motivo == "Mejoras al hogar"),
    }])
    prob = float(predecir(m, fila)[0])
    razon = prob / base
    color = ROJO if razon >= UMBRAL_ALTA else AMBAR if razon >= UMBRAL_MEDIA else VERDE
    estado = {ROJO: "Prioritario", AMBAR: "Vigilar", VERDE: "Normal"}[color]

    st.write("")
    fila_tiles([
        ("Probabilidad de incumplimiento", f"{prob:.1%}", f"cartera: {base:.1%}", color,
         "Probabilidad estimada por el modelo preliminar de que este solicitante no pague.",
         f"Verde: menos de {UMBRAL_MEDIA}× la cartera. Ámbar: {UMBRAL_MEDIA}–{UMBRAL_ALTA}×. "
         f"Rojo: {UMBRAL_ALTA}× o más."),
        ("Comparado con la cartera", f"{razon:.1f}×", "1.0× = igual que el promedio", color,
         "Cuántas veces la probabilidad media de la cartera es la de este solicitante.",
         "Es la misma regla de semáforo que usa el resto del tablero."),
        ("Estado", {"Prioritario": "▲ Prioritario", "Vigilar": "◆ Vigilar", "Normal": "● Normal"}[estado],
         {"Prioritario": "revisar con detalle", "Vigilar": "revisar con atención",
                            "Normal": "sin alerta"}[estado], color,
         "Lectura del semáforo para decidir cuánta revisión necesita la solicitud.",
         TIP_COLOR.get(color, "")),
    ])
    if deuda_nd:
        st.warning("**Cuando falte la deuda sobre ingreso:** solicitar comprobante de ingresos y deudas "
                   "antes de decidir. En la base, 62 % de las solicitudes sin ese dato incumplió.")

    fs = [(c, a) for c, a in factores(m, fila) if abs(a) >= 0.05]
    suben, bajan = [t for t in fs if t[1] > 0][:4], [t for t in fs if t[1] < 0][:3]
    st.markdown("**Qué pesa más en este resultado** (frente a un solicitante promedio)")
    ca, cb = st.columns(2)
    with ca:
        st.markdown("Sube el riesgo")
        for c, a in suben or [("—", 0)]:
            st.markdown(f"- {texto_factor(c, fila.iloc[0]) if c != '—' else c}")
    with cb:
        st.markdown("Baja el riesgo")
        for c, a in bajan or [("—", 0)]:
            st.markdown(f"- {texto_factor(c, fila.iloc[0]) if c != '—' else c}")
    _nota_modelo(m)


def _nota_modelo(m: dict):
    st.caption(
        f"**Modelo preliminar** (regresión logística en Python), entrenado con {m['n_entrena']:,} solicitudes y "
        f"validado con {m['n_valida']:,}: AUC {m['auc']:.3f}. El modelo campeón de SAS (Gradient Boosting, "
        "AUC 0.965) todavía no está conectado a este formulario. Demostración: los datos capturados no se guardan.")



# --------------------------------------------------------------------------- pantalla del Gerente
def grafica_burbujas(s: pd.DataFrame, base: float):
    s = s[s["Nivel"] != "Muestra baja"]
    fig = go.Figure()
    xmin, xmax = max(s["Solicitudes"].min() * 0.7, 1), s["Solicitudes"].max() * 1.5
    ymax = min(1.0, float(s["Tasa"].max()) * 1.15)
    for y0, y1, c in ((0, base * UMBRAL_MEDIA, VERDE), (base * UMBRAL_MEDIA, base * UMBRAL_ALTA, AMBAR),
                      (base * UMBRAL_ALTA, ymax, ROJO)):
        fig.add_hrect(y0=y0, y1=y1, fillcolor=c, opacity=0.08, line_width=0)
    for niv in ("Sin alerta", "Media", "Alta"):
        g = s[s["Nivel"] == niv]
        fig.add_trace(go.Scatter(
            x=g["Solicitudes"], y=g["Tasa"], mode="markers+text", name=ESTADO_ICONO[niv],
            marker={"size": 13, "color": COLOR_NIVEL[niv], "symbol": SIMBOLO_PLOTLY[niv],
                    "line": {"width": 1, "color": "#fff"}},
            text=g["Etiqueta"] if niv == "Alta" else None, textposition="top center",
            textfont={"size": 10}, cliponaxis=False,
            customdata=list(g["Etiqueta"]),
            hovertext=[f"<b>{e}</b><br>{int(n):,} solicitudes<br>Incumplen {t:.0%} ({en_palabras(t)})<br>"
                       f"{r:.1f}× la cartera · casos de más: {c:+.0f}<br><i>Haz clic para ver el detalle</i>"
                       for e, n, t, r, c in zip(g["Etiqueta"], g["Solicitudes"], g["Tasa"], g["Razón vs cartera"],
                                                g["Casos en exceso"])],
            hovertemplate="%{hovertext}<extra></extra>"))
    fig.add_hline(y=base, line_dash="dash", line_color="#333",
                  annotation_text=f"Cartera {base:.1%}", annotation_position="bottom right")
    fig.update_xaxes(type="log", range=[np.log10(xmin), np.log10(xmax)], title="Solicitudes del grupo (escala log)")
    fig.update_yaxes(tickformat=".0%", range=[0, ymax], title="Tasa de incumplimiento")
    fig.update_layout(height=470, margin={"t": 10, "b": 10, "l": 10, "r": 10},
                      legend={"orientation": "h", "y": -0.2})
    return fig


def grafica_grupo(d: pd.DataFrame, dim: str, base: float, tope: float):
    titulo, orden = DIMS[dim]
    g = d.groupby(dim)["BAD"].agg(["mean", "size"]).reindex(orden).dropna()
    g = g.sort_values("mean", ascending=True)
    cols = [COLOR_NIVEL[nivel(m / base, int(n))] for m, n in zip(g["mean"], g["size"])]
    fig = go.Figure(go.Bar(
        x=g["mean"], y=g.index, orientation="h", marker_color=cols,
        text=[f"{m:.0%} · {int(n):,}" for m, n in zip(g["mean"], g["size"])], textposition="outside",
        cliponaxis=False, hovertext=hover_barras(g, base), hovertemplate="%{hovertext}<extra></extra>"))
    fig.add_vline(x=base, line_dash="dash", line_color="#333",
                  annotation_text=f"Cartera {base:.1%}", annotation_position="top")
    fig.update_yaxes(type="category", automargin=True)
    fig.update_xaxes(tickformat=".0%", range=[0, tope])
    fig.update_layout(title=titulo, height=300, bargap=0.35, margin={"t": 50, "b": 10, "l": 10, "r": 40})
    return fig


_ZONA = None   # contenedor de la barra lateral donde cada pantalla puede poner sus controles


def detalle_grupo(r: pd.Series, base: float):
    col = COLOR_NIVEL[r["Nivel"]]
    bg, fg = FONDO_NIVEL[r["Nivel"]]
    accion = {"Alta": "Dirigir atención a este grupo: su incumplimiento está claramente por encima de la cartera.",
              "Media": "Mantenerlo en seguimiento: está por encima de la cartera, aunque no tanto.",
              "Sin alerta": "No requiere atención especial: se comporta como la cartera o mejor.",
              "Muestra baja": f"Pocos datos (menos de {MIN_N} solicitudes): no se calcula alerta."}[r["Nivel"]]
    st.divider()
    a, b = st.columns([1, 1], gap="large")
    with a:
        st.markdown(
            f"<div style='font-size:13px'><b>{escape(r['Etiqueta'])}</b> · {escape(r['Variable'])}</div>"
            f"<div style='font-size:38px;font-weight:700;color:{col}'>{r['Tasa']:.0%} "
            f"<span class='chip' style='background:{bg};color:{fg}'>{ESTADO_ICONO[r['Nivel']]}</span></div>"
            f"<div style='font-size:13px;color:#44506b'>{en_palabras(r['Tasa'])} incumple · "
            f"{r['Razón vs cartera']:.1f}× la cartera · {int(r['Solicitudes']):,} solicitudes · "
            f"{int(r['Incumplimientos']):,} incumplieron</div>", unsafe_allow_html=True)
    with b:
        st.markdown("".join([
            "<div style='font-weight:600;font-size:13px'>¿Cómo se compara?</div>",
            barra_html("Este grupo", r["Tasa"], col), barra_html("Toda la cartera", base, GRIS),
            f"<div style='font-size:13px;margin-top:6px'><b>Casos de más:</b> {r['Casos en exceso']:+,.0f} "
            f"incumplimientos respecto a lo esperado.</div>",
            f"<div style='font-size:13px;margin-top:4px;color:#44506b'>{escape(accion)}</div>"]),
            unsafe_allow_html=True)


def pantalla_gerente(d: pd.DataFrame, df: pd.DataFrame):
    base, base_total = d["BAD"].mean(), df["BAD"].mean()
    s_all = segmentos(d)
    nombre_dim = {v[0]: k for k, v in DIMS.items()}
    nivel_de = {"Prioritario": "Alta", "Vigilar": "Media"}
    zona = _ZONA if _ZONA is not None else st.sidebar
    with zona:
        st.markdown("**Ajustar la vista**")
        tipos = st.multiselect("Tipos de grupo", list(nombre_dim), default=list(nombre_dim), key="g_tipos",
                               help="Elige qué características se comparan.")
        alertas = st.multiselect("Alertas en la tabla", list(nivel_de), default=list(nivel_de), key="g_alertas",
                                 help="Prioritario = 1.5× la cartera o más. Vigilar = 1.15× a 1.5×.")
        orden = st.radio("Ordenar la tabla por", ["Casos de más", "Tasa", "Solicitudes"], key="g_orden")
        st.caption("Estos controles solo cambian lo que ves en esta pantalla. Los filtros de la cartera están "
                   "arriba a la derecha.")
    s = s_all[s_all["Dimensión"].isin([nombre_dim[t] for t in tipos])]
    ev = s[s["Nivel"] != "Muestra baja"]
    n_alta = int((s["Nivel"] == "Alta").sum())
    pes_alta = float(s[s["Nivel"] == "Alta"]["Casos en exceso"].sum())
    seccion("Comparativo de cartera", "¿Qué grupos de clientes incumplen más que el resto?")
    leyenda()
    fila_tiles([
        ("Solicitudes analizadas", f"{len(d):,}", f"{len(d) / len(df):.0%} de la cartera completa", AZUL, ""),
        ("Tasa de incumplimiento", f"{base:.1%}", f"{en_palabras(base)} · cartera completa: {base_total:.1%}",
         COLOR_NIVEL[nivel(base / base_total if base_total else 1, len(d))], ""),
        ("Grupos con alerta alta", f"{n_alta}", f"de {len(ev)} grupos evaluados · {pes_alta:+,.0f} casos de más",
         ROJO if n_alta else VERDE, f"Grupos con al menos {MIN_N} solicitudes."),
    ])
    st.write("")
    if s.empty or ev.empty:
        st.info("Elige al menos un tipo de grupo en el panel de la izquierda.")
        fuente(d)
        return
    izq, der = st.columns([0.85, 1.15], gap="large")
    with izq:
        st.markdown("**Cada punto es un grupo de clientes**")
        pregunta("burbujas")
        st.caption("Más arriba = incumple más. Más a la derecha = más solicitudes. Haz clic en un punto para ver "
                   "su detalle abajo.")
        evento = st.plotly_chart(grafica_burbujas(s, base), config={"displayModeBar": False},
                                 on_select="rerun", selection_mode="points", key="burbujas_gerente")
    with der:
        st.markdown("**Grupos que requieren atención**")
        st.caption("Ordenados por la medida que elijas en el panel de la izquierda.")
        col_orden = {"Casos de más": "Casos en exceso", "Tasa": "Tasa", "Solicitudes": "Solicitudes"}[orden]
        a = s[s["Nivel"].isin([nivel_de[x] for x in alertas])].sort_values(col_orden, ascending=False)
        if a.empty:
            st.info("Con estos filtros ningún grupo llega a alerta.")
        else:
            tabla_segmentos(a, "gerente_tabla", incluir_variable=False, compacta=True)
        st.download_button("Descargar tabla (CSV)", a.drop(columns=["Dimensión"]).to_csv(index=False).encode("utf-8"),
                           "grupos_con_atencion.csv", "text/csv", disabled=a.empty)
    puntos = evento.selection.points if evento is not None and evento.selection else []
    if puntos:
        cd = puntos[0].get("customdata")
        etiqueta_sel = cd[0] if isinstance(cd, (list, tuple)) and cd else cd
        fila = s[s["Etiqueta"] == etiqueta_sel]
        if not fila.empty:
            detalle_grupo(fila.iloc[0], base)
    fuente(d)
    with st.expander("Ver el comparativo por tipo de grupo (barras)"):
        tope = max(0.7, float(ev["Tasa"].max()) * 1.2)
        dims = [nombre_dim[t] for t in tipos]
        for i in range(0, len(dims), 3):
            for col, dim in zip(st.columns(3), dims[i:i + 3]):
                col.plotly_chart(grafica_grupo(d, dim, base, tope), config={"displayModeBar": False})
        st.caption("Barra roja/ámbar/verde según el semáforo. Texto: tasa · solicitudes. Misma escala en todas.")


# --------------------------------------------------------------------------- pantalla del Supervisor
def pantalla_supervisor(d: pd.DataFrame, df: pd.DataFrame):
    base = d["BAD"].mean()
    s = segmentos(d)
    s = s[s["Nivel"] != "Muestra baja"].copy()
    s["Clave"] = s["Dimensión"] + "|" + s["Segmento"]
    marcados = st.session_state.setdefault("seguimiento", set())
    cuenta = s["Nivel"].value_counts()
    tot = len(s)
    seccion("Seguimiento de cartera", "¿Qué grupos hay que vigilar y cuáles ya marqué para seguimiento?")
    leyenda()
    fila_tiles([
        ("Prioritarios", f"{cuenta.get('Alta', 0)}", f"de {tot} grupos evaluados", ROJO, f"≥ {UMBRAL_ALTA}× la cartera."),
        ("A vigilar", f"{cuenta.get('Media', 0)}", f"de {tot} grupos evaluados", AMBAR,
         f"{UMBRAL_MEDIA}× a {UMBRAL_ALTA}× la cartera."),
        ("Normales", f"{cuenta.get('Sin alerta', 0)}", f"de {tot} grupos evaluados", VERDE,
         f"menos de {UMBRAL_MEDIA}× la cartera."),
        ("En seguimiento", f"{len(marcados & set(s['Clave']))}", "marcados por ti en esta sesión", AZUL,
         "Marca filas en la tabla y usa los botones."),
    ])
    st.write("")
    filtro = st.radio("Mostrar", ["Todos", "Prioritario", "Vigilar", "Normal"], horizontal=True, index=1,
                      label_visibility="collapsed")
    mapa = {"Prioritario": "Alta", "Vigilar": "Media", "Normal": "Sin alerta"}
    sel = s if filtro == "Todos" else s[s["Nivel"] == mapa[filtro]]
    sel = sel.sort_values("Tasa", ascending=False).reset_index(drop=True)
    if sel.empty:
        st.info("No hay grupos en este estado con los filtros actuales.")
        return
    v = pd.DataFrame({
        "Seguimiento": np.where(sel["Clave"].isin(marcados), "En seguimiento", ""),
        "Alerta": sel["Nivel"].map(ESTADO_ICONO), "Grupo": sel["Etiqueta"], "Variable": sel["Variable"],
        "Solicitudes": sel["Solicitudes"], "Tasa": sel["Tasa"] * 100, "En palabras": sel["Tasa"].map(en_palabras),
        "Veces la cartera": sel["Razón vs cartera"]})
    ev = st.dataframe(
        v, hide_index=True, on_select="rerun", selection_mode="multi-row", key="tabla_supervisor",
        height=min(36 * (len(v) + 1) + 8, 640),
        column_config={
            "Tasa": st.column_config.ProgressColumn("Tasa de incumplimiento", format="%.0f %%", min_value=0,
                                                    max_value=100),
            "Veces la cartera": st.column_config.NumberColumn("× la cartera", format="%.1f ×"),
            "En palabras": st.column_config.TextColumn("Dicho fácil")})
    filas = [i for i in ev.selection.rows if i < len(sel)]
    claves = set(sel.loc[filas, "Clave"]) if filas else set()
    b1, b2, b3, b4 = st.columns([1.3, 1.3, 1.1, 1.4])
    if b1.button(f"Marcar seleccionados ({len(claves)})", type="primary", disabled=not claves):
        st.session_state["seguimiento"] |= claves
        st.rerun()
    if b2.button("Quitar de seguimiento", disabled=not (claves & marcados)):
        st.session_state["seguimiento"] -= claves
        st.rerun()
    columnas = ["Dimensión", "Etiqueta", "Solicitudes", "Incumplimientos", "Tasa", "Razón vs cartera", "Nivel"]
    elegidos = s[s["Clave"].isin(marcados)]
    b3.download_button("Descargar todos", s[columnas].to_csv(index=False).encode("utf-8"),
                       "grupos_todos.csv", "text/csv")
    b4.download_button(f"Descargar en seguimiento ({len(elegidos)})",
                       elegidos[columnas].to_csv(index=False).encode("utf-8"),
                       "grupos_en_seguimiento.csv", "text/csv", disabled=elegidos.empty)
    st.caption("Selecciona una o varias filas (casilla a la izquierda). El seguimiento solo vive en esta sesión.")
    fuente(d)


# --------------------------------------------------------------------------- acceso y ruteo
def login(usuarios: dict):
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        if LOGO.exists():
            st.image(str(LOGO), width=130)
        st.markdown("<span style='font-size:26px;font-weight:700;color:#0B1A8C'>Banco Siete</span><br>"
                    "Plataforma de Créditos Hipotecarios", unsafe_allow_html=True)
        st.header("¡Bienvenid@!")
        bloqueado = st.session_state.get("intentos", 0) >= MAX_INTENTOS
        with st.form("login"):
            u = st.text_input("Usuario", placeholder="(Ingresa tu usuario)")
            p = st.text_input("Contraseña", type="password", placeholder="(Ingresa tu contraseña)")
            if st.form_submit_button("Iniciar sesión", disabled=bloqueado):
                if u in usuarios and verificar_clave(p, usuarios[u][0]):
                    st.session_state["user"] = u
                    st.session_state["intentos"] = 0
                    st.rerun()
                st.session_state["intentos"] = st.session_state.get("intentos", 0) + 1
                st.error("Usuario o contraseña incorrectos.")
        if st.session_state.get("intentos", 0) >= MAX_INTENTOS:
            st.error("Demasiados intentos en esta sesión. Recarga la página para intentar de nuevo.")
        with st.expander("¿No tienes acceso?"):
            st.write("Cada persona tiene su propia cuenta y un rol (Analista, Gerente o Supervisor) que define "
                     "qué pantallas ve. Pide tus credenciales al equipo responsable del tablero.")


def glosario():
    with st.sidebar.expander("¿Qué significa cada término?"):
        for nombre, tecnico, texto in TERMINOS:
            sufijo = f" *({tecnico})*" if tecnico != "—" else ""
            st.markdown(f"**{nombre}**{sufijo}  \n{texto}")


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    usuarios = cargar_usuarios()
    if st.session_state.get("user") not in usuarios:
        st.session_state.pop("user", None)
        login(usuarios)
        st.stop()
    rol = usuarios[st.session_state["user"]][1]
    if rol not in PANTALLAS:
        st.error("Tu cuenta tiene un rol no reconocido. Avisa al equipo responsable.")
        st.stop()
    df = cargar()
    st.sidebar.markdown(f"**Sesión:** {st.session_state['user']}  \n**Rol:** {rol}")
    paginas = PANTALLAS[rol]
    pagina = st.sidebar.radio("Pantalla", paginas) if len(paginas) > 1 else paginas[0]
    if pagina not in PANTALLAS[rol]:  # control de acceso: cada rol solo llega a sus pantallas
        st.stop()
    global _ZONA
    _ZONA = st.sidebar.container()
    glosario()
    if st.sidebar.button("Cerrar sesión"):
        for k in list(st.session_state):
            del st.session_state[k]
        st.rerun()
    con_filtros = pagina not in ("Desempeño del modelo", "Nueva solicitud")
    encabezado(df, con_filtros)
    if not con_filtros:
        (pantalla_modelo if pagina == "Desempeño del modelo" else pantalla_solicitud)(df)
        return
    d = aplicar_filtros(df)
    if d.empty:  # estado vacío («nada seleccionado»): se declara y se detiene todo lo que sigue
        st.warning("Con estos filtros no hay solicitudes, así que no hay nada que mostrar. "
                   "Abre Filtros y pulsa Restablecer, o elige al menos una opción en cada filtro.")
        st.stop()
    lectura_filtros(df, d)
    {"Portafolio": pag_resumen, "Mapa de riesgo": pag_mapa, "Perfiles a revisar": pag_perfiles,
     "Comparativo de cartera": pantalla_gerente, "Seguimiento de cartera": pantalla_supervisor}[pagina](d, df)


main()
