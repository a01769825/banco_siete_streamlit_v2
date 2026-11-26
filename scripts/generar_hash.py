"""Genera el hash PBKDF2 de una contraseña para pegarlo en los secrets (nunca guardes la contraseña).
Uso:  python scripts/generar_hash.py        (pide la contraseña sin mostrarla)
"""
import getpass, hashlib, os

ITERACIONES = 600_000  # debe coincidir con ITERACIONES_HASH en app.py

clave = getpass.getpass("Contraseña: ")
sal = os.urandom(16)
h = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, ITERACIONES)
print(f'password_hash = "{sal.hex()}${h.hex()}"')
