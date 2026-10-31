"""Redibujo en vector del logo actual (frontend/public/logo.png, 220×360), fiel al original.

Traza la silueta (canal alfa) y la hoja (los píxeles verde vivo) con marching squares a nivel de subpíxel, simplifica
(Ramer-Douglas-Peucker), endereza los bordes rectos (velas, mechas, asta y ranura) a sus líneas guía corregidas
(mismo ancho y misma separación en las tres velas) y suaviza las curvas (Catmull-Rom → Bézier). Escribe las rutas en
JSON para que generar.mjs componga el SVG con los degradados de la marca.

Uso: python -I marca-renovacion/trazar.py
"""
import json
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "frontend", "public", "logo.png")

# Líneas guía (x e y) a las que se enderezan los bordes casi rectos: (valor medido → valor corregido).
# Velas: cuerpos de 54, 52 y 51 → 53 de ancho, con 8 de separación; mechas de 7, centradas en su cuerpo.
SNAP_X = {1: 1, 55: 54, 63: 62, 115: 115, 125: 123, 176: 176, 25: 24.5, 32: 31.5, 85: 85, 93: 92, 147: 146, 154: 153,
          102: 102, 133: 133, 95: 95}
SNAP_Y = {46: 46, 83: 83, 112: 112, 150: 150, 177: 177, 0: 0, 1: 1}
SNAP_TOL = 1.6          # px: un borde casi recto a esta distancia de una guía se lleva a ella
AXIS_DEG = 4            # un tramo a menos de esto de la vertical u horizontal se considera recto
RDP_EPS = 0.45          # px
CORNER_DEG = 38         # giro a partir del cual un vértice es esquina (no se suaviza)


def marching(field, level=0.5):
    """Contornos cerrados de `field` al nivel dado (subpíxel, interpolación lineal)."""
    f = np.pad(field, 1)
    h, w = f.shape
    segs = {}

    def interp(p, q, a, b):
        t = (level - a) / (b - a) if b != a else 0.5
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))

    edges = []
    for y in range(h - 1):
        for x in range(w - 1):
            a, b, c, d = f[y, x], f[y, x + 1], f[y + 1, x + 1], f[y + 1, x]
            idx = (a > level) * 1 | (b > level) * 2 | (c > level) * 4 | (d > level) * 8
            if idx in (0, 15):
                continue
            P = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
            V = [a, b, c, d]
            pts = {}
            for e, (i, j) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0))):
                if (V[i] > level) != (V[j] > level):
                    pts[e] = interp(P[i], P[j], V[i], V[j])
            ks = sorted(pts)
            if len(ks) == 2:
                pairs = [(ks[0], ks[1])]
            else:                                   # silla: se decide con el centro
                center = (a + b + c + d) / 4 > level
                if idx == 5:                        # a y c dentro
                    pairs = [(0, 1), (2, 3)] if center else [(3, 0), (1, 2)]
                else:                               # b y d dentro
                    pairs = [(3, 0), (1, 2)] if center else [(0, 1), (2, 3)]
            for e1, e2 in pairs:
                p1, p2 = pts[e1], pts[e2]
                edges.append((p1, p2))
    # enlazar
    def key(p):
        return (round(p[0], 4), round(p[1], 4))
    adj = {}
    for p1, p2 in edges:
        adj.setdefault(key(p1), []).append(key(p2))
        adj.setdefault(key(p2), []).append(key(p1))
    seen = set()
    loops = []
    for start in list(adj):
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        if len(loop) > 8:
            loops.append([(x - 1, y - 1) for x, y in loop])   # quitar el relleno
    return loops


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a
    n = np.hypot(*ab) or 1e-9
    d = [abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / n for p in pts[1:-1]]
    i = int(np.argmax(d)) + 1
    if d[i - 1] > eps:
        return rdp(pts[: i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]


def rdp_closed(loop, eps):
    # partir por los dos puntos más alejados para que el cierre no dependa del arranque
    arr = np.array(loop)
    i = 0
    j = int(np.argmax(np.hypot(*(arr - arr[0]).T)))
    a = rdp(loop[i: j + 1], eps)
    b = rdp(loop[j:] + loop[: 1], eps)
    return a[:-1] + b[:-1]


def snap(poly):
    """Endereza tramos casi verticales u horizontales y los lleva a su guía (x o y corregida)."""
    out = [list(p) for p in poly]
    n = len(out)
    for i in range(n):
        p, q = out[i], out[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        ang = math.degrees(math.atan2(abs(dy), abs(dx)))
        L = math.hypot(dx, dy)
        if L < 2.5:
            continue
        if ang > 90 - AXIS_DEG:                     # vertical
            x = (p[0] + q[0]) / 2
            for g, t in SNAP_X.items():
                if abs(x - g) <= SNAP_TOL:
                    x = t
                    break
            p[0] = q[0] = x
        elif ang < AXIS_DEG:                        # horizontal
            y = (p[1] + q[1]) / 2
            for g, t in SNAP_Y.items():
                if abs(y - g) <= SNAP_TOL:
                    y = t
                    break
            p[1] = q[1] = y
    return [tuple(p) for p in out]


def to_path(poly):
    """Esquinas donde el giro es fuerte o el tramo es recto; curvas suaves (Catmull-Rom) en lo demás."""
    n = len(poly)
    P = [np.array(p, float) for p in poly]

    def turn(i):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        v1, v2 = b - a, c - b
        n1, n2 = np.hypot(*v1), np.hypot(*v2)
        if n1 == 0 or n2 == 0:
            return 180
        cos = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
        return math.degrees(math.acos(cos))

    def straight(i, j):
        d = P[j] - P[i]
        ang = math.degrees(math.atan2(abs(d[1]), abs(d[0])))
        return ang < 0.5 or ang > 89.5
    corner = [turn(i) > CORNER_DEG for i in range(n)]
    f = lambda v: f"{v[0]:.2f} {v[1]:.2f}"
    d = f"M{f(P[0])}"
    for i in range(n):
        j = (i + 1) % n
        if straight(i, j) or (corner[i] and corner[j]):
            d += f"L{f(P[j])}"
            continue
        p0 = P[i - 1] if not corner[i] else P[i] - (P[j] - P[i])
        p3 = P[(j + 1) % n] if not corner[j] else P[j] + (P[j] - P[i])
        c1 = P[i] + (P[j] - p0) / 6
        c2 = P[j] - (p3 - P[i]) / 6
        d += f"C{f(c1)} {f(c2)} {f(P[j])}"
    return d + "Z"


def area(poly):
    return 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))


