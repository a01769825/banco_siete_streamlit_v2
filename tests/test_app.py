"""Pruebas de la app con secretos de PRUEBA (contraseñas inventadas, solo en memoria)."""
import hashlib, os, sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
os.chdir(RAIZ)


def h(clave):
    sal = b"0123456789abcdef"
    return sal.hex() + "$" + hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, 600_000).hex()


def app(con_secretos=True):
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60)
    if con_secretos:
        at.secrets["usuarios"] = {
            "a": {"password_hash": h("pw-a-test"), "rol": "Analista"},
            "g": {"password_hash": h("pw-g-test"), "rol": "Gerente"},
            "s": {"password_hash": h("pw-s-test"), "rol": "Supervisor"},
        }
    return at.run()


def entrar(at, u, p):
    at.text_input[0].set_value(u)
    at.text_input[1].set_value(p)
    at.button[0].click()
    return at.run()


def menu(at):
    return list(at.sidebar.radio[0].options) if at.sidebar.radio else None


def test_sin_secretos_se_detiene():
    at = app(False)
    assert any("Faltan las cuentas" in e.value for e in at.error)
    assert not at.sidebar.radio


def test_login_mal():
    at = entrar(app(), "a", "mala")
    assert any("incorrectos" in e.value for e in at.error)
    assert "user" not in at.session_state


def test_bloqueo_por_intentos():
    at = app()
    for _ in range(5):
        at = entrar(at, "a", "mala")
    assert any("Demasiados intentos" in e.value for e in at.error)
    at = entrar(at, "a", "pw-a-test")  # ni con la clave correcta: el botón está bloqueado en esta sesión
    assert at.button[0].disabled and "user" not in at.session_state


def test_roles_ven_menus_distintos():
    m = {}
    for u, p in [("a", "pw-a-test"), ("g", "pw-g-test"), ("s", "pw-s-test")]:
        at = entrar(app(), u, p)
        assert not at.exception, at.exception
        m[u] = menu(at) or ["(única)"]
    assert "Nueva solicitud" in m["a"] and "Mapa de riesgo" in m["a"]
    assert m["a"] != m["g"] and m["g"] != m["s"] and m["a"] != m["s"]
    assert "Nueva solicitud" not in m["g"] + m["s"]


def test_analista_cada_pantalla_sin_error_y_con_preguntas():
    at = entrar(app(), "a", "pw-a-test")
    for p in list(at.sidebar.radio[0].options):
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, (p, at.exception)


def test_no_hay_contrasenas_en_el_repo():
    for f in RAIZ.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".md", ".toml", ".yml", ".example", ".txt"} and "tests" not in f.parts:
            t = f.read_text(encoding="utf-8", errors="ignore")
            assert "demo123" not in t, f


def test_estado_vacio_se_declara_y_se_detiene():
    at = entrar(app(), "a", "pw-a-test")
    next(m for m in at.multiselect if m.key == "f_job").set_value([])
    at.run()
    assert any("no hay solicitudes" in w.value for w in at.warning)
    assert not at.exception
