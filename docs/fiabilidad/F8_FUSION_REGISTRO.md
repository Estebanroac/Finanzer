# F8 · Fusión de `fiabilidad/f8-auditoria` en `rediseno/v4-f8`

## Qué se fusiona

- **f8-auditoria** (68785e29): E1, E4+E5, E2, E8, E9, E11 y el peso de Altman.
- **v4-f8** (5ef69671): la v4 más f8-independientes, con E3, E6, E10 por SIC y la cautiva, la historia de 10 años y
  el BPA de ciclo medio.

**Conflictos.** Hubo 5 en código, resueltos conservando las dos partes:

- `main.py` y `archetype_metrics.compute`: se quedan los dos parámetros nuevos, `reit_ffo` (E3) y `ke` (E1).
- `test_pdf_v2_parts`: lee la calidad del golden en lugar de fijar una cifra.
- `v7.spec.ts` y `CompanyHeader.test.tsx`: la estructura de la v4b (`#desglose`, `ScoreBreakdowns`) con los casos
  de E8. AAPL tiene ya una bandera roja, así que P2 usa JPM; el DCF inverso se prueba en DOW.

Los golden y los fixtures se regeneraron.

**Cruces.** Los golden que no son la suma de las dos ramas tienen su causa en `GOLDEN_DIFF_F8_FUSION.md`: 27 campos en
10 golden y ninguno sin causa.

**Comprobaciones en vivo:**

- **E6 frente a E11 (AMZN):** AMZN tiene los estados desfasados (corte del 31 de marzo de 2026; la SEC ya tiene el 10-Q
  al 30 de junio). Su cobertura es «media» y la confianza baja de **alta** (informe original) a **media**: la confianza
  no supera a la cobertura.
- **KMI y BA** también tienen los estados desfasados. KMI pasa de confianza alta a media.

## Las 26 empresas de la auditoría: informe original frente al motor corregido

**Original:** la corrida «antes», con el código de a0e824f, el que evaluó la auditoría, y los precios del 26-oct.
Coincide con las cifras que cita la auditoría: XOM 82 «excelente» con confianza baja, GOOGL 100 y MRNA con confianza
media.

**Corregido:** la corrida «fusion», con el código fusionado y los precios del 27-oct. El precio de mercado ha cambiado
un día, así que una diferencia de 1 a 3 puntos de precio puede ser solo del mercado.

Tabla: `tools/f8_tabla_auditoria.py antes fusion`. Estado: §4 de la auditoría.

| Empresa | Estado en la auditoría | Calidad (original → corregido) | Precio (original → corregido) | Confianza (original → corregido) |
|---|---|---|---|---|
| VZ | no utilizable | 65 sólida → **59 media** | 80 atractivo → **50 razonable** | alta → **media** |
| AWK | no utilizable | 76 sólida → **65 sólida** | 42 exigente → **35 exigente** | media |
| NEE | no utilizable | 66 sólida → **49 media** | 46 razonable → **35 exigente** | media |
| PLD | no utilizable | 79 sólida → **75 sólida** | 50 razonable → **40 exigente** | alta |
| UNH | no utilizable | 52 media → **62 media** | 61 razonable | media |
| XOM | no utilizable | 82 excelente → **72 sólida** | 48 razonable → **45 razonable** | baja |
| CB | no utilizable | 89 excelente → **81 sólida** | 61 razonable → **55 razonable** | media → **baja** |
| MSFT | utilizable con múltiplos y DCF inverso | 95 excelente | 39 exigente | media |
| GOOGL | utilizable con múltiplos y DCF inverso | 100 excelente | 39 exigente | media |
| AMZN | utilizable con múltiplos y DCF inverso | 60 media | 35 exigente → **39 exigente** | alta → **media** |
| LIN | utilizable con múltiplos y DCF inverso | 81 excelente → **78 sólida** | 10 muy exigente | alta |
| UNP | utilizable con múltiplos y DCF inverso | 75 sólida → **71 sólida** | 25 muy exigente → **15 muy exigente** | alta |
| WMT | utilizable con múltiplos y DCF inverso | 81 excelente → **86 excelente** | 10 muy exigente → **15 muy exigente** | alta |
| CAT | utilizable con múltiplos y DCF inverso | 84 excelente → **71 sólida** | 31 exigente → **30 exigente** | media → **baja** |
| FCX | utilizable con múltiplos y DCF inverso | 72 sólida → **65 sólida** | 35 exigente → **42 exigente** | media → **baja** |
| ASML | utilizable con múltiplos y DCF inverso | 90 excelente → **81 sólida** | 20 muy exigente → **35 exigente** | media → **baja** |
| KMI | utilizable con múltiplos y DCF inverso | 54 media → **48 media** | 30 exigente → **35 exigente** | alta → **media** |
| O | utilizable con múltiplos y DCF inverso | 59 media → **63 media** | 61 razonable → **58 razonable** | media → **baja** |
| NVDA | razonablemente sólido | 93 excelente | 61 razonable → **58 razonable** | media |
| LLY | razonablemente sólido | 89 excelente → **86 excelente** | 35 exigente → **39 exigente** | alta → **media** |
| JPM | razonablemente sólido | 91 excelente → **89 excelente** | 45 razonable → **46 razonable** | alta → **media** |
| MCD | razonablemente sólido | 81 excelente → **76 sólida** | 39 exigente → **48 razonable** | media → **baja** |
| KO | razonablemente sólido | 81 excelente → **79 sólida** | 25 muy exigente → **30 exigente** | alta |
| SAP | razonablemente sólido | 96 excelente → **92 excelente** | 30 exigente → **31 exigente** | alta → **media** |
| MRNA | sin precio, correctamente | 33 débil → **31 débil** | sin dato | media → **baja** |
| BA | sin precio, correctamente | 19 débil → **29 débil** | sin dato | baja |

