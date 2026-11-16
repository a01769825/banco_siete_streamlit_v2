"""Revisión para el pipeline (GitHub Actions): misma función que usa la app.

Uso:  python validar_datos.py
Termina con código 1 (corrida en rojo) si el archivo no cumple contrato-datos.md.
"""
import sys

from validacion import DATA, revisar_archivo

errores, n = revisar_archivo()
if errores:
    print(f"✗ {DATA.name} NO cumple el contrato de datos:")
    for e in errores:
        print(f"  - {e}")
    sys.exit(1)
print(f"✓ {DATA.name}: {n} columnas cumplen el contrato de datos.")
