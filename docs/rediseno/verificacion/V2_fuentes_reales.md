# V2 · Fuentes reales (rama `rediseno/e4-portada` con la v4 fusionada, 2026-10-18)

**Montaje.** Backend real en local (`backend/tools/load_server.py --port 8771 --no-prewarm`) sirviendo el build de la
rama (`npm run build`) y la API en el mismo origen. Fuentes reales: Yahoo, SEC EDGAR y Finnhub. Las claves salen del
Llavero solo en el entorno de ese comando; ningún informe contiene una clave (comprobado: ni el parámetro de la clave de Finnhub).

**Recorrido:**
- API: `backend/tools/real_sources.py`, 3 tickers a la vez. Por ticker: análisis, `/v2/{T}`, precios, segmentos,
  rivales hasta completar, escenario (base, extremos y dos cuerpos malos) y `/api/v2/pdf`.
- Páginas: `frontend/e2e/fuentes-reales/paginas.spec.ts`. Historia y 9 páginas por ticker, en escritorio, con errores
  de consola, errores de página, respuestas 5xx y «undefined/NaN» en el texto.
- Tablas: `backend/tools/real_sources_report.py`, en `V2_tablas.md` (segunda pasada, con los arreglos) y
  `V2_tablas_frio.md` (primera pasada, sin caché). Datos: `V2_api.json` y `V2_api_frio.json`.

**Tickers (52):**

| Grupo | Tickers |
|---|---|
| Verificación (8) | AAPL, JPM, O, NEE, XOM, PLTR, RIVN, BCS |
| Universo al azar (30, semilla 20261018) | FTV, MUFG, BIIB, TROW, WM, CPT, HBAN, BBVA, KKR, IR, FDXF, WTW, AZN, HWM, CVS, COP, BX, HCA, GNRC, WFC, BHP, CINF, VMC, A, C, CMI, ETN, CFG, ASML, AON |
| Casos raros (13) | BRK-B; GOOG y GOOGL (dos clases); TSM (ADR con factor); CB (aseguradora); PLD (REIT); LCID (pre-beneficio); CRCL (salida a bolsa de 2025-06); MC.PA (París); SPY (ETF); ZZZZZ (inexistente); BF.B (con punto); SIVB (deslistado en 2023) |
| Añadido | CEG (apareció como rival de NEE con un 500) |

## Resultado

**Ningún 5xx con los arreglos.** Las 520 páginas cargan sin errores de consola, sin 5xx y sin «undefined/NaN».

| Endpoint | Éxito | 4xx esperado | p50 / p95 en frío (s) | p50 / p95 con caché (s) |
|---|---|---|---|---|
| `/api/analysis` | 48/51 (los 51 menos 3) | 3: SPY 422 «es un ETF, así que no se analiza»; ZZZZZ y SIVB 404 «No data found» | 2,44 / 8,50 (los lentos son los 4xx: Yahoo reintenta; empresas reales ≤ 5,7) | 2,58 / 4,01 |
| `/v2/{T}` (HTML) | 51/51 | — | 0,002 / 0,010 | 0,002 / 0,007 |
| `/api/v2/prices` | 51/51 | — | 0,56 / 2,45 | 0,71 / 1,30 |
| `/api/v2/segments` | 51/51 | — | 0,62 / 1,06 | 0,10 / 0,21 |
| `/api/v2/peers` (hasta completar) | 51/51 | — | 76 / 128 | 32 / 68 |
| escenario: base | 48/48 (reproduce el valor del motor en todos) | — | 0,001 / 0,024 | 0,001 / 0,003 |
| escenario: extremos | 48/48 (recortados y finitos) | — | 0,001 / 0,002 | 0,001 / 0,002 |
| escenario: años 2·10⁷ y NaN | 29/29 → 422 cada uno | — | 0,001 | 0,001 |
| `/api/v2/pdf` | 48/51 | 3 (los mismos del análisis) | 0,24 / 4,64 | 0,25 / 0,73 |
| Páginas (historia + 9) | 520/520 | — | carga hasta red en reposo: p50 1,06 s, p95 5,73 s | — |

- **Tiempos de los rivales.** Incluyen analizar la empresa, pedir hasta 20 capitalizaciones a Finnhub (1,5 s entre
  ellas) y analizar 5 rivales en la cola compartida. Con 3 empresas pedidas a la vez, la cola atiende 15 rivales.
- **«4xx esperado».** SPY, ZZZZZ y SIVB: la página dice el motivo y el PDF responde lo mismo.

## Bugs encontrados y arreglados en origen (cada uno con su test)

| Bug | Causa | Arreglo |
|---|---|---|
| **CEG: `/api/analysis` → 500** (y su fila de rival en NEE salía en «fallo») | El ejercicio antes de su escisión trae 0 acciones; `cyclicality.growth_profitable_measures` dividía por cero | `cyclicality._shares`: una cuenta de acciones ≤ 0 es un dato vacío (75f1c1f). `diff_golden` sin diferencias |
| **BF.B y BRK.B → 404 «No data found»** (producción, igual) | En Yahoo son BF-B y BRK-B | El análisis, los PDF y `_v2_symbol` normalizan la clase con `universe.norm_symbol` (solo A/B/C; BARC.L no cambia) (75f1c1f) |
| **CRCL: segmentos «el 10-K/A no desglosa ingresos»** | Un 10-K/A de julio (solo la Parte III) ganaba por fecha al 10-K de marzo del mismo ejercicio | El ejercicio más reciente y, dentro de él, el original antes que la enmienda (032877c). CRCL: 3 segmentos |

