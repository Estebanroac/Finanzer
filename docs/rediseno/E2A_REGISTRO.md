# Registro de la etapa E2a — datos del motor

*Operador E2a · 2026-10-17 · rama `rediseno/e2a-datos-motor` (worktree `../finanzer_next-e2a`, desde
`rediseno/e1-sistema-historia` + `main` 3063fd4) · sin push, sin merge, sin deploy.*

**Estado:** Tasks 0–12 hechas y verificadas, con la corrección D2 de la revisión del PM de las capturas (titulares que nombran a la empresa). Golden **aprobado por el PM por delegación del usuario** (Task 11,
`docs/fiabilidad/GOLDEN_DIFF_E2A.md`, con las dos citas literales). Pendiente de la revisión final del PM.

## Commits de la rama (`git log e471026^..HEAD`)

| Task | Commit | Mensaje |
|---|---|---|
| 0 | e471026 | main al día en la rama del rediseño (conflicto en `main.py`: se conservan los dos bloques) |
| 0 | 400f20a | las capturas de Playwright se guardan en `capturas-e2a` (las de E1 quedan como referencia) |
| 1 · A | 1b51ab9 | spread ROIC−WACC en puntos porcentuales (golden: solo esas frases) |
| 1 · B | b514e67 | frontera de nivel con mayúscula cuando la frase va sola (golden: solo esa frase) |
| 2 · C | cfe937c | nombre de la bolsa en lugar del código del proveedor (NMS → Nasdaq) |
| 3 | a5ee945 | ficha de la empresa desde EDGAR (SIC, sede, constitución, cierre fiscal, tipo de emisor) |
| 4 | 80ec2c5 | variación del día frente al cierre anterior |
| 5 | d03c445 | historia de 10 ejercicios desde EDGAR (sin red adicional) |
| 6 | f1379d3 | Piotroski con el valor actual y el de comparación de cada criterio |
| 7 | 77a18c4 | escenarios del usuario con el mismo DCF del motor (endpoint sin estado) |
| 8 | 25d0b00 | noticias con resumen, imagen y hora; próximos resultados (anunciados o estimados) |
| 8 · D | 7125abe | titulares y calendario de Finnhub en los fixtures de los 8 tickers (golden: solo las noticias) |
| 9 | 2c18902 | serie de 5 años para la gráfica, con cierre ajustado y eventos |
| 10 | 0bdd9bb | una imagen repetida en titulares distintos es el logotipo del medio (no se publica) |
| 10 | 26b02d8 | el replay atiende un análisis cada vez (carrera latente desde E1) |
| 10 | 5e19425 | `display.extended` en el contrato y cableado mínimo en `/v2` |
| 11 | 5e036bd | diff del golden explicado |
| PM | 2c1b6fb | (revisión del PM) un hueco en la historia de EDGAR no se presenta como crecimiento anual |
| PM | 8e7c7b6 | (revisión del PM) estados de EE. UU. con su nombre en la ficha |
| 11 | a2cc674 | GOLDEN_DIFF con las correcciones del PM |
| 11 | 4ac27c6 | golden con los datos nuevos (aditivos), aprobado por el PM por delegación del usuario |
| 12 | f896543 | accesibilidad (axe) en los 8 tickers y los dos temas, y las 32 capturas |
| 12 | 5ee275e | registro de la etapa |
| PM · D2 | 7784935 | (revisión del PM de las capturas) solo titulares que nombran a la empresa (golden D2) |
| 12 | (este commit) | registro, capturas y GOLDEN_DIFF al día tras D2 |

## Verificación (salida literal)

```
$ ../.venv313/bin/python tools/gen_frontend_config.py --check   → sincronizado
$ ../.venv313/bin/python -m pytest tests -q                      → 4275 passed, 1 skipped in 86.00s
$ npm run check   → check-analysis-literals: sin umbrales literales en los componentes de análisis
                    check-contract: StockAnalysis encaja con 46 salidas del backend
$ npx tsc --noEmit → sin errores
$ npm run test:v2  → Test Files 12 passed (12) · Tests 60 passed (60)
$ npm run e2e:v2   → 108 passed, 2 skipped (59.7s)  (escritorio + móvil; los skip, las dos pruebas de zoom, solo en escritorio)
    · a11y 16×2 (8 tickers × claro/oscuro, axe WCAG 2 A/AA sin infracciones graves ni críticas)
    · capturas 16×2 · simetría 8×2 · legibilidad 10×2 · noticias y cabecera 2×2 · shell 2×2 · precio 1×2
```

