# Banco Siete · Tablero de riesgo hipotecario (Entregable 3)

> Línea 1 del README del repositorio: URL del tablero desplegado (la pone el equipo).

## Qué cambió en el Entregable 3
- **Paleta verificada** (`paleta.py`): el contraste WCAG 2.2 AA y la distinción para daltonismo se comprueban en cada push con `scripts/verificar_contraste.py` (GitHub Actions, `.github/workflows/contraste.yml`).
- **El nivel nunca se distingue solo por color**: ▲ Prioritario, ◆ Vigilar, ● Normal, ○ Pocos datos.
- **Cada gráfica declara la pregunta que responde** (diccionario `PREGUNTA` en `app.py`).
- **Estado vacío**: si los filtros no dejan solicitudes, la app lo declara y se detiene con `st.stop()`.
- **Filtros con conteo siempre visible** («Estás viendo N de M solicitudes · Filtros activos…»).
- **Acceso por persona**: cuentas en `st.secrets` con contraseña hasheada (PBKDF2-SHA256), matriz de acceso por rol aplicada en el servidor.

## Cuentas y secretos (nada de esto va al repositorio)
1. `python scripts/generar_hash.py` → copia la línea `password_hash = "..."`.
2. Local: crea `.streamlit/secrets.toml` (ya está en `.gitignore`) con el formato de `.streamlit/secrets.toml.example`.
3. Streamlit Cloud: App → Settings → Secrets → pega el mismo contenido.

## Ejecutar y probar
```
pip install -r requirements.txt
streamlit run app.py
python scripts/verificar_contraste.py
pip install pytest && python -m pytest -q tests
```
Documentación del entregable: `docs/entregable-3.md`. Prompts: `prompts/B3.md`.
