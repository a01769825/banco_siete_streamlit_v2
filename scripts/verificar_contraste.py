"""Verifica la paleta del tablero: contraste WCAG 2.2 AA y distinguibilidad con daltonismo.

Uso:  python scripts/verificar_contraste.py
Sale con código 1 (y el CI falla) si algún par no cumple. No evalúa nada "a ojo": todo se calcula.

Contraste (WCAG 2.2, criterios 1.4.3 y 1.4.11): razón = (L1 + 0.05) / (L2 + 0.05), con L la luminancia relativa.
  - texto normal: 4.5:1 · texto grande y elementos no textuales: 3:1.
Daltonismo: se simulan protanopía, deuteranopía y tritanopía (matrices de Machado et al., 2009) y se exige una
distancia de color CIE76 ΔE mínima entre cada par de niveles del semáforo. Además cada nivel lleva un símbolo
propio (▲ ◆ ● ○), así que la identidad nunca depende solo del color.
"""
import itertools
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import paleta  # noqa: E402

UMBRAL = {"texto": 4.5, "grande": 3.0, "grafico": 3.0}


def a_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def lineal(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(h):
    r, g, b = (lineal(x) for x in a_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razon(a, b):
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


MATRICES = {
    "protanopía": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deuteranopía": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritanopía": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def simular(h, tipo):
    lin = [lineal(x) for x in a_rgb(h)]
    if tipo is None:
        return lin
    m = MATRICES[tipo]
    return [min(1.0, max(0.0, sum(m[i][j] * lin[j] for j in range(3)))) for i in range(3)]


def a_lab(rgb_lineal):
    r, g, b = rgb_lineal
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a, b, tipo):
    return math.dist(a_lab(simular(a, tipo)), a_lab(simular(b, tipo)))


def main():
    fallas, filas = [], []
    for nombre, fg, bg, tipo in paleta.PARES:
        r, minimo = razon(fg, bg), UMBRAL[tipo]
        ok = r >= minimo
        filas.append((nombre, fg, bg, tipo, r, minimo, ok))
        if not ok:
            fallas.append(f"{nombre}: {r:.2f}:1, se necesita {minimo}:1 ({fg} sobre {bg})")

    niveles = {k: paleta.COLOR_NIVEL[k] for k in ("Alta", "Media", "Sin alerta", "Muestra baja")}
    dalt = []
    for tipo in (None, *MATRICES):
        for (n1, c1), (n2, c2) in itertools.combinations(niveles.items(), 2):
            d = delta_e(c1, c2, tipo)
            ok = d >= paleta.DELTA_E_MIN
            dalt.append((tipo or "visión normal", n1, n2, d, ok))
            if not ok:
                fallas.append(f"Daltonismo ({tipo or 'normal'}): {n1} y {n2} se parecen (ΔE {d:.1f}, mínimo "
                              f"{paleta.DELTA_E_MIN})")

    out = ["## Verificación de contraste (WCAG 2.2 AA)", "",
           "| Par | Primer plano | Fondo | Tipo | Razón | Mínimo | Resultado |", "|---|---|---|---|---|---|---|"]
    out += [f"| {n} | `{fg}` | `{bg}` | {t} | {r:.2f}:1 | {m}:1 | {'✅' if ok else '❌'} |"
            for n, fg, bg, t, r, m, ok in filas]
    out += ["", "## Distinguibilidad con daltonismo (ΔE mínimo "
            f"{paleta.DELTA_E_MIN:g} entre niveles del semáforo)", "",
            "| Visión | Nivel A | Nivel B | ΔE | Resultado |", "|---|---|---|---|---|"]
    out += [f"| {t} | {a} | {b} | {d:.1f} | {'✅' if ok else '❌'} |" for t, a, b, d, ok in dalt]
    texto = "\n".join(out)
    print(texto)
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as f:
            f.write(texto + "\n")

    if fallas:
        print("\nFALLA la verificación:", *fallas, sep="\n - ")
        sys.exit(1)
    print(f"\nOK: {len(filas)} pares de contraste y {len(dalt)} comparaciones de daltonismo cumplen.")


if __name__ == "__main__":
    main()