### Qué explica los cambios (por grupo de la auditoría)

- **Los 7 «no utilizables»:**
  - **VZ:** el titular ya no es el retorno total y el FCF descuenta la media de 10 años del espectro (E4). El precio
    deja de ser «atractivo» y pasa a 50, razonable. La rentabilidad la topa ROIC − WACC (+1,7 pp, E9).
  - **AWK:** piso de Ke (Rf + 0,5 × ERP, 7,4 %; E1). Antes tenía un Ke de 5,1 %, por debajo de su Kd. Su veredicto
    depende de Ke y la rentabilidad la topa un ROIC − WACC de −0,9 pp.
  - **NEE:** bandera de pico de beneficio (E2) y piso de Ke (Kd + 1 pp, 9,0 %). El precio pasa a «exigente». La
    rentabilidad la topa un ROIC − WACC de −3,8 pp: la calidad baja a media.
  - **PLD:** FFO según Nareit (E3): resta las ganancias por venta de inmuebles, así que el FFO baja de 6,94 a 6,03 mil
    millones y el P/FFO sube de 17,7x a 20,4x. El precio pasa de 50, razonable, a 40, exigente.
  - **UNH:** el DCF directo tiene fiabilidad baja por el margen en caída (E8, criterio 5) y sus márgenes se comparan
    en puntos (E9). Calidad media.
  - **XOM:** piso de Ke (Rf + 0,5 × ERP); la confianza baja contrae la calidad (E11): de excelente 82 a sólida 72.
  - **CB:** piso de Ke y su veredicto depende de Ke, así que la confianza pasa a baja. La calidad se contrae de 87 a 81
    (sólida).
- **Los 11 «utilizables con múltiplos y DCF inverso»:**
  - **AMZN:** estados desfasados (E6) y confianza media.
  - **KMI:** Altman no aplica (midstream, E10), así que ya no dice «zona de peligro». Además tiene los estados
    desfasados (E6): la cobertura es media y la confianza baja de alta a media.
  - **CAT, FCX y ASML:** son cíclicas con estabilidad baja; por la regla de la más baja (E11), la confianza pasa a baja
    y se contraen la calidad y el precio.
  - **O:** FFO según Nareit (E3). La convergencia es media y su veredicto depende de Ke (E1), así que la confianza
    pasa a baja y se contraen la calidad y el precio.
  - **LIN, UNP y WMT:** cambian poco. WMT y MCD tienen Altman referencial.
- **Los 6 «razonablemente sólidos»:**
  - **NVDA:** sin cambios.
  - **LLY, JPM y SAP:** pierden un escalón de confianza. En LLY, porque una lectura extrema del forward P/E contradice
    la convergencia (E4); en JPM y SAP, porque su veredicto depende de Ke (E1).
  - **KO:** pasa a «sólida» 79 por el umbral de 85 y Altman +3.
  - **MCD:** la convergencia es baja (múltiplos y DCF en direcciones opuestas) y la regla de la más baja (E11) lleva
    la confianza a baja.
- **Sin precio:** MRNA y BA siguen sin precio. MRNA pasa a confianza baja (cobertura baja, E11); BA ya la tenía.

**«Excelente»:** en las 26 pasa de 14 a 7 (MSFT, GOOGL, WMT, NVDA, LLY, JPM y SAP; GOOGL sigue en 100).