def main():
    im = np.asarray(Image.open(SRC).convert("RGBA")).astype(float)
    alpha = im[:, :, 3] / 255
    r, g = im[:, :, 0], im[:, :, 1]
    yy, xx = np.mgrid[0: im.shape[0], 0: im.shape[1]]

    out = {}
    loops = marching(alpha)
    polys = [snap(rdp_closed(l, RDP_EPS)) for l in loops]
    polys = [p for p in polys if abs(area(p)) > 4]
    out["silueta"] = [to_path(p) for p in polys]
    print("silueta", len(polys), "contornos", [len(p) for p in polys])

    # La hoja: verde vivo o pálido, nunca el blanco de la ranura (R alto); máscara suavizada 3×3 y su contorno. Se parte
    # en la punta y en el arranque de la vena: cuerpo (vivo) y lámina (pálida), con la vena (el hueco) entre ambos.
    m = ((g > 150) & (r < 215) & (alpha > 0.5)).astype(float)
    m[(yy < 228) | (xx > 100) | (yy > 310)] = 0
    k = np.pad(m, 1)
    m = sum(k[1 + dy: k.shape[0] - 1 + dy, 1 + dx: k.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
    loop = max(marching(m), key=lambda l: len(l))
    n = len(loop)
    sm = [tuple(np.mean([loop[(i + d) % n] for d in range(-2, 3)], axis=0)) for i in range(n)]   # suavizado (media de 5)
    poly = rdp_closed(sm, 0.35)
    tip = min(range(len(poly)), key=lambda i: poly[i][0] + 0.2 * poly[i][1])
    vein = min(range(len(poly)), key=lambda i: math.hypot(poly[i][0] - 38.5, poly[i][1] - 244))
    rot = poly[tip:] + poly[:tip]
    v = (vein - tip) % len(poly)
    a, b = rot[: v + 1], rot[v:] + rot[:1]
    # la parte que pasa por el borde derecho (x máx) es la lámina
    lam, body = (a, b) if max(p[0] for p in a) > max(p[0] for p in b) else (b, a)
    out["hoja_lamina"] = to_path(lam)
    out["hoja_cuerpo"] = to_path(body)
    print("hoja", len(poly), "puntos; punta", poly[tip], "vena", poly[vein])
    with open(os.path.join(HERE, "trazado.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
