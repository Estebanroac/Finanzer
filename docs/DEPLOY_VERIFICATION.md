# Verificación del despliegue del rediseño (2026-10-13)

Merge `a6482f9` (redesign-motor → main, `--no-ff`) desplegado en Render el
2026-10-13. Punto de rollback: **c446df5** (Render → servicio → Events/Deploys →
"Rollback" al deploy de c446df5 y desactivar auto-deploy; o `git revert -m 1 a6482f9`
y push).

Este informe solo constata; nada de lo encontrado en el punto 4 se ha corregido.

## 1. Preparación

| Comprobación | Resultado |
|---|---|
| Suite backend (`.venv313`) | 569 passed, 1 skipped (en la rama y de nuevo en main tras el merge) |
| `tsc --noEmit` | ok |
| `npm run lint` | 0 errores, 3 avisos `<img>` preexistentes |
| `npm run build` | ok; reconstruir solo cambia el buildId aleatorio de Next (chunks idénticos): se sirve el `frontend/out` commiteado |
| `build.sh` (sin `pip install`) | assets referenciados presentes; sello de contrato = `src/lib/api.ts` (b26fe621c9b8…) |
| `requirements.txt`, `constraints.txt`, `.python-version` | sin cambios frente a main |
| Variables de entorno nuevas | ninguna (solo `FINNHUB_API_KEY`, ya existente) |
| Grep de secretos `main..redesign-motor` | sin tokens: `ghp_` solo aparece redactado (`ghp_…`), sin CAPTURE_TOKEN; las claves son el falso `"fixture-replay"` |
| Merge | 105 commits (103 sin merge), 243 archivos, +225 347 / −9 272; de ellos 96 archivos / +206 483 son fixtures y golden |

## 2. Despliegue

- Push `c446df5..a6482f9` a las 16:25:12 UTC; Render sirvió el sello nuevo a las 16:27:00 (≈2 min).
- `/api/health` → 200 `{"status":"ok"}`.
- `/` → 200, buildId `jlWixcvM1IyAx8-ll_avS` (= `frontend/out` commiteado).
- `/build-stamp.json` → `contract_sha256` b26fe621c9b8620c… = SHA-256 de `src/lib/api.ts`.

## 3. Verificación en producción: NFLX, JPM, O, FCX, SNOW, V

### Resultado global

- `/api/analysis`: 200 en los 6. `/api/pdf`: 200 en los 6; PDF válidos de 7–9 páginas.
  - En el texto del PDF los códigos de arquetipo y `<=` solo aparecen en «Clasificación (detalle técnico)».
- Test de contrato (`check-contract.mjs`) sobre los 6 JSON vivos: **encaja**.
  - Con `--strict-unions`, el único aviso es el caso `kind: "nc"` (categoría no concluyente).
  - Ningún ticker real lo produce; el pytest lo cubre con una muestra forzada, por diseño.
- Web (Chrome headless, escritorio 1440×900 y móvil 390×844, las 7 pestañas):
  - sin errores de JS ni desbordamiento horizontal;
  - veredicto visible sin scroll en los 12 casos.
  - Capturas en `~/Downloads/finanzer_deploy_verificacion/`.
- **Arquetipo idéntico al golden en los 6** (NFLX Madura, JPM Banco/aseguradora, O REIT,
  FCX Cíclica, SNOW Crecimiento sin beneficio, V Madura/red de pagos).

### Comprobaciones solo posibles en prod (RECON §7.12–§7.13)

| Punto | Resultado |
|---|---|
| TTM | **Llegan los estados trimestrales desde Render**: `data_provenance.ttm.basis = "ttm"` en los 6, balance al 2026-06-30 (SNOW 2026-07-31), 0 errores. En la muestra amplia solo BRK-B cae a anual (sus trimestres no traen `Total Revenue`, `Net Income`, … en alguno de los 4 últimos) y SPY (ETF, sin estados). |
| Pico de NFLX | **El detector lo capta**: «pico de resultado no operativo en el trimestre 2026-03-31 (z robusto 66.2; habitual −0.14B frente a +2.59B)», bruto $2.73B, neto $2.26B (16.6 % del beneficio TTM), confianza media, aplicado. **P/E publicado 22.1x → normalizado 26.5x**; el score usa el normalizado y marca `pe_unreliable`. |
| Rf | **^TNX se lee en vivo**: 5.225 % a 2026-10-13, `fallback: false`. Ya no se usa el 5.29 % de config. |
| Calidad de fuente «alta» | **Ningún ticker la alcanza** (los 22 con estados). Todos quedan en «media» salvo MU («baja», validación de `revenueGrowth`). El motivo común es que 6–17 campos vienen de Finnhub en lugar de los estados (`forwardPE`, `pegRatio`, `currentRatio`, `beta`, `revenueGrowth`, …). |