**Web actual intacta:**
```
$ git diff rediseno/e1-sistema-historia --stat -- frontend/src/components frontend/src/app/stock frontend/src/app/page.tsx frontend/out
(vacío)
$ git diff e471026 --stat -- frontend/src/components frontend/src/app/stock frontend/src/app/page.tsx \
    frontend/src/app/layout.tsx frontend/src/app/globals.css frontend/out backend/lib/pdf_report.py
(vacío)
```
`api.ts` solo crece (`exchange_code`, `Display.extended?`, `scenario_inputs?` y sus tipos). **Texto del PDF de los 8
tickers** (golden al inicio de E2a frente a HEAD), normalizando solo las causas aprobadas (A spread, B frontera, C bolsa,
D bloque de titulares y su salto de página): igual en los 8. Las claves aditivas no cambian ninguna línea de PDF
(46 JSON de golden regenerados en la Task 11, ningún `.pdf.txt`).

**Golden:** 0 cambios de veredicto en los 42 análisis (36 del panel —SPY se rechaza— y 6 locales), comprobado por el
operador y, de forma independiente, por el PM en 43 golden. Detalle por causa en `GOLDEN_DIFF_E2A.md`.

**Secretos:** `grep -rl 'token=' backend/tests/fixtures` → 0 archivos; ni la clave de Finnhub ni el User-Agent de la
SEC aparecen en ningún archivo del repositorio (búsqueda literal con los valores del Llavero, sin imprimirlos). La
captura de Finnhub se hizo con `FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)"` en el mismo
comando.

**Simetría (sin huecos muertos)**, alto natural texto − visual por capítulo, en px (escritorio; límites: −48 / +96):
```
AAPL  empresa:11 negocio:69 accion:-12 calidad:81 valor:4 rivales:26 riesgos:3 actualidad:-26 conclusion:21
JPM   empresa:15 negocio:50 accion:-12 calidad:4 valor:22 rivales:67 riesgos:48 actualidad:-26 conclusion:21
O     empresa:0 negocio:9 accion:-12 calidad:30 valor:17 rivales:67 riesgos:42 actualidad:-26 conclusion:21
NEE   empresa:-8 negocio:69 accion:-12 calidad:55 valor:-9 rivales:26 riesgos:77 actualidad:-26 conclusion:21
XOM   empresa:18 negocio:69 accion:-12 calidad:30 valor:22 rivales:11 riesgos:29 actualidad:-26 conclusion:21
PLTR  empresa:18 negocio:43 accion:-12 calidad:55 valor:9 rivales:11 riesgos:32 actualidad:-26 conclusion:21
RIVN  empresa:18 negocio:84 accion:-12 calidad:4 valor:25 rivales:8 riesgos:-9 actualidad:-26 conclusion:21
BCS   empresa:15 negocio:50 accion:-12 calidad:4 valor:38 rivales:93 riesgos:48 actualidad:-26 conclusion:-1
```
Gráfica del capítulo 3: 136 px en escritorio (crece con el texto; mínimo 8.5rem) y 150 px en móvil. Capítulo 8: 2
tarjetas de noticias en escritorio (una fila completa), hasta 5 en móvil.

## Capturas

`docs/rediseno/capturas-e2a/`: 32 capturas de página completa `{TICKER}-{light|dark}-{desktop|mobile}.png` (escritorio
1440 px, móvil 375 px), 68 MB (E1: 54 MB). Las de E1 quedan en `capturas-e1/` como referencia.

## Lo que se ve nuevo en `/v2` (replay del panel)

