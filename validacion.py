"""Revisión del archivo del tablero contra contrato-datos.md.

La usan la app (app.py) y el pipeline (validar_datos.py), para que las dos revisen lo mismo.
El contrato es la tabla de la sección 1 de contrato-datos.md: si cambia una columna, se cambia ahí.
"""
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).parent
CONTRATO = AQUI / "contrato-datos.md"
DATA = AQUI / "hmeq_preparado_1_con_motivo.csv"

# Columnas cuyo faltante viene imputado y marcado con <columna>_FALTANTE (sección 3 del contrato).
CON_MARCA = ["VALUE", "DEBTINC", "DELINQ", "DEROG", "NINQ", "YOJ"]

TIPOS = {"entero": "debería ser entero", "decimal": "debería ser número",
         "bandera": "debería ser 0 o 1"}


def leer_contrato(ruta=CONTRATO) -> list[dict]:
    """Lee la tabla «1. Columnas del archivo» y devuelve una fila por columna."""
    filas, en_seccion = [], False
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            en_seccion = linea.startswith("## 1.")
            continue
        if en_seccion and linea.startswith("| `"):
            c = [x.strip() for x in linea.strip("|").split("|")]
            filas.append({"columna": c[0].strip("`"), "tipo": c[1],
                          "min": float(c[3]) if c[3] else None,
                          "max": float(c[4]) if c[4] else None})
    if not filas:
        raise ValueError("No se encontró la tabla de la sección 1 en contrato-datos.md")
    return filas


def validar(df: pd.DataFrame, contrato: list[dict] | None = None) -> list[str]:
    """Devuelve la lista de errores. Lista vacía = el archivo cumple el contrato."""
    contrato = contrato or leer_contrato()
    errores = []
    faltan = [f["columna"] for f in contrato if f["columna"] not in df.columns]
    if faltan:
        errores.append(f"Faltan columnas del contrato: {', '.join(faltan)}")
    sobran = [c for c in df.columns if c not in {f['columna'] for f in contrato}]
    if sobran:
        errores.append(f"Columnas que no están en el contrato: {', '.join(sobran)}")

    for f in contrato:
        col, tipo = f["columna"], f["tipo"]
        if col not in df.columns:
            continue
        s = df[col]
        if not pd.api.types.is_numeric_dtype(s):
            raros = s[pd.to_numeric(s, errors="coerce").isna() & s.notna()].astype(str).unique()[:3]
            errores.append(f"{col}: {TIPOS.get(tipo, 'debería ser número')} y se leyó como texto "
                           f"(por ejemplo: {', '.join(repr(x) for x in raros)})")
            continue
        vacios = int(s.isna().sum())
        if vacios:
            errores.append(f"{col}: {vacios} celdas vacías; en este archivo el faltante se marca con _FALTANTE")
        v = s.dropna()
        if tipo in ("entero", "bandera") and (v % 1 != 0).any():
            errores.append(f"{col}: {TIPOS[tipo]} y trae decimales")
        if tipo == "bandera" and not v.isin([0, 1]).all():
            errores.append(f"{col}: {TIPOS[tipo]} y trae otros valores")
        if f["min"] is not None and (v < f["min"]).any():
            errores.append(f"{col}: hay valores menores que {f['min']:g}")
        if f["max"] is not None and (v > f["max"]).any():
            errores.append(f"{col}: hay valores mayores que {f['max']:g}")

    jobs = [c for c in ["JOB_Office", "JOB_Other", "JOB_ProfExe", "JOB_Sales", "JOB_Self"] if c in df.columns]
    if jobs and all(pd.api.types.is_numeric_dtype(df[c]) for c in jobs) and (df[jobs].sum(axis=1) > 1).any():
        errores.append("JOB_*: hay solicitudes con más de una ocupación")
    return errores


def convertir_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """Cambia el valor imputado por vacío donde <columna>_FALTANTE = 1 (sección 3 del contrato)."""
    df = df.copy()
    for col in CON_MARCA:
        df[col] = df[col].where(df[f"{col}_FALTANTE"] == 0, np.nan)
    return df


def revisar_archivo(ruta=DATA) -> tuple[list[str], int]:
    """Lee el CSV tal cual viene y lo revisa. Devuelve (errores, columnas revisadas)."""
    contrato = leer_contrato()
    df = pd.read_csv(ruta)
    return validar(df, contrato), len(contrato)
