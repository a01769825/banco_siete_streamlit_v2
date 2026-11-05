"""Banco Siete · Plataforma de Créditos Hipotecarios (Streamlit) — versión 2.

Uso:   streamlit run app.py
Archivos necesarios en la misma carpeta:
    hmeq_preparado_1_con_motivo.csv   datos
    logo.png               logo (opcional)
    modelo_sas.json        resultados del modelo de SAS (se llenan a mano)
"""
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
                   layout="wide")

# --- Reglas del "Cierre de Condiciones" y metas del equipo (se pueden ajustar aquí) ------------
FUENTE = "HMEQ_Preparado"
MIN_N = 30                 # con menos solicitudes no se calcula alerta
UMBRAL_ALTA = 1.5          # tasa del segmento / tasa de la cartera
UMBRAL_MEDIA = 1.15
META_AUC = 0.85            # hipótesis H4a del plan de trabajo
META_RECALL = 0.70
PESO_PRIORITARIOS = (0.10, 0.25)   # % de solicitudes en perfiles prioritarios: verde < 10 %, ámbar < 25 %

# Usuarios de DEMOSTRACIÓN: no es seguridad real.
USUARIOS = {
    "analista":   ("demo123", "Analista"),
    "gerente":    ("demo123", "Gerente"),
    "supervisor": ("demo123", "Supervisor"),
}
PANTALLAS = {
    "Analista":   ["Resumen", "Mapa de riesgo", "Perfiles a revisar", "Desempeño del modelo"],
    "Gerente":    ["Comparativo de cartera"],
    "Supervisor": ["Seguimiento de cartera"],
}

ORD_DELINQ = ["0", "1", "2", "3 o más", "Sin dato"]
ORD_DEBTINC = ["< 30 %", "30–35 %", "35–40 %", "40–45 %", "> 45 %", "Sin dato"]
ORD_JOB = ["Gerencia", "Oficina", "Prof. / Ejecutivo", "Ventas", "Autoempleo", "Otro", "Sin dato"]
ORD_MOTIVO = ["Mejoras al hogar", "Consolidación", "Sin dato"]
ORD_MONTO = ["< $15 mil", "$15–25 mil", "$25–40 mil", "> $40 mil"]

# columna interna -> (nombre para personas, orden)
DIMS = {
    "Ocupación": ("Ocupación del cliente", ORD_JOB),
    "Endeudamiento": ("Deuda sobre ingreso", ORD_DEBTINC),
    "Morosidad": ("Líneas de crédito morosas", ORD_DELINQ),
    "Motivo": ("Motivo del préstamo", ORD_MOTIVO),
    "Monto": ("Monto solicitado", ORD_MONTO),
}

# Identidad visual
AZUL, AZUL_CLARO, FONDO = "#0B1A8C", "#e6e9f7", "#f4f5fa"
CELESTE, NARANJA_MARCA = "#5aa9f0", "#f2b36b"
ROJO, AMBAR, VERDE, GRIS = "#c0392b", "#d99a1c", "#2e8b57", "#8a93ad"
COLOR_NIVEL = {"Alta": ROJO, "Media": AMBAR, "Sin alerta": VERDE, "Muestra baja": GRIS}
FONDO_NIVEL = {"Alta": ("#f6cbc5", "#7a1f12"), "Media": ("#fae6b4", "#6b4e00"),
               "Sin alerta": ("#d3ebdd", "#1d5c3b"), "Muestra baja": ("#eceff4", "#6b7488")}
ESTADO = {"Alta": "Prioritario", "Media": "Vigilar", "Sin alerta": "Normal", "Muestra baja": "Pocos datos"}