Cabecera: variación del día junto al precio (en móvil, en la misma línea que el precio de 32 px) y la bolsa con su
nombre. Capítulo 1: ficha oficial de EDGAR (las filas que caben junto al texto; el resto, en E3) con su fuente.
Capítulo 3: 5 años reales en 3A/5A, marcas de resultados, dividendos y splits, y rentabilidad de precio y con dividendos
de la empresa, el S&P 500 y el ETF del sector. Capítulo 8: noticias en tarjetas («En inglés») y «Próximos resultados».

| Ticker | Variación del día | Bolsa | Ficha EDGAR (SIC · sede · constitución) | Historia | Serie de la gráfica y eventos | Próximos resultados | Titulares |
|---|---|---|---|---|---|---|---|
| AAPL | +$1.69 (+0.50%) | Nasdaq | 3571 · Electronic Computers · Cupertino, California · California | 10 (2016–2025, USD) | 1 254 sesiones desde 2021-10-18; 11 resultados, 20 dividendos | 2 de noviembre de 2026 · anunciada | 6 de 29 que nombran a Apple (1 con imagen propia) |
| JPM | +$3.85 (+1.16%) | NYSE | 6021 · National Commercial Banks · New York, Nueva York · Delaware | 10 (2016–2025, USD) | 1 254 desde 2021-10-18; 4 resultados (ver pendientes), 20 dividendos | 14 de enero de 2027 · anunciada | 6 de 97 (3) |
| O | +$0.18 (+0.33%) | NYSE | 6798 · Real Estate Investment Trusts · San Diego, California · Maryland | 10 (2016–2025, USD) | 1 254; 11 resultados, 60 dividendos, 1 ajuste de capital (escisión de Orion, 2021) | 2 de noviembre de 2026 · anunciada | 6 de 33 (0) |
| NEE | +$0.15 (+0.19%) | NYSE | 4911 · Electric Services · Juno Beach, Florida · Florida | 10 (2016–2025, USD) | 1 254; 12 resultados, 20 dividendos | 21 de octubre de 2026 · anunciada | 6 de 24 (0) |
| XOM | +$2.98 (+1.71%) | NYSE | 2911 · Petroleum Refining · Spring, Texas · Texas | 10 (2016–2025, USD) | 1 254; 1 resultado (ver pendientes), 20 dividendos | 23 de octubre de 2026 · anunciada | 6 de 34 (0) |
| PLTR | −$7.70 (−3.69%) | Nasdaq | 7372 · Services-Prepackaged Software · Aventura, Florida · (EDGAR no la trae) | 8 (2018–2025, USD) | 1 254; 11 resultados | 2 de noviembre de 2026 · anunciada | 6 de 120 (0) |
| RIVN | −$0.42 (−3.14%) | Nasdaq | 3711 · Motor Vehicles & Passenger Car Bodies · Irvine, California · Delaware | 7 (2019–2025, USD) | 1 237 desde 2021-11-10 (salida a bolsa; «5A · desde 10/11/2021»); 12 resultados | 29 de octubre de 2026 · anunciada | 6 de 27 (0) |
| BCS | +$0.10 (+0.44%) | NYSE | 6029 · Commercial Banks, NEC · London, United Kingdom · United Kingdom | 10 (2016–2025, GBP) | 1 254; 0 resultados (presenta 6-K, sin 8-K), 10 dividendos | 22 de octubre de 2026 · anunciada | 6 de 27 (0) |

Las variaciones del día son las de la sesión de captura de cada ticker en el replay (14–15 de octubre). Fuera de los 8,
`next_earnings` en el panel: 11 anunciadas, 18 estimadas (último 8-K de resultados + 91 días) y 7 sin fecha;
`scenario_inputs`: 21 con DCF significativo y 15 `sin_dato` con su motivo.

## Desviaciones respecto al plan (y motivo)

1. **Arranque de la suite (Task 0):** la primera pasada de Playwright falló en 4 pruebas por la compilación en frío de
   `next dev` (más de 30 s); con los servidores de E2a levantados y calientes, 76 passed. Los servidores de E1 (3000 y
   8767, con cwd en `finanzer_next-e1`) se pararon antes de empezar.