## Cada `sin_dato` con su motivo

| Bloque | Motivo | Tickers | ¿Razonable? |
|---|---|---|---|
| Escenario (`scenario_inputs`) | «No aplica a bancos y aseguradoras» | JPM, BCS, MUFG, HBAN, BBVA, WFC, CINF, C, CFG, BRK-B, CB, CRCL | Sí: el DCF de flujo de caja no aplica. CRCL (emisor de stablecoins: ingresa por las reservas) clasificado como financiero es defendible |
| Escenario | «No aplica a REIT» | O, CPT, PLD | Sí |
| Escenario | «No aplica a empresas en crecimiento sin beneficio con FCF negativo» | RIVN, LCID | Sí |
| Escenario | «No aplica a utilities reguladas» | NEE | Sí |
| Escenario | «FCF − SBC base −$225 M (≤ 0)» | FDXF | Sí |
| Ficha, historia de 10 años, segmentos | «el emisor no presenta en la SEC» | MC.PA (y ZZZZZ, SIVB en segmentos) | Sí |
| Próximos resultados | «Sin fecha anunciada» | BCS, MC.PA | Sí (Finnhub no la tiene) |
| Segmentos | «el 10-K/20-F no desglosa ingresos por segmento en XBRL» | CPT, BBVA | Sí. CPT: un solo segmento. BBVA: banco IFRS, sin «ingresos» por segmento |
| Segmentos | ídem | CB | **Dudoso:** Chubb desglosa por segmento las primas, no los ingresos; el motivo es literal pero engaña. Ver «Para decidir» |
| Segmentos | «sin informe anual con XBRL en la SEC» | SPY | Sí |
| Rivales | «sin industria de referencia para proponer rivales» | TROW, KKR, BX (gestoras), AON, WTW (intermediarios de seguros) | **Dudoso:** ver «Para decidir» |
| Rival ACLX (de BIIB) | «No data found for ACLX» | BIIB | Razonable: Yahoo ya no tiene ni su serie. Candidato desfasado de la lista de Damodaran |
| Precios (empresa) | «Yahoo no devolvió la serie de precios» | ZZZZZ, SIVB | Sí |
| Precios (sector) | «sin ETF de sector» | SPY, ZZZZZ, SIVB | Sí |

## Cifras sospechosas: comparación con producción (finanzer.app, pública)

En 16 tickers (los 8 de verificación y TSM, GOOGL, CB, PLD, ASML, MUFG, WFC y CVS):
- **Coinciden** los 16 veredictos y precios, y la calidad en 15.
- **Difieren** algunas puntuaciones de precio (BCS 70/65, TSM 39/35, PLD 50/55, MUFG 35/30, WFC 61/54, CVS 80/75) y en
  AAPL la calidad (79/75) y el DCF (119,98/119,81).

**Explicación.** Arranqué el backend de **main** en local con las mismas fuentes, en el mismo instante: da exactamente
lo mismo que la v4 en los 7 tickers con diferencias. La diferencia está en los datos o la caché de producción (Render),
no en la v4.

## Decisiones del PM y lo hecho

| Punto | Decisión | Hecho |
|---|---|---|
| 1. Gestoras e intermediarios de seguros sin industria (TROW, KKR, BX, AON, WTW) | **Pendiente del motor (fiabilidad), fuera de la migración**: mapear esas industrias movería cifras del motor y va con su propio golden | Comprobado en `/v2/TROW/rivales`: la página dice «sin industria de referencia para proponer rivales (puedes añadirlos a mano)», deja añadir (BEN entra analizado: calidad 58, precio 30) y la nota pasa a «menos de 3 comparables elegidos». Detalle para E3: la entradilla sigue diciendo «Rivales propuestos por el motor: misma industria de referencia…» cuando no hay propuestos |
| 2. Segmentos de aseguradoras | Sí: primas como concepto de ingresos solo para el arquetipo asegurador | b1c7b02. Para una aseguradora (la regla del motor: industria «Insurance - …») y solo si ningún concepto de ingresos da segmentos, `premium_concepts` (config). CB: «Primas», cubren el 89 % de los ingresos consolidados (como BCS). TRV, MET, BRK-B y AAPL no cambian. Además, «Segment Life» → «Life» |
| 3. «Descargar PDF» sin análisis | Lo arregla E3 (TopBar) | — |
| 4. Rival desaparecido | Sí: en la lista automática, sustitución por el siguiente del ranking, como mucho 2, anotada | 2a54612. ACLX → el siguiente; la nota dice «sustituidos (la fuente ya no los tiene): ACLX → …». Otro fallo se queda con su motivo; la lista elegida a mano no se toca |
| 5. Portada del 20-F/A | Sí: el factor sale del 20-F original, salvo enmienda con portada completa | 839eb8a. Test con un 20-F/A sintético de solo la Parte III. `diff_golden` sin diferencias |

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