### Comparación con `golden/prod`

`golden/prod` reproduce la captura de prod hecha con el *fetch* de c446df5, que no pedía
estados trimestrales ni ^TNX (`sin estados trimestrales`, Rf de config). El código
desplegado es el que reproduce esos golden (suite verde en `a6482f9`). Por tanto toda
diferencia viene de **datos nuevos**: cotización, TTM (estados y balance trimestral) y
Rf. Se comprobó ajuste a ajuste. Dos casos en que el mismo valor puntúa distinto se deben
a reglas que dependen de otra entrada:

- **Forward P/E** (NFLX y V, 19.2x y 24.2x, de +2 a +3): puntúa la compresión frente al P/E trailing, que ahora es el normalizado TTM (NFLX 22x → 27x; V 31x → 32x).
- **SNOW D/E 1.42x → 1.29x** (de 0 a −5): en el golden era informativo porque había caja neta. Con el balance trimestral, la caja baja de $4.03B a $2.34B y la deuda neta pasa de −$1.29B a +$0.42B, así que el D/E vuelve a puntuar.

| Ticker | Cotización | Calidad | Precio (sin ajustar → mostrado) | Veredicto | Confianza | Causa |
|---|---|---|---|---|---|---|
| NFLX | 70.30 → 70.90 | 100 = 100 | 45→46 = | = | media = | Normalización TTM ahora activa (pico de Q1-2026); Rf 5.29 → 5.22 %; DCF $46.45 → $55.55, fiabilidad media → alta (FCF TTM y Rf). Las puntuaciones netas no cambian. |
| JPM | 332.99 → 335.45 | 91 = 91 | 40→40 = | = | alta = | Solo cambian el P/E normalizado (13.95 → 14.28, TTM) y el motivo de fuente (desaparece «sin TTM»). |
| O | 54.18 → 54.58 | **65 → 70** | 65→61 = | = | media = | FFO TTM: margen FFO 56.5 → 63.8 % (+3 → +5) y payout sobre FFO 90 → 79 % (−1 → +1). |
| FCX | 73.69 → 71.86 | **75 → 79** | **35→42 → 35→39** | = (solo cambia el texto de confianza) | **baja → media** | ROE normalizado TTM 12.2 % (+2 → +4, cruza 12 %); FCF/beneficio normalizado 51 → 72 % (0 → +1). Al desaparecer «sin TTM», la fuente pasa de baja a media y la confianza también; el factor 0.5 → 0.75 cambia el precio mostrado. El nivel sigue siendo «exigente». |
| SNOW | 368.89 → 359.50 | **55 → 48** | **10→20 → 20→28** | = | media = | Balance a 2026-07-31: deuda neta positiva (D/E −5, cobertura −3) y current ratio 1.30 → 0.94 (−2). Márgenes TTM mejores (operativo −30.6 → −22.8 %, FCF−SBC −10.3 → −8.3 %). EV/Ventas 27.5 → 23.4x. El nivel sigue siendo «media / muy exigente». |
| V | 385.45 → 393.40 | **98 → 96** | 25→25 = | = | alta = | Current ratio 1.08 → 0.99 (0 → −2, cruza 1.0); FCF/beneficio normalizado 102 → 90 %. DCF $294 → $287. |

Veredicto verbal y nivel de calidad o precio iguales al golden en los 6. El único cambio
de nivel es la confianza de FCX (baja → media), causada por el TTM.

### Tiempos de respuesta

Antes: c446df5 medido justo antes del push. Después: a6482f9. «Fría» es la primera
llamada con la caché vacía; «caliente», la segunda. El PDF se pide tras el análisis,
con este ya en caché.