2. **Capturas en `capturas-e2a`** (`screens.spec.ts`): si no, cada pasada de Playwright reescribía las de E1.
3. **Task 1 en dos commits** (A spread, B frontera): un commit por causa, para poder revertir uno solo.
4. **Alcance de A:** la misma causa (spread en «%») aparecía además en la nota del P/E (`display.read_pe`) y en los
   motivos y el valor del ajuste ROIC vs WACC (`financial_ratios`, desglose institucional de la web y el PDF); se
   corrigió en los tres sitios. `numfmt.pp(0)` = «0.0 pp» (sin signo, como `signed_pct`); `pp(None)` = «—» (el plan).
5. **Firmas reales:** `verdict.border(value, bands, labels)` (sin `k`: lo lee de config); la alerta de spread es
   `alert_interpretations._spread(ctx)`, probada con `Ctx`. En B, `display._lc_first` pone la frase en minúscula donde
   va tras «; » o dentro del paréntesis del veredicto ejecutivo.
6. **Config validada:** cada tabla nueva (`[exchanges]`, `[filer_categories]`, `[us_states]`, `[scenario]`, claves de
   `[history]` y `[context]`) declarada en `config/schema.toml` (el arranque falla si no).
7. **Ficha (Task 3):** `company_profile.build(..., edgar_status, edgar_reason)` distingue «no presenta en la SEC» de
   «EDGAR no respondió»; el país de las direcciones extranjeras nuevas sale de `country` (TSM) y no se repite si la
   ciudad ya lo trae (Toyota «JAPAN», Novo «BAGSVAERD DENMARK»); categorías combinadas con `<br>`; se añade «emerging
   growth company». 7 CIK del juego f2b sin caché cruda en el checkout principal (AMAT, TRV, DE, SAN, NOW, FOR, LIN):
   ninguno está en los golden; quedan sin ficha. Revisión del PM: estados de EE. UU. con su nombre.
8. **Lista temporal `E2A_ADDITIVE`:** se aplicó también a las muestras forzadas del contrato. **Error mío, corregido:**
   al ampliarla en f1379d3 borré `test_seams_exist` y `test_local_env_present` de `test_regression.py`; al retirar la
   lista en la Task 11, los dos archivos vuelven a su versión de `main` y los recuperan (4271 tests, antes 4269).
9. **Variación del día (Task 4):** el replay corta la serie en la fecha de captura (XOM: sesión 2026-10-14), así que
   el cierre anterior no es el penúltimo del archivo completo; el test lo compara con la serie que usó el análisis.
10. **Historia (Task 5):** la moneda sale de la unidad de EDGAR (BCS GBP, TSM TWD, TM JPY) en vez de pasarla; NEE y JPM
    no traen capex en la historia de EDGAR (FCF «—»). `years_v2` en `[history]` de `market.toml`, como dice el plan
    (esa tabla es la de la serie de precios; el comentario lo aclara). Revisión del PM: huecos con `gap_before`.
11. **Escenarios (Task 7):** `growth_cap` del motor es 0.50, así que `growth_max = 0.50` (el plan decía 0.30 «si no,
    usa su valor»). `scenario_inputs` siempre presente con `status`/`reason` (no `None`); los supuestos base no se
    recortan (son los del motor). El entorno no trae `httpx`: el endpoint se prueba llamando a la función y con `curl`
    contra el replay (base 116.08 = motor; WACC 11% → 96.32).
12. **Noticias (Task 8):** `news()` devuelve hasta 6; `display` recorta a 5 y a los cuatro campos de siempre (la web
    actual y el PDF no cambian de forma). El test existente de 5 titulares pasa a 6. «Hoy» de `next_earnings` es la
    sesión de la serie (como `_apply_edgar`). Replay: titulares y calendario por símbolo y ruta, sin fechas; titulares
    solo hasta la hora de captura (también recortados en el fixture: AAPL 248 → 63); el calendario hacia delante se usa
    en las consultas que pasan de la fecha de captura. La captura de los fixtures (causa D) va en su propio commit, con
    el golden regenerado sin las claves aditivas.
13. **Serie de 5 años (Task 9):** `c` pasa a ser el cierre **sin ajustar** (en E1 era el ajustado); la gráfica sigue
    pintando el ajustado. El «split» 1.032 de O (escisión de Orion) se rotula «Ajuste de capital (factor 1.032)». Las
    marcas de resultados salen de los 8-K desde `data.edgar.since` (2024-01-01) y `events_reason` lo dice.