TERMINOS = [
    ("Incumplimiento", "BAD", "El cliente dejó de pagar o cayó en mora grave."),
    ("Tasa de incumplimiento", "—", "De cada 100 solicitudes, cuántas terminaron en incumplimiento."),
    ("Cartera", "—", "El conjunto de solicitudes que se está viendo (con los filtros aplicados)."),
    ("Veces la cartera (×)", "—", "La tasa del grupo dividida entre la tasa de la cartera. 2× = incumple el doble."),
    ("Casos de más", "—", "Incumplimientos que tiene el grupo por encima de lo esperado si se comportara "
                          "como la cartera."),
    ("Deuda sobre ingreso", "DEBTINC", "Qué parte del ingreso del cliente ya se va en pagar deudas."),
    ("Líneas de crédito morosas", "DELINQ", "Cuántas líneas de crédito del cliente tienen pagos atrasados."),
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
.chip {{display:inline-block; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600;}}
</style>
"""


def tile(titulo: str, valor: str, ref: str, color: str, ayuda: str = ""):
    """Indicador con punto de semáforo y su comparación contra una referencia."""
    st.markdown(
        f"<div class='tile' style='border-left:6px solid {color}'><div class='t'>{escape(titulo)}</div>"
        f"<div class='v'>{escape(valor)}</div>"
        f"<div class='r'><span class='dot' style='background:{color}'></span>{escape(ref)}</div>"
        f"<div class='a'>{escape(ayuda)}</div></div>", unsafe_allow_html=True)


def fila_tiles(items):
    for col, it in zip(st.columns(len(items)), items):
        with col:
            tile(*it)


def seccion(titulo: str, pregunta: str):
    st.subheader(titulo)
    st.markdown(f"<p class='sub'>{pregunta}</p>", unsafe_allow_html=True)


def leyenda():
    st.markdown(
        "<div style='font-size:12.5px;color:#44506b;margin:2px 0 8px 0'><b>Semáforo</b> (compara cada grupo "
        f"con la tasa de la cartera): <span class='dot' style='background:{VERDE}'></span>normal &lt; "
        f"{UMBRAL_MEDIA}× &nbsp; <span class='dot' style='background:{AMBAR}'></span>vigilar "
        f"{UMBRAL_MEDIA}–{UMBRAL_ALTA}× &nbsp; <span class='dot' style='background:{ROJO}'></span>"
        f"prioritario ≥ {UMBRAL_ALTA}× &nbsp; <span class='dot' style='background:{GRIS}'></span>pocos datos "
        f"(&lt; {MIN_N} solicitudes)</div>", unsafe_allow_html=True)


def barra_html(texto: str, valor: float, color: str, extra: str = "", marca: float | None = None):
    ancho = max(0.0, min(valor, 1.0)) * 100
    tick = (f"<div style='position:absolute;left:{min(marca, 1) * 100:.1f}%;top:-2px;width:2px;height:12px;"
            f"background:#222'></div>" if marca is not None else "")
    return (f"<div style='display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px'>"
            f"<div style='width:38%'>{escape(texto)}</div>"
            f"<div style='position:relative;flex:1;height:8px;background:#e6e9f0;border-radius:4px'>"
            f"<div style='width:{ancho:.1f}%;height:8px;background:{color};border-radius:4px'></div>{tick}</div>"
            f"<div style='width:24%;text-align:right'><b>{valor:.0%}</b> {escape(extra)}</div></div>")


def mapa_calor(d: pd.DataFrame, base: float):
    celdas = d.groupby(["Endeudamiento", "Morosidad"])["BAD"].agg(["mean", "size"])
    filas = d.groupby("Endeudamiento")["BAD"].agg(["mean", "size"])
    cols = d.groupby("Morosidad")["BAD"].agg(["mean", "size"])
    th = "style='padding:4px;font-size:12px;color:#44506b;text-align:center'"
    nom_col = {"0": "0", "1": "1", "2": "2", "3 o más": "3 o más", "Sin dato": "Sin dato"}
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
            if n < MIN_N:
                h.append(f"<td style='background:#eceff4;color:#7b8498;text-align:center;border-radius:8px;"
                         f"padding:10px 4px;font-size:12px'>n = {n}<br>pocos datos</td>")
                continue
            niv = nivel(t / base, n)
            bg, fg = FONDO_NIVEL[niv]
            borde = "border:2px solid #1b1b1b;" if niv == "Alta" else ""
            h.append(f"<td style='background:{bg};color:{fg};text-align:center;border-radius:8px;"
                     f"padding:8px 4px;{borde}'><b style='font-size:17px'>{t:.0%}</b><br>"
                     f"<span style='font-size:11px'>{t / base:.1f}× · n = {n:,}</span></td>")
        tr = float(filas["mean"].get(r, 0)) if n_r else 0
        h.append(f"<td style='background:#f1f3f8;text-align:center;border-radius:8px;font-weight:700'>"
                 f"{tr:.0%}</td></tr>" if n_r else "<td style='background:#f1f3f8'></td></tr>")
    h.append("<tr><td style='font-size:12px'><b>Todas</b></td>")
    for c in ORD_DELINQ:
        n_c = int(cols["size"].get(c, 0))
        h.append(f"<td style='background:#f1f3f8;text-align:center;border-radius:8px;font-weight:700;"
                 f"padding:8px 4px'>{(float(cols['mean'].get(c)) if n_c else 0):.0%}"
                 f"<br><span style='font-size:11px;font-weight:400'>n = {n_c:,}</span></td>")
    h.append(f"<td style='background:#f1f3f8;text-align:center;border-radius:8px;font-weight:700'>"
             f"{base:.0%}</td></tr></table>")
    st.markdown("".join(h), unsafe_allow_html=True)


def tabla_segmentos(df_s: pd.DataFrame, key: str, incluir_variable: bool = True, seleccion: str | None = None,
                    compacta: bool = False):
    """Tabla completa (sin scroll interno) de grupos con semáforo."""
    v = pd.DataFrame({
        "Alerta": df_s["Nivel"].map(ESTADO),
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
        "Alerta": st.column_config.TextColumn(width=100),
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
            st.multiselect("Monto solicitado", ORD_MONTO, key="f_monto")
            st.multiselect("Motivo del préstamo", ORD_MOTIVO, key="f_motivo")
            st.multiselect("Ocupación del cliente", ORD_JOB, key="f_job")
            vmin, vmax = limites_valor(df)
            st.slider("Valor de la propiedad", vmin, vmax, key="f_valor", step=5000)
            st.checkbox("Incluir valor sin dato", key="f_valor_nd")
            st.button("Restablecer", on_click=restablecer, args=(df,))


def lectura_filtros(df, d):
    if len(d) != len(df):
        st.info(f"Estás viendo {len(d):,} de {len(df):,} solicitudes ({len(d) / len(df):.0%}) por los filtros "
                f"activos. Se cambian en Filtros, arriba a la derecha.")


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

    seccion("Resumen de la cartera", "¿Cuántas solicitudes hay, cuántas incumplen y dónde está el riesgo?")
    leyenda()
    fila_tiles([
        ("Solicitudes analizadas", f"{len(d):,}", f"{len(d) / len(df):.0%} de la cartera completa", AZUL,
         "Tamaño de lo que estás viendo."),
        ("Tasa de incumplimiento", f"{base:.1%}",
         f"{en_palabras(base)} · cartera completa: {base_total:.1%}",
         COLOR_NIVEL[nivel(razon_tasa, len(d))], "Verde si no supera a la cartera completa en más de 15 %."),
        ("Perfiles prioritarios", f"{len(prio)}", f"{n_prio:,} solicitudes ({peso:.0%} de lo analizado)",
         col_peso, f"Verde < {PESO_PRIORITARIOS[0]:.0%} · ámbar < {PESO_PRIORITARIOS[1]:.0%} · rojo más."),
        ("Sin dato de deuda/ingreso", f"{len(nd) / len(d):.0%}",
         (f"incumplen {nd['BAD'].mean():.0%} vs {base:.0%} de la cartera" if len(nd) >= MIN_N else "pocos datos"),
         COLOR_NIVEL[nivel(nd["BAD"].mean() / base if len(nd) else 0, len(nd))],
         "Solicitudes donde no se capturó este dato."),
    ])
    st.write("")
    n_bad = int(d["BAD"].sum())
    a, b, c, e, f = st.columns([3, 0.4, 3, 0.4, 3], vertical_alignment="center")
    a.markdown(f"<div class='paso'>Solicitudes<br><b>{len(d):,}</b></div>", unsafe_allow_html=True)
    b.markdown("<div style='text-align:center;font-size:24px;color:#8a93ad'>→</div>", unsafe_allow_html=True)
    c.markdown(f"<div class='paso'>Incumplen<br><b>{n_bad:,}</b></div>", unsafe_allow_html=True)
    e.markdown("<div style='text-align:center;font-size:24px;color:#8a93ad'>→</div>", unsafe_allow_html=True)
    f.markdown(f"<div class='paso'>Tasa<br><b>{base:.1%}</b> · {en_palabras(base)}</div>", unsafe_allow_html=True)
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
        mapa_calor(d, base)
        st.caption(f"Cada casilla: tasa de incumplimiento, veces la cartera ({base:.1%}) y solicitudes (n). "
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
            "Alerta": t["Nivel"].map(ESTADO), "Perfil": t["Perfil"],
            "Solicitudes": t["Solicitudes"], "Tasa": t["Tasa"] * 100, "Veces la cartera": t["Razón"],
            "Casos de más": t["Casos en exceso"].round().astype(int)})
        ev = st.dataframe(
            v, hide_index=True, on_select="rerun", selection_mode="single-row", key="tabla_perfiles",
            height=min(36 * (len(v) + 1) + 8, 640),
            column_config={
                "Alerta": st.column_config.TextColumn(width=105),
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
            f"<span class='chip' style='background:{bg};color:{fg}'>{ESTADO[fila['Nivel']]}</span></div>"
            f"<div style='font-size:13px;color:#44506b'>{en_palabras(fila['Tasa'])} incumple · "
            f"{fila['Razón']:.1f}× la cartera · {int(fila['Solicitudes']):,} solicitudes</div>", unsafe_allow_html=True)
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


def pantalla_modelo():
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
         semaforo(auc, META_AUC), "Qué tan bien separa a quien paga de quien no (0.5 = azar, 1 = perfecto)."),
        ("Recall (detección)", "Pendiente" if rec is None else f"{rec:.1%}",
         ref(rec, META_RECALL, lambda x: f"{x:.0%}"), semaforo(rec, META_RECALL),
         "De los que sí incumplieron, qué porcentaje detectó el modelo."),
        ("Precisión", "Pendiente" if pre is None else f"{pre:.1%}",
         "sin meta definida" if pre is None else f"{pre:.0%} de las alertas son reales", GRIS,
         "De los que el modelo marcó como riesgosos, cuántos sí incumplieron."),
        ("Umbral", "Pendiente" if umb is None else f"{umb:.2f}", "referencia: 0.50 (SAS)", GRIS,
         "Probabilidad desde la cual el modelo marca a un cliente como riesgoso."),
    ])
    if m.get("nombre_modelo") or m.get("conjunto_evaluacion"):
        st.caption(f"Modelo: {m.get('nombre_modelo') or '—'} · Conjunto de evaluación: "
                   f"{m.get('conjunto_evaluacion') or '—'}")
    st.write("")
    st.markdown("**Matriz de confusión** — aciertos y errores del modelo")
    if hay_matriz:
        z = [[vn, fp], [fn, vp]]
        fig = go.Figure(go.Heatmap(z=z, x=["Modelo dice: paga", "Modelo dice: incumple"],
                                   y=["Realidad: paga", "Realidad: incumple"], text=z, texttemplate="%{text:,}",
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
            x=g["Solicitudes"], y=g["Tasa"], mode="markers+text", name=ESTADO[niv],
            marker={"size": 13, "color": COLOR_NIVEL[niv], "line": {"width": 1, "color": "#fff"}},
            text=g["Etiqueta"] if niv == "Alta" else None, textposition="top center",
            textfont={"size": 10}, cliponaxis=False,
            customdata=np.stack([g["Etiqueta"], g["Razón vs cartera"], g["Casos en exceso"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{x:,} solicitudes<br>Tasa %{y:.0%} "
                          "(%{customdata[1]:.1f}× la cartera)<br>Casos de más: %{customdata[2]:+.0f}<extra></extra>"))
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
        cliponaxis=False))
    fig.add_vline(x=base, line_dash="dash", line_color="#333",
                  annotation_text=f"Cartera {base:.1%}", annotation_position="top")
    fig.update_yaxes(type="category", automargin=True)
    fig.update_xaxes(tickformat=".0%", range=[0, tope])
    fig.update_layout(title=titulo, height=300, bargap=0.35, margin={"t": 50, "b": 10, "l": 10, "r": 40})
    return fig


def pantalla_gerente(d: pd.DataFrame, df: pd.DataFrame):
    base, base_total = d["BAD"].mean(), df["BAD"].mean()
    s = segmentos(d)
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
    izq, der = st.columns([0.85, 1.15], gap="large")
    with izq:
        st.markdown("**Cada punto es un grupo de clientes**")
        st.caption("Más arriba = incumple más. Más a la derecha = más solicitudes. La franja roja es donde se "
                   "requiere atención.")
        st.plotly_chart(grafica_burbujas(s, base), config={"displayModeBar": False})
    with der:
        st.markdown("**Grupos que requieren atención**")
        st.caption("Ordenados por casos de más sobre lo esperado.")
        a = s[s["Nivel"].isin(["Alta", "Media"])].sort_values("Casos en exceso", ascending=False)
        if a.empty:
            st.info("Con estos filtros ningún grupo llega a alerta.")
        else:
            tabla_segmentos(a, "gerente_tabla", incluir_variable=False, compacta=True)
        st.download_button("Descargar tabla (CSV)", a.drop(columns=["Dimensión"]).to_csv(index=False).encode("utf-8"),
                           "grupos_con_atencion.csv", "text/csv", disabled=a.empty)
    fuente(d)
    with st.expander("Ver el comparativo por tipo de grupo (barras)"):
        tope = max(0.7, float(ev["Tasa"].max()) * 1.2)
        dims = list(DIMS)
        for fila in (dims[:3], dims[3:]):
            for col, dim in zip(st.columns(3), fila):
                col.plotly_chart(grafica_grupo(d, dim, base, tope), config={"displayModeBar": False})
        st.caption(f"Barra roja/ámbar/verde según el semáforo. Texto: tasa · solicitudes. Misma escala en todas.")


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
        "Alerta": sel["Nivel"].map(ESTADO), "Grupo": sel["Etiqueta"], "Variable": sel["Variable"],
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
def login():
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        if LOGO.exists():
            st.image(str(LOGO), width=130)
        st.markdown("<span style='font-size:26px;font-weight:700;color:#0B1A8C'>Banco Siete</span><br>"
                    "Plataforma de Créditos Hipotecarios", unsafe_allow_html=True)
        st.header("¡Bienvenid@!")
        with st.form("login"):
            u = st.text_input("Usuario", placeholder="(Ingresa tu usuario)")
            p = st.text_input("Contraseña", type="password", placeholder="(Ingresa tu contraseña)")
            if st.form_submit_button("Iniciar sesión"):
                if u in USUARIOS and p == USUARIOS[u][0]:
                    st.session_state["user"] = u
                    st.rerun()
                st.error("Usuario o contraseña incorrectos.")
        with st.expander("Usuarios de demostración"):
            st.write("`analista`, `gerente` o `supervisor`, con la contraseña `demo123`. "
                     "Es una simulación de acceso por rol: no ofrece seguridad real.")


def glosario():
    with st.sidebar.expander("¿Qué significa cada término?"):
        for nombre, tecnico, texto in TERMINOS:
            sufijo = f" *({tecnico})*" if tecnico != "—" else ""
            st.markdown(f"**{nombre}**{sufijo}  \n{texto}")


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    if "user" not in st.session_state:
        login()
        return
    rol = USUARIOS[st.session_state["user"]][1]
    df = cargar()
    st.sidebar.markdown(f"**Sesión:** {st.session_state['user']}  \n**Rol:** {rol}")
    paginas = PANTALLAS[rol]
    pagina = st.sidebar.radio("Pantalla", paginas) if len(paginas) > 1 else paginas[0]
    glosario()
    if st.sidebar.button("Cerrar sesión"):
        for k in list(st.session_state):
            del st.session_state[k]
        st.rerun()
    con_filtros = pagina != "Desempeño del modelo"
    encabezado(df, con_filtros)
    if not con_filtros:
        pantalla_modelo()
        return
    d = aplicar_filtros(df)
    if d.empty:
        st.warning("Con estos filtros no hay solicitudes. Abre Filtros y pulsa Restablecer.")
        return
    lectura_filtros(df, d)
    {"Resumen": pag_resumen, "Mapa de riesgo": pag_mapa, "Perfiles a revisar": pag_perfiles,
     "Comparativo de cartera": pantalla_gerente, "Seguimiento de cartera": pantalla_supervisor}[pagina](d, df)


main()
