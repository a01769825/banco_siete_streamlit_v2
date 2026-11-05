# Banco Siete · Plataforma de Créditos Hipotecarios (Streamlit)

1. Instala Python 3.10 o más reciente.
2. En esta carpeta: `pip install -r requirements.txt`
3. Ejecuta: `streamlit run app.py` (se abre en http://localhost:8501)

Usuarios de demostración (contraseña `demo123`): `analista`, `gerente`, `supervisor`.
Es una simulación de acceso por rol, no seguridad real.

## Resultados del modelo de SAS
Escribe los números en `modelo_sas.json` (AUC, recall, precisión, umbral y matriz de confusión).
Mientras haya `null`, la pantalla "Desempeño del modelo" dice "Pendiente".

## Reglas (se cambian al inicio de `app.py`)
- Alerta alta: tasa del segmento ≥ 1.5 × tasa de la cartera; media: ≥ 1.15 ×.
- Segmentos con menos de 30 solicitudes no generan alerta.
- Datos faltantes: "Sin dato" (no se imputan). Fecha de actualización = fecha de hoy.


## Versión 2 (4 nov)
Nombres de variables en lenguaje claro (el nombre técnico queda en el glosario del menú lateral), frases «1 de cada N», semáforo con referencia en cada indicador, filtros en ⚙ Filtros, analista en 4 pantallas (Resumen, Mapa de riesgo, Perfiles a revisar, Desempeño del modelo), gerente simplificado, casos en tablas. Metas del modelo (AUC 0.85, recall 70 %) y umbrales del semáforo se cambian al inicio de app.py.