14. **Capítulo 8 (Task 10):** seis tarjetas con imagen no caben junto al texto sin romper la regla de E1 de no dejar
    huecos muertos; la maqueta 1 pone 2 titulares + próximos resultados. El modelo trae los 6 (Vitest) y el capítulo
    enseña los pares que caben (recorte de 2 en 2, `fitStep`): 2 en escritorio, hasta 5 en móvil. El Playwright
    comprueba filas completas, mismo alto, fecha, medio, resumen, idioma y texto alternativo (no «6 visibles»).
15. **Gráfica (Task 10):** la rentabilidad va en una tabla de dos filas (Precio · Con dividendos) × tres series; la
    leyenda de las marcas ocupa el sitio de «1A · base 100 · cierre ajustado» (el periodo lo marca la pestaña; base 100 y
    dividendos, en la etiqueta accesible y el `title`); en escritorio la gráfica parte de 8.5rem y crece hasta igualar
    el texto (móvil: 9.375rem).
16. **Logotipos (Task 10, en el motor):** Yahoo publica su logotipo genérico como imagen de muchos titulares; una imagen
    repetida en titulares distintos no se publica (la tarjeta enseña el medio sobre el fondo neutro, con la misma altura).
17. **Replay con un análisis cada vez:** con Playwright en paralelo, `reset_state` de un análisis vaciaba la serie de
    otro y su capítulo 3 salía sin momentum ni tendencia (carrera latente desde E1; se vio en una captura).
18. **Accesibilidad:** `a11y.spec.ts` pasa de AAPL a los 8 tickers en los dos temas, con la gráfica y las tarjetas ya
    pintadas.
19. **Titulares que nombran a la empresa (D2, revisión del PM de las capturas):** Finnhub pone el ticker en `related` de
    noticias generales del mercado (AAPL enseñaba «CPI Pressures Markets…»). `market_context.news` filtra por mención
    del ticker o del nombre corto (sufijos societarios y palabras comunes en config; «Realty Income» completo; un ticker
    de una letra solo como «(O)»). Ningún ticker se queda sin titulares en 7 días (24–120), así que no se añadió
    `news_days_v2`. Golden D2: solo el bloque de noticias de los 8; 0 cambios de veredicto; aprobada por el PM.
20. **Paradas:** por delegación expresa del usuario, la aprobación del golden y la revisión final son del PM.

## Pendientes para E2b / E3 / E4

- **Marcas de resultados incompletas en emisores muy activos:** EDGAR `submissions` («recent») guarda los últimos ~1 000
  filings; JPM presenta miles de folletos 424B2 y solo se ven 4 resultados. Leer los archivos de filings antiguos
  (`filings.files`) o el calendario histórico de Finnhub. XOM publica sus resultados casi siempre sin el apartado 2.02
  (1 marca).
- **Moneda en precios no-USD:** la cabecera y `price_card` escriben «$» también en MC.PA (EUR) (heredado de E1 y del
  motor); la variación del día sigue esa misma forma. La historia de 10 años sí va en la moneda de los estados.
- **E3:** página de profundidad del capítulo 8 con los 6 titulares (2 × 3); historia de 10 ejercicios en tabla/gráfica
  (con `gap_before` dicho); Piotroski con valores (`piotroski_values`); escenarios (`scenario_inputs` +
  `POST /api/v2/scenario`); ficha completa (cierre fiscal y tipo de emisor, que el capítulo 1 recorta).
- **E4 (móvil):** una cifra corta se parte en dos líneas («+1.2 / pp» en la fuerza relativa de NEE).
- **ESLint en `/v2`:** 5 problemas heredados de E1 (`setState` dentro de un efecto en `StoryPageClient`, variables sin
  usar en `story.ts`), sin tocar.
- **Resúmenes de Finnhub cortados en origen** (O: «yields 6. 7% against Realty Income’s 6.»): vienen así de la fuente.
- **E2b** (plan aparte): segmentos, rivales SIC y tendencias de la portada.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
