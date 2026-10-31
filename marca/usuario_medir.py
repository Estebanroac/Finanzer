"""El logo del usuario (logo-usuario-original.webp, 1671 × 941): medidas y ajuste de sus bordes, sin el fondo.

Del original se toma solo el logo (recorte x 650–1080, y 225–690); el fondo, las líneas y los puntos se descartan.
Bordes exteriores: el contorno subpíxel del logo frente al fondo (trazar.marching sobre la luminancia). Bordes
interiores (la cinta sobre las barras y sobre el asta, el pliegue): la cresta del gradiente de luminancia, con ajuste
parabólico a subpíxel. Cada borde curvo se ajusta con Bézier cúbicas por mínimos cuadrados; los rectos, con rectas.
Escribe usuario.json (coordenadas del original). Uso: python -I marca/usuario_medir.py <ruta del webp>
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trazar as T  # noqa: E402

X0, Y0, X1, Y1 = 650, 225, 1080, 690


def fit_cubic(pts, p0, p3, iters=6):
    pts = np.asarray(pts, float)
    p0, p3 = np.asarray(p0, float), np.asarray(p3, float)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    t = d / d[-1]
    for _ in range(iters):
        b0, b1, b2, b3 = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t ** 2 * (1 - t), t ** 3
        rhs = pts - np.outer(b0, p0) - np.outer(b3, p3)
        sol, *_ = np.linalg.lstsq(np.c_[b1, b2], rhs, rcond=None)
        P = [p0, sol[0], sol[1], p3]
        B = np.outer((1 - t) ** 3, P[0]) + np.outer(3 * t * (1 - t) ** 2, P[1]) + np.outer(3 * t ** 2 * (1 - t), P[2]) + np.outer(t ** 3, P[3])
        dB = np.outer(3 * (1 - t) ** 2, P[1] - P[0]) + np.outer(6 * (1 - t) * t, P[2] - P[1]) + np.outer(3 * t ** 2, P[3] - P[2])
        t = np.clip(t - ((B - pts) * dB).sum(1) / np.maximum((dB * dB).sum(1), 1e-9), 0, 1)
    B = np.outer((1 - t) ** 3, P[0]) + np.outer(3 * t * (1 - t) ** 2, P[1]) + np.outer(3 * t ** 2 * (1 - t), P[2]) + np.outer(t ** 3, P[3])
    return [list(map(float, q)) for q in P], float(np.max(np.hypot(*(B - pts).T)))


def line_fit(pts):
    """Recta por mínimos cuadrados (y = a x + b, o x = a y + b si es casi vertical)."""
    pts = np.asarray(pts, float)
    if np.ptp(pts[:, 0]) >= np.ptp(pts[:, 1]):
        a, b = np.polyfit(pts[:, 0], pts[:, 1], 1)
        return {"y_de_x": [float(a), float(b)]}
    a, b = np.polyfit(pts[:, 1], pts[:, 0], 1)
    return {"x_de_y": [float(a), float(b)]}


def ridge(E, fixed, rng, axis):
    """Cresta del gradiente en una fila (axis='x': recorre x en la fila y=fixed) o columna; subpíxel por parábola."""
    if axis == "x":
        prof = E[fixed - Y0, rng[0] - X0: rng[1] - X0]
    else:
        prof = E[rng[0] - Y0: rng[1] - Y0, fixed - X0]
    i = int(np.argmax(prof))
    if 0 < i < len(prof) - 1:
        a, b, c = prof[i - 1], prof[i], prof[i + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den != 0 else 0
    else:
        off = 0
    return rng[0] + i + off + 0.5, float(prof[i])


def main(src):
    im = np.asarray(Image.open(src).convert("RGB")).astype(float)
    c = im[Y0:Y1, X0:X1]
    L = 0.2126 * c[:, :, 0] + 0.7152 * c[:, :, 1] + 0.0722 * c[:, :, 2]
    # gradiente suavizado (3×3) para las crestas
    k = np.pad(L, 1, mode="edge")
    Ls = sum(k[1 + dy: k.shape[0] - 1 + dy, 1 + dx: k.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
    gx = np.zeros_like(Ls); gy = np.zeros_like(Ls)
    gx[:, 1:-1] = (Ls[:, 2:] - Ls[:, :-2]) / 2; gy[1:-1, :] = (Ls[2:, :] - Ls[:-2, :]) / 2
    E = np.hypot(gx, gy)
    sil = max(T.marching(np.clip((L - 16) / 14, 0, 1)), key=len)
    sil = np.array(sil) + [X0 + 0.5, Y0 + 0.5]
    near = lambda p: sil[int(np.argmin(np.hypot(*(sil - np.asarray(p)).T)))]
    def seg(a, b):
        """Tramo de la silueta entre dos puntos, por el arco más corto."""
        i, j = int(np.argmin(np.hypot(*(sil - np.asarray(a)).T))), int(np.argmin(np.hypot(*(sil - np.asarray(b)).T)))
        fwd = sil[i: j + 1] if i <= j else np.r_[sil[i:], sil[: j + 1]]
        bwd = (sil[j: i + 1] if j <= i else np.r_[sil[j:], sil[: i + 1]])[::-1]
        return fwd if len(fwd) <= len(bwd) else bwd
    out = {"silueta_puntos": len(sil)}
    # ── barras: lados (x) y techo inclinado (recta) ──
    bars = {}
    for name, (xl, xr, ytop) in {"b1": (676, 751, 345), "b2": (772, 848, 294), "b3": (870, 945, 242)}.items():
        left = [p for p in sil if abs(p[0] - xl) < 2.5 and ytop + 50 < p[1] < ytop + 70]
        right = [p for p in sil if abs(p[0] - xr) < 2.5 and ytop + 15 < p[1] < ytop + 60]
        top = [p for p in sil if xl + 12 < p[0] < xr - 12 and p[1] < ytop + 45 and abs(p[0] - xl) > 3]
        top = [p for p in top if p[1] < np.interp(p[0], [xl, xr], [ytop + 45, ytop + 5])]
        bars[name] = {"x0": float(np.mean([p[0] for p in left])), "x1": float(np.mean([p[0] for p in right])),
                      "techo": line_fit(top)["y_de_x"]}
    out["barras"] = bars
    # ── brazo inferior: borde superior e inferior (y) ──
    out["brazo"] = {"y0": float(np.mean([p[1] for p in sil if 785 < p[0] < 930 and abs(p[1] - 522.5) < 3])),
                    "y1": float(np.mean([p[1] for p in sil if 785 < p[0] < 870 and abs(p[1] - 587) < 3])),
                    "remate": fit_cubic(seg((943, 524), (878, 587)), near((943, 524)), near((878, 587)))}
    # ── asta: borde derecho (x) y diagonal del pie ──
    out["asta"] = {"x": float(np.mean([p[0] for p in sil if abs(p[0] - 771.5) < 2.5 and 600 < p[1] < 660])),
                   "pie": line_fit([p for p in sil if 692 < p[0] < 758 and 620 < p[1] < 671])["y_de_x"]}
    # ── cinta: borde interior (silueta) del codo a la muesca, y su tramo recto ──
    out["cinta_int_recto_y"] = float(np.mean([p[1] for p in sil if 805 < p[0] < 895 and abs(p[1] - 490) < 3]))
    out["cinta_int_subida"] = fit_cubic(seg((900, 490), (1031, 400)), near((900, 490)), near((1031, 400)))
    out["cinta_int_codo"] = fit_cubic(seg((772, 512), (800, 490)), near((772, 512)), near((800, 490)))
    # flecha
    out["flecha"] = {k: list(map(float, near(p))) for k, p in {"muesca": (1032, 399), "barba_baja": (1058, 418), "punta": (1058, 317),
                                                              "barba_izq": (973, 353), "barba_int": (995, 370)}.items()}
    # cinta: borde exterior a la derecha de la barra 3 (silueta)
    out["cinta_ext_derecha"] = fit_cubic(seg((995, 370), (946, 415)), near((995, 370)), near((946, 415)))
    # ── bordes interiores por cresta ──
    def peaks(prof, thr):
        """Máximos locales del perfil por encima de `thr`, con su posición a subpíxel."""
        out = []
        for i in range(1, len(prof) - 1):
            if prof[i] >= thr and prof[i] >= prof[i - 1] and prof[i] > prof[i + 1]:
                a, b, c = prof[i - 1], prof[i], prof[i + 1]
                den = a - 2 * b + c
                out.append((i + (0.5 * (a - c) / den if den else 0), prof[i]))
        return out
    THR = 6
    ext_left, inner_left = [], []
    for y in range(436, 600, 2):
        row = E[y - Y0, 679 - X0: 769 - X0]
        pk = [(679 + i + 0.5, v) for i, v in peaks(row, THR)]
        if pk:
            ext_left.append((pk[0][0], y + 0.5))                  # el más a la izquierda: borde exterior de la cinta
            if y >= 506 and len(pk) > 1:
                inner_left.append((pk[-1][0], y + 0.5))           # el último antes del asta: borde interior
    ext_top = [(x + 0.5, ridge(E, x, (405, 450), "y")[0]) for x in range(760, 946, 3)]          # cinta (techo) sobre barras 2 y 3
    fold = []
    for x in range(882, 966, 2):
        top = np.interp(x, [900, 946, 966], [426, 415, 404]) + 5
        bot = np.interp(x, [882, 900, 966], [489, 489, 450]) - 5
        col = E[int(top) - Y0: int(bot) - Y0, x - X0]
        pk = peaks(col, 2.5)
        if pk:
            i, v = max(pk, key=lambda t: t[1])
            fold.append((x + 0.5, int(top) + i + 0.5))
    out["crestas"] = {"ext_izq": ext_left, "ext_techo": ext_top, "int_izq": inner_left, "pliegue": fold}
    with open(os.path.join(HERE, "usuario.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "crestas"}, indent=1)[:2500])
    for k, v in out["crestas"].items():
        print(k, " ".join(f"({x:.1f},{y:.1f})" for x, y in v[::3]))


if __name__ == "__main__":
    main(sys.argv[1])


# ══════════════════ composición de las piezas (rutas SVG en coordenadas del original) ══════════════════
def f(p):
    return f"{p[0]:.2f} {p[1]:.2f}"


def cubic_d(P):
    return f"C{f(P[1])} {f(P[2])} {f(P[3])}"


def rev(P):
    return [P[3], P[2], P[1], P[0]]


def split_at_x(P, x, lo=0.0, hi=1.0):
    """Parte una cúbica en el t donde su x vale `x` (bisección); devuelve (primera mitad, segunda mitad)."""
    P = [np.asarray(p, float) for p in P]
    def at(t):
        return ((1 - t) ** 3) * P[0] + 3 * t * (1 - t) ** 2 * P[1] + 3 * t * t * (1 - t) * P[2] + t ** 3 * P[3]
    a, b = lo, hi
    inc = at(hi)[0] > at(lo)[0]
    for _ in range(60):
        m = (a + b) / 2
        if (at(m)[0] < x) == inc:
            a = m
        else:
            b = m
    t = (a + b) / 2
    p01, p12, p23 = P[0] + t * (P[1] - P[0]), P[1] + t * (P[2] - P[1]), P[2] + t * (P[3] - P[2])
    p012, p123 = p01 + t * (p12 - p01), p12 + t * (p23 - p12)
    q = p012 + t * (p123 - p012)
    return [P[0], p01, p012, q], [q, p123, p23, P[3]]


def compose(m):
    out, err = {}, {}
    FOOT = np.array([677.6, 603.6])                      # pie de la cinta (los dos bordes convergen ahí)
    # ── barras: techo inclinado medido, esquinas redondeadas (7 la de la izquierda, 5 la de la derecha) ──
    for k, b in m["barras"].items():
        a, c = b["techo"]; x0, x1 = b["x0"], b["x1"]
        u = np.array([1, a]) / math.hypot(1, a)
        TL, TR = np.array([x0, a * x0 + c]), np.array([x1, a * x1 + c])
        r1, r2 = 7.0, 5.0
        bottom = 606 if k == "b1" else 470            # la barra 1 acaba en el pie (debajo, la cara del asta)
        out[k] = (f"M{f((x0, bottom))}V{TL[1] + r1:.2f}Q{f(TL)} {f(TL + r1 * u)}L{f(TR - r2 * u)}"
                  f"Q{f(TR)} {f((x1, TR[1] + r2))}V{bottom}Z")
    # ── borde exterior de la cinta: del pie al techo (curva), techo (recta), subida a la barba interior (curva) ──
    cr = m["crestas"]
    left = sorted([p for p in cr["ext_izq"] if p[1] <= 551], key=lambda p: -p[1])
    top_l = [p for p in cr["ext_techo"] if p[0] <= 790]
    E1, e1 = fit_cubic([FOOT] + left + top_l, FOOT, (790.0, 426.4))
    top_r = [p for p in cr["ext_techo"] if p[0] >= 905]
    ext_r = m["cinta_ext_derecha"][0]
    E3, e3 = fit_cubic([(905.0, 425.9)] + top_r + [tuple(ext_r[3])], (905.0, 425.9), ext_r[3])
    err["ext"] = round(max(e1, e3), 2)
    # ── borde interior: de la muesca a la recta (curva), recta, codo, y sobre el asta hasta el pie ──
    sub = m["cinta_int_subida"][0]; codo = m["cinta_int_codo"][0]
    y_int = m["cinta_int_recto_y"]
    # el codo de la silueta va del asta (771, 512,5) a la recta; la cinta lo sigue hasta x 772 y baja por encima del asta
    c_hi, c_lo = split_at_x(rev(codo), 772.6)
    J = c_lo[0]
    inner_pts = sorted([tuple(p) for p in cr["int_izq"]] + [p for p in cr["ext_izq"] if p[1] >= 555], key=lambda p: p[1])
    I1, e4 = fit_cubic([tuple(J)] + inner_pts + [tuple(FOOT)], J, FOOT)
    err["int"] = round(e4, 2)
    fl = m["flecha"]
    out["cinta"] = (f"M{f(FOOT)}{cubic_d(E1)}L905.00 425.90{cubic_d(E3)}{cubic_d(rev(ext_r))}"
                    f"L{f(fl['barba_izq'])}L{f(fl['punta'])}L{f(fl['barba_baja'])}L{f(fl['muesca'])}"
                    f"{cubic_d(rev(sub))}L{f((sub[0][0], y_int))}L{f((codo[3][0], y_int))}{cubic_d(c_hi)}{cubic_d(I1)}Z")
    # ── pliegue: la cara de abajo de la cinta, entre la línea del pliegue y el techo ──
    fold = cr["pliegue"]
    lo_pt, hi_pt = np.array(fold[0]), np.array(fold[-1])
    a_, b_ = np.polyfit([p[0] for p in fold], [p[1] for p in fold], 1)      # casi recta: recta ajustada
    P0 = np.array([ (y_int - b_) / a_, y_int])                              # donde toca el borde interior
    # arriba, el pliegue toca el borde exterior (la subida, entre 946 y 994): ahí se corta esa curva
    up = rev(ext_r)
    xs_ = np.linspace(946.5, 994, 200)
    def edge_y(x):
        first, _ = split_at_x(up, x)
        return float(first[3][1])
    xm = min(xs_, key=lambda x: abs(edge_y(x) - (a_ * x + b_)))
    P1 = np.array([xm, edge_y(xm)])
    first, _ = split_at_x(up, xm)
    out["pliegue"] = (f"M{f(P0)}L{f(P1)}{cubic_d(rev(first))}{cubic_d(rev(E3))}L{f((880, y_int))}Z")
    out["pliegue_linea"] = [list(map(float, P0)), list(map(float, P1))]
    # ── cara del asta (bajo la cinta) y brazo inferior ──
    xs = m["asta"]["x"]; pa, pb = m["asta"]["pie"]
    out["asta"] = (f"M{f(J)}L{xs:.2f} 512.50V{pa * (xs - 3) + pb - 0.0:.2f}Q{xs:.2f} {pa * xs + pb:.2f} {f((xs - 5, pa * (xs - 5) + pb))}"
                   f"L{f((684, pa * 684 + pb))}Q675.90 {pa * 675.9 + pb - 4:.2f} 675.90 {pa * 675.9 + pb - 10:.2f}V{FOOT[1] + 2:.2f}L{f(FOOT)}{cubic_d(rev(I1))}Z")
    br = m["brazo"]; R = br["remate"][0]
    out["brazo"] = f"M{xs:.2f} {br['y0']:.2f}L{f(R[0])}{cubic_d(R)}L{xs:.2f} {br['y1']:.2f}Z"
    out["err"] = err
    return out


if __name__ == "__main__":
    with open(os.path.join(HERE, "usuario.json")) as fh:
        m = json.load(fh)
    m["piezas"] = compose(m)
    with open(os.path.join(HERE, "usuario.json"), "w") as fh:
        json.dump(m, fh, indent=1)
    print("piezas:", list(m["piezas"]), "error de ajuste (px):", m["piezas"]["err"])
