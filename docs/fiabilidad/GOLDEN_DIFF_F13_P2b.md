# F13 · Paso 2b: financieras cautivas con el 10-K de la filial (5-nov-2026)

Patrón 8 de la revisión de 110 empresas: Ford, GM y Deere sumaban la deuda de su financiera (que presta a clientes)
como deuda industrial, y GM contaba como capex los vehículos que GM Financial compra para arrendar (caja libre ≈ 0).
La separación existía solo para CAT (por el segmento de su 10-Q) y en la práctica no actuaba: la deuda de Cat Financial
era de otro corte que la de la matriz.

## Qué cambia

- **Fuente:** `config/data.toml [edgar.captive_filers]`, las filiales que presentan su propio 10-K/10-Q porque emiten
  deuda pública: Ford Credit (CIK 38009), GM Financial (804269) y Cat Financial (764764). Es un hecho de la fuente (qué
  filial presenta informes), no un criterio por empresa. La detección por nombre de segmento **no** activa la
  separación: da falsos positivos (CTSH, FISV; medido en el paso 0).
- `sec_edgar.captive_filer_debt`: su deuda total **y su caja** en cada fecha publicada (companyfacts de la filial).
- `debt.apply`: toma la fecha de esa serie más cercana al corte de la deuda de la matriz, y saca de la deuda y de la
  caja industriales (deuda neta, EV, apalancamiento, pesos del WACC, DCF) la deuda y la caja de la filial del mismo
  corte, con el mecanismo que ya existía (F3_DISENO §8.6). Antes, sacar la caja no se hacía ni en CAT.
- `edgar_primary`: el capex sin el equipo arrendado (el de EDGAR de la matriz) también para estas filiales: Ford
  8,8 B$ y GM 9,3 B$ en 2025.
- **Deere sigue «no separable», declarado:** John Deere Capital presenta 10-Q/10-K, pero sin un total de deuda estándar
  (solo piezas; `LongTermDebtNoncurrent` se dejó de etiquetar en 2022). Sumar pasivos sería inventar el dato.
- **Toyota (TM)** queda fuera: emisor extranjero (20-F en IFRS y JPY); Toyota Motor Credit presenta en USD y US GAAP.

## Efecto en las 110 congeladas (paso 2a → 2b)

| Empresa | Cautiva fuera (deuda / caja) | Deuda neta industrial | FCF | WACC | Veredicto |
|---|---|---|---|---|---|
| F | 139,4 / 8,25 B$ (30-sep) | −1,3 B$ (ND/EBITDA −0,18) | 5,1 B$ | 9,0 → 10,6 % | razonable → **atractivo** (baja) |
| GM ★ | 111,7 / 4,99 B$ (30-jun) | −3,8 B$ (−0,23) | 0,6 → **14,4 B$** | 7,6 → 10,9 % | calidad débil · exigente → **media · atractivo (media)** |
| CAT | 34,5 / 0,66 B$ (30-jun) | 4,6 B$ (0,30) | 10,7 B$ | 10,0 → 10,7 % | igual (exigente, nota 32 → 38) |

El WACC sube porque la deuda pesa menos frente al Ke: es lo correcto para la actividad industrial. GM era uno de los 11
«no se sostiene» de la revisión («6x beneficios esperados y sale exigente»): ahora sale atractiva, con confianza media.

Tabla: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso2b_vs_paso2a.md`. Los companyfacts de las
tres filiales se grabaron en el banco (`fixtures/f2b`) y, el de Cat Financial, en `tests/fixtures/f2b` (golden de CAT).

## Golden

Solo CAT (panel): ya separaba la deuda de su cautiva en octubre (las fechas casaban). Ahora también sale su caja: caja
6,71 → 6,05 B$, deuda neta 3,98 → 4,64 B$. Sin cambio de veredicto. Tests: `tests/test_f13_paso2b.py`.