| | `/api/analysis` fría | `/api/analysis` caliente | `/api/pdf` |
|---|---|---|---|
| Antes (6 tickers) | 6.7–9.9 s (mediana ≈ 8.1) | 0.22–0.46 s | 1.3–4.7 s (típico 1.4–1.9) |
| Después (6 tickers) | 12.0–17.4 s (mediana ≈ 15.2) | 0.25–0.39 s | 1.6–3.8 s (típico 1.8–2.2) |
| Después (16 de la muestra amplia) | 12.5–18.8 s | 0.28–0.66 s | 1.6–2.1 s |

La primera llamada es **≈ 6–7 s más lenta**. El aumento lo causa el código (c446df5 no
pedía nada de esto), no los datos: el motor nuevo descarga 3 estados trimestrales por
ticker y ^TNX (este con caché de 24 h). Caliente, los tiempos son iguales. El PDF tarda
≈ 0.3 s más (más páginas y secciones).

## 4. Muestra amplia (prod, sin corregir nada)

Todas responden 200 y sus PDF se generan. Ningún `errors` no vacío. TTM y ^TNX en vivo
en todas salvo las indicadas.

| Ticker | Arquetipo (motivo) | Calidad | Cotización | Precio | Veredicto · confianza | Cobertura | Observaciones |
|---|---|---|---|---|---|---|---|
| KO | Madura (por defecto) | 85 excelente | $90.12 | 25 muy exigente | excelente · muy exigente · alta | completa | — |
| PG | Madura (por defecto) | 81 excelente | $152.60 | 35→39 exigente | excelente · exigente · media | completa | — |
| JNJ | Madura (por defecto) | 84 excelente | $245.78 | 45→46 razonable | excelente · razonable · media | solidez 0.75 | 1 tarjeta institucional «sin dato» |
| PFE | Madura (por defecto) | 71 sólida | $28.23 | 75→69 atractivo | sólida · atractivo · media | valoración 0.80 | ⚠ DCF con crecimiento −14.8 % (CAGR 3 años desde la base COVID): valor $6.43 (−77 %), fiabilidad baja, fuera del score. Rejilla de sensibilidad con «$-0». |
| XOM | Cíclica (industria) | 71 sólida | $173.62 | 35→39 exigente | sólida · exigente · media | completa | ⚠ el código «CYCLICAL» aparece en prosa visible (fiabilidad del DCF, desglose institucional) |
| NEE | Madura (por defecto) | 65 sólida | $78.18 | 35→39 exigente | sólida · exigente · media | crecimiento 0.67 | ⚠ arquetipo dudoso (utility regulada sin arquetipo propio → Solidez 0/20, 3 riesgos). DCF con **valor razonable negativo** (−$5.76, «equity ≤ 0 tras restar la deuda neta»), fiabilidad baja y fuera del score, pero se muestra; rejilla de sensibilidad con «$-8», «$-17»… |
| T | Madura (por defecto) | 66 sólida | $22.90 | 90 atractivo | sólida · atractivo · alta | crecimiento 0.67 | P/E 7.4 → normalizado 9.7 (cargos especiales + pico no operativo). DCF +86 % con fiabilidad alta: optimista, pero coherente con un P/E bajo. |
| CB | Banco/aseguradora (industria) | 90 excelente | $346.57 | 60→58 razonable | excelente · razonable · media | calidad de ganancias 0.67 | — |
| BRK-B | Banco/aseguradora (industria) | 81 excelente | $521.91 | 50 razonable | excelente · razonable · media | crecimiento 0.50 | ⚠ arquetipo dudoso (conglomerado; confianza de clasificación baja). ⚠ **P/E publicado 0.0087** (beneficio de toda la empresa sobre el precio de la clase B: mezcla de clases A/B). Sin TTM (trimestres incompletos). 3 «sin dato» (KPI, tarjeta, fila de valoración). |
| MA | Madura (red de pagos) | **96** excelente | $603.46 | 40→42 exigente | excelente · exigente · media | completa | calidad saturada |
| AMZN | Madura (por defecto) | 68 sólida | $260.14 | 50 razonable | sólida · razonable · media | **crecimiento 0.33 (no concluyente)**, valoración 0.60 | «Sin dato» explicado por datos: BPA y FCF de 2022 negativos (CAGR no definido) y FCF TTM −$2.47B (capex), así que no hay DCF. Calidad sobre 3 de 4 categorías. |
| MU | Cíclica (industria condicional: margen −66 pt, ingresos −49.5 %) | 92 excelente | $946.34 | 30→40 exigente | excelente · exigente · **baja** | completa | Fuente «baja» (`revenueGrowth` artefacto e incoherente). DCF −94 % fuera del score. |
| NVDA | Madura (semis estable) | **95** excelente | $227.01 | 55→54 razonable | excelente · razonable · media | completa | calidad saturada; ⚠ «Madura» para una empresa que crece ~30 % anual (no hay arquetipo de crecimiento rentable) |
| PLTR | Madura (por defecto) | **100** excelente | $207.45 | 40→42 **exigente** | excelente · exigente · media | crecimiento 0.67 | calidad saturada; ⚠ arquetipo dudoso (crecimiento alto rentable → «Madura»). ⚠ **El precio contradice la lectura elemental**: P/E 177x, EV/EBITDA 184x y P/FCF 148x quedan en «exigente» y no en «muy exigente». El bloque de múltiplos promedia −2.4: el Forward P/E (177x → 87x) suma +3 y el PEG 1.49 neutro diluye. DCF −79 % fuera del score. |
| CROX | Madura (por defecto) | 92 excelente | $117.56 | 85 atractivo | excelente · atractivo · alta | crecimiento 0.67 | Coherente: P/E 10.1, DCF +77 %. |
| TSM | Madura (semis estable) | **100** excelente | $444.99 | 75→69 **atractivo** | excelente · atractivo · media | valoración 0.80 | calidad saturada; ⚠ **mezcla de divisa/ADR**: estados en TWD y cotización del ADR en USD. BPA 87.38 (TWD) → **P/E 5.1** (real ≈ 30), DCF $8 938 (+1909 %), EV/EBITDA −0.1 con texto crudo «EV_EBITDA = -0.1: EBITDA <= 0». **El veredicto «precio atractivo» contradice la lectura elemental.** |
| SPY | Madura (por defecto) | sin dato | $777.55 | sin dato | «Calidad sin dato · precio sin dato» · media | 0 de 4 categorías | ⚠ **No falla de forma controlada**: 200 y se analiza como empresa «Madura», con 29 de 40 estados «sin dato» y confianza «media». c446df5 tampoco rechazaba ETF (no es regresión). |
| ZZZQX | — | — | — | — | — | — | ✓ Falla de forma controlada: 404 `{"detail":"No data found for ZZZQX"}` en análisis y PDF. |

### Resumen de señales

- **Arquetipos dudosos:** NEE (utility → Madura), BRK-B (conglomerado → aseguradora), PLTR y NVDA (crecimiento rentable → Madura), SPY (ETF → Madura).
- **Calidad saturada (≥ 95):** PLTR 100, TSM 100, MA 96, NVDA 95. También NFLX 100 y V 96 en el bloque de los 6.
- **Veredictos que contradicen la lectura elemental:**
  - TSM «precio atractivo», por divisa/ADR;
  - PLTR «precio exigente» con P/E 177x.
- **Datos anómalos:**
  - BRK-B: P/E 0.0087 (clases A/B);
  - TSM: P/E, DCF y EV/EBITDA en divisas mezcladas;
  - NEE: valor razonable negativo mostrado;
  - PFE: DCF proyectado con el −14.8 % post-COVID.
- **Texto incoherente:**
  - el código «CYCLICAL» en prosa visible (FCX, XOM, MU: fiabilidad del DCF, desglose institucional, texto de la dimensión de estabilidad);
  - formato «$-8» en la rejilla de sensibilidad del DCF (PFE, NEE) frente al «−$» del resto;
  - «EV_EBITDA = -0.1: EBITDA <= 0» en TSM;
  - «<= 0» en la nota del WACC (SNOW).
- **Control de errores:** el ticker inexistente da 404 limpio; SPY no se rechaza.
