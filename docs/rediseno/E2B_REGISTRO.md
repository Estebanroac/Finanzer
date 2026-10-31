# Registro de la etapa E2b — segmentos, rivales y tendencias (`/api/v2/…`)

*Operador E2b · 2026-10-17 · rama `rediseno/e2b-segmentos-rivales-tendencias` (worktree `../finanzer_next-e2b`, desde
`rediseno/e1-sistema-historia` 966f576 con `main` 732fae0 fusionada) · sin push, sin merge, sin deploy.*

**Estado:** Tasks 0–5 hechas y verificadas, más las dos revisiones del PM (segmentos sobre 5e043cc y rivales sobre
cc8828f; sección "Revisiones del PM"). El análisis y el PDF no cambian: golden idéntico a `main` (ni una línea).
Sin UI (el cableado en `/v2` es de E3 y E4). Pendiente de la aprobación del PM (delegada por el usuario).

## Commits de la rama (`git log 966f576..HEAD`)

| Task | Commit | Mensaje |
|---|---|---|
| 0 | 08c340a | Merge main (conserva `/api/v2/prices` **y** el arranque de `keepalive`) |
| 1 | 8a2e991 | universo de valores (S&P 500 + ADR principales) con su industria de Damodaran |
| 2 | 5e043cc | ingresos por segmento desde la instancia XBRL del último 10-K (endpoint perezoso) |
| 3 | cc8828f | rivales automáticos y editables, analizados con el motor completo en segundo plano |
| 4 | 9a4dd74 | tendencias del día sobre el universo (más negociadas, subidas, caídas) con cálculo perezoso |
| 5 | 35f7c21 | tipos aditivos y clientes de segmentos, rivales y tendencias, con su contrato contra el backend |
| 5 | feb78d0 | registro de la etapa |
| PM | 5526d75 | segmentos tras la revisión del PM (miembros solapados, ejes descartados, instancia en streaming, NEE) |
| PM | a056351 | rivales tras la revisión del PM (industria del análisis, región ampliada, universo con más ADR) y registro |
| PM | dc3c4d2 | cobertura de los segmentos frente a los ingresos consolidados (concepto en español, comisiones de BCS) |
| PM | 8c23341 | rivales de la propia región primero dentro de una banda de tamaño (BCS: bancos europeos) |
| motor | af0d302 | emparejamiento tolerante de ADR en `industry_bench.firm` (solo único; golden sin cambios) |
| PM | (este commit) | registro de los tres encargos finales |

`main` avanzó durante la etapa (57de44f, 57263bd: solo planes de E3–E5 en `docs/`); no se volvió a fusionar (no hay
código nuevo que integrar).

## Endpoints nuevos (perezosos, fuera del camino de `/api/analysis`)

| Endpoint | Módulo | Respuesta |
|---|---|---|
| `GET /api/v2/segments/{symbol}` | `lib/segments.py` (+ `sec_edgar.parse_segments`, `sec_edgar.labels`) | `{status ok\|sin_dato, fiscal_years, axis, axis_label, concept, segments[{member, label, values{FY}, share_last}], total_reported{FY}, reconciles, gap_pct, notes[], secondary, others[], currency, source{form, filed, accn, period_end}, reason}` |
| `GET /api/v2/peers/{symbol}[?symbols=A,B]` | `lib/peers.py` | `{status listo\|calculando\|sin_dato, symbol, industry, source automaticos\|elegidos, rivals[{symbol, status en_cola\|analizando\|listo\|fallo, summary?, reason?}], note, poll_s}` |
| `GET /api/v2/trending` | `lib/trending.py` (+ `lib/universe.py`) | `{status listo\|calculando\|sin_dato, data{session, as_of, lists{most_traded, gainers, losers}[{symbol, name, price, change_pct, dollar_volume}], universe_date, count, failed_batches, note}, refreshing, reason}` |

Símbolo validado `^[A-Z0-9.\-]{1,10}$` (422 si no); `?symbols=` como mucho `peers_count` (5). Tipos exactos en
`frontend/src/lib/api.ts` (`SegmentsResponse`, `PeersResponse`, `TrendingResponse`) y clientes `fetchSegments`,
`fetchPeers(symbol, symbols?)`, `fetchTrending` en `frontend/src/v2/lib/companyData.ts`.

## Verificación (salidas)

- Suite del backend: `4230 passed, 1 skipped in 90.54s` (antes de E2b: 4175).
- Golden: `git diff main --stat -- backend/tests/golden` vacío; `tests/diff_golden.py --env panel` → `Resultado: sin diferencias`.
- Frontend: `npm run check` → `check-contract: StockAnalysis encaja con 46 salidas del backend`; `vitest run src/v2` →
  `55 passed`; `tsc --noEmit` y `eslint` limpios.
- Contrato de los tipos nuevos: `tests/test_e2b_contract.py` vuelca salidas reales de los tres endpoints (fixtures) y
  las pasa por `check-contract.mjs --strict-unions --root=<Tipo>` (opción nueva): 3 passed. Prueba negativa: las
  muestras de segmentos contra `TrendingResponse` → `Contrato roto (8)` (el verificador muerde).
- Secretos: `grep -rn "token=" backend/tests/fixtures` vacío; el log del servidor real de la prueba de carga, 0 `token=`.

## Task 1 · Universo

`tools/build_universe.py` (con red, local) → `config/universe.tsv` del 2026-10-17: **543 valores** (503 del S&P 500 +
40 ADR); industria de Damodaran para **524 (96,5 %)**. Sin industria (anotados): BNY ECHO FDXF HONA MRSH P SKYD VMRK
VYLR (altas del S&P posteriores al archivo de Damodaran de enero de 2026) y ARM BABA BN BP CNQ ENB PDD RY SE TD (ADR
sin emparejamiento exacto por nombre legal y país). Todos los ADR con factor en `config/adr.toml` están en la lista.

## Task 2 · Segmentos: revisión a mano de los 8 (+ MC.PA)

| Ticker | Resultado | Eje | Segmentos (peso del último ejercicio) | Concilia | Tiempo real en frío |
|---|---|---|---|---|---|
| AAPL | ok | negocio (+ geográfico, + productos en `others`) | Americas 43 %, Europe 27 %, Greater China 15 %, Rest of Asia Pacific 8 %, Japan 7 %; productos: iPhone 50 %, Service 26 %, Wearables 9 %, Mac 8 %, iPad 7 % | sí (0,0 %) | 1,8 s |
| JPM | ok | negocio (+ geográfico) | Commercial & Investment Bank 44 %, Consumer & Community Banking 43 %, Asset & Wealth Management 13 % | **no** (−2,1 %: Corporate +7,0 bn y partidas de conciliación −3,1 bn fuera de los segmentos) | 1,2 s |
| O | ok | productos (tipo de inmueble) | Retail 80 %, Industrial 16 %, Other 5 % | **no** (−5,4 %: otros ingresos) | 1,5 s |
| NEE | sin_dato | — | solo desglosa por entidad legal (FPL, `dei:LegalEntityAxis`): "el 10-K no desglosa ingresos por segmento en XBRL" | — | 0,9 s |
| XOM | ok | negocio, suma de zonas y neto de ventas entre segmentos (`notes`) | Energy Products 74 %, Upstream 14 %, Chemical Products 7 %, Specialty Products 5 % | sí (−0,3 %) | 1,1 s |
| PLTR | ok | negocio | Government 54 %, Commercial 46 % | sí | 0,8 s |
| RIVN | ok | negocio (+ productos) | Automotive 71 %, Software and Services 29 % | sí | 0,7 s |
| BCS | sin_dato | — | "la instancia XBRL del 20-F pesa 44 MB (más de 25 MB: no se lee por memoria)" — no se descarga (tamaño del índice) | — | 0,3 s |
| MC.PA | sin_dato | — | "no presenta estados en la SEC" | — | — |

Segunda consulta (caché por filing): 1 ms. Fixtures: `tests/fixtures/segments/<T>.json` (7–80 KB; solo lo que usa
`build`); `tests/capture_segments.py` comprueba que el replay da **exactamente** lo mismo que la descarga en vivo (9/9).

## Task 3 · Rivales automáticos propuestos (Finnhub, 2026-10-17) y revisión a mano

| Ticker | Industria (Damodaran) | Rivales (capitalización, B$) | ¿Comparables? |
|---|---|---|---|
| AAPL | Computers/Peripherals | DELL 287, SNDK 188, STX 145, WDC 133, HPE 73 | sí (hardware; MSFT es software para Damodaran) |
| JPM | Bank (Money Center) | BAC 355, WFC 258, HSBC 244, C 208, SAN 174 | sí |
| O | Retail (REITs) | SPG 66, KIM 15, REG 13, FRT 9, BRX 8 | sí |
| NEE | Power | SO 105, CEG 96, DUK 95, AEP 69, VST 51 | sí |
| XOM | Oil/Gas (Integrated) | CVX 445, SHEL 223, TTE 179, OXY 62 (solo 4: BP sin industria en el universo) | sí |
| PLTR | Software (System & Application) | ORCL 388, PANW 280, CRWD 233, CRM 198, NOW 147 | sí |
| RIVN | Auto & Truck | F 50, GM 74, THO 4, HOG 3, LCID 1 | aceptable (THO y HOG: caravanas y motos; TSLA queda lejos por tamaño) |
| BCS | Bank (Money Center), región desconocida | NU 70, FITB 46, ING 83, PNC 87, USB 92 | mejorable: sin región (ADR que `firm()` no resuelve por símbolo) solo mira el universo; HSBC y SAN quedan más lejos por tamaño |

Replay (8768): `?symbols=MSFT,NVDA,MU,AMZN,DELL` → 4 `listo` en ~2 s y DELL `fallo` "no está en el juego de fixtures";
automáticos de JPM → BAC y HSBC `listo` con las mismas cifras que su golden (P/E 12.72x, P/B 1.30x…), WFC/C/SAN `fallo`
sin fixtures; 6 símbolos → 422.

## Task 4 · Tendencias

Descarga real del universo (sesión 2026-10-16): 543/543 con dos sesiones, 0 lotes fallidos, **19,9 s** (14,4 s en otra
medida). Memoria: con pandas y yfinance ya importados (como en el servidor) 94 MB → pico 130 MB (**+37 MB**); proceso en
frío, 224 MB. Más negociadas: MU, NVDA, TSLA, AAPL, META…; subidas: TRGP +4,4 %, FANG, KMI, APA, NOC…; caídas: TWLO
−10,6 %, SMCI −9,9 %, FLEX, MRNA, PANW…. Replay de la captura idéntico al vivo.

## Task 5 · Prueba de carga contra el backend real (local, claves del Llavero solo en el entorno del servidor)

`uvicorn main:app --port 8768`; RSS muestreado cada 0,5 s.

| Paso | Resultado |
|---|---|
| Arranque | RSS 123 MB |
| Segmentos de los 8 en frío | 0,3–1,8 s cada uno; caché 1 ms |
| Tendencias desde cero | `calculando` → `listo` a los 26,1 s (respuestas de 2 ms mientras); 543 valores, 0 lotes fallidos |
| Rivales de AAPL (automáticos) | `calculando` 32 s (21 capitalizaciones de Finnhub a 1,5 s), después los 5 análisis completos de uno en uno (≈ 4 s cada uno); todos `listo` a los 48 s; cada consulta responde en 2–46 ms |
| Usuario en medio (MSFT a los 40 s) | HTTP 200 en 2,7 s mientras corrían los rivales |
| **Pico de memoria** | **238 MB** (final 226 MB): por debajo de 400 MB, no hizo falta reducir nada |
| Errores | ninguno; un aviso de Finnhub (403 en `profile2` de un candidato, plan gratuito): esa empresa va al final por tamaño |

## Desviaciones del plan (el código real manda)

1. **Universo:** columna extra `cik` (para la industria de otra clase de la misma empresa —GOOG por GOOGL— y para
   excluirla como rival). Los ADR no tienen sector GICS (la tabla pública solo lo da al S&P 500); su nombre es el título
   legal de EDGAR y su industria sale por nombre legal + país (`industry_bench.firm`), que es lo que hace el motor.
2. **Segmentos — miembro neutro:** desde ASU 2023-07 el ingreso de cada segmento operativo viene con **dos**
   dimensiones (`ConsolidationItemsAxis=OperatingSegmentsMember` + el eje del segmento; AAPL, JPM). La regla del plan
   ("una sola dimensión") los perdía todos: `neutral_members` en la config no cuenta como dimensión.
3. **Segmentos — agregados:** `ProductOrServiceAxis` mezcla agregados (Product, Service) con el detalle (iPhone, Mac…).
   Un miembro que es la suma de otros dos o más (`aggregate_tolerance` 0,1 %) sale; si no, se contaría dos veces.
4. **Segmentos — XOM:** sus segmentos solo vienen cruzados con la geografía (EE. UU. / fuera) y brutos, con las ventas
   entre segmentos aparte. `parse_segments` devuelve además `by_geo` y `elims`; `build` prueba, por orden, el eje tal
   cual, neto de eliminaciones, la suma de zonas y la suma neta, y se queda con la primera que concilia (si ninguna, la
   primera que haya). Lo que se hizo va en `notes`. `parse_segments` lleva dos parámetros más (`geo_axes`,
   `eliminations`) y su salida es `{axes{eje{concepto{miembro{periodo}}}}, totals, by_geo, elims, units}`.
5. **Segmentos — un concepto por eje** (el primero por prioridad que concilia), no por miembro: mezclar conceptos entre
   miembros mezcla definiciones (JPM usa `RevenuesNetOfInterestExpense` en los segmentos y `Revenues` en la geografía).
6. **Segmentos — `others`:** los ejes utilizables que no son el principal ni el geográfico (productos de AAPL); un eje
   con los mismos miembros que otro ya mostrado no se repite. Ejes IFRS en la config (`SegmentsAxis`,
   `ProductsAndServicesAxis`, `GeographicalAreasAxis`) y conceptos `RevenueFromContractWithCustomerIncludingAssessedTax`
   y `RevenueFromContractsWithCustomers`.
7. **Segmentos — filing:** `recent` de submissions trae solo los últimos ~1000 filings: si no hay un anual, se miran las
   páginas antiguas. XOM: el 10-K está en el CIK predecesor (34088, `data.edgar.predecessors`). El tamaño de la instancia
   sale de `index.json`: si supera `max_instance_mb` no se descarga. Etiquetas limpias ("Americas Segment" → "Americas";
   "Product and Service, Retail" → "Retail"). `sec_edgar._get` acepta un descargador propio (el replay de segmentos).
8. **Rivales — orden en segundo plano:** las capitalizaciones (Finnhub, ≤ 60/min) también van al hilo: la primera
   consulta de una empresa responde `calculando` (~30 s la primera vez, 7 días en caché). Cola con prioridad (ordenar
   antes que analizar). Config añadida: `max_cap_lookups` 20 (candidatos del universo primero), `finnhub_min_interval_s`
   1,5, `fail_ttl_s` 600, `busy_wait_s` 2. Respuesta con `industry` y `source`. Sin región conocida: solo el universo.
9. **Rivales — prioridad de los usuarios:** `main._slot()` cuenta a los usuarios que esperan turno (análisis **y PDF**);
   el hilo de rivales no pide turno mientras haya alguno. `_compute_limited(symbol, user=True)`; el análisis en sí no
   cambia (golden idéntico).
10. **Tendencias:** `compute` recorta a la última sesión cerrada (en horario de mercado Yahoo trae la fila parcial de
    hoy). Config añadida: `close_hour_et` 16 y `retry_after_s` 600 (tras un fallo). Salida con `refreshing`,
    `failed_batches` y `note` (universo viejo). Tras un festivo (Yahoo sin sesión nueva) la lista sigue con su fecha y no
    se vuelve a descargar hasta la siguiente sesión esperada. Precalentado al arrancar solo con `RENDER_EXTERNAL_URL`.
11. **Contrato:** `check-contract.mjs --root=<Tipo>` para contrastar los tipos nuevos con salidas reales.
12. **Replay:** el almacén de fixtures no admite análisis simultáneos: mientras el replay calcula rivales, no pidas otro
    análisis (en producción no aplica).

## Revisiones del PM (2026-10-17)

### Segmentos (sobre 5e043cc) → 5526d75

1. **Miembros solapados (RIVN, ProductOrServiceAxis):** si la suma del eje supera el total consolidado más que
   `reconcile_tolerance`, se busca el subconjunto que concilia (exhaustivo hasta `max_subset_members` = 12): el de más
   miembros; a igualdad, el de menos etiquetas casi duplicadas ("Software and Services" / "… Revenue") y después el de
   menor diferencia. RIVN: Vehicles 67,6 %, Software And Services Revenue 28,8 %, Regulatory Credits 3,7 %, concilia; la
   nota dice qué quedó fuera (Automotive, Software And Services). Si ninguno concilia: `reconciles: false` y nota
   "miembros solapados: ninguna combinación concilia…". Tests con la forma de RIVN y sin partición posible.
2. **Ejes sin información (XOM):** un eje con un miembro de más de `max_single_share` = 0,95 se descarta y va a
   `dropped_axes` con su motivo: «Sales And Other Operating Revenue» es el 97.5% del total: son componentes del ingreso,
   no segmentos. Campo nuevo también en `SegmentsResponse` (api.ts) y en el contrato.
3. **Instancias grandes (BCS):** la instancia se descarga en streaming a un archivo temporal (`tempfile`, borrado al
   salir; `sec_edgar._get_to_file`, gzip en flujo) y `parse_segments` lee el archivo. `max_instance_mb` = 150 (solo
   disco y tiempo). Memoria pico medida (`resource.getrusage`, proceso con pandas y yfinance ya importados, 99 MB):
   **BCS 44 MB → +50 MB** (1,7 s), HSBC +38 MB (1,3 s), JPM 15 MB → +38 MB. La memoria ya no depende del tamaño del
   archivo: el pico lo pone el bloque de texto más grande de la instancia, que ElementTree monta entero (BCS: una nota de
   8,6 MB; tracemalloc 39 MB). Si hiciera falta bajarlo, un lector `expat` que ignore el texto de esos bloques.
   BCS ahora: **ok**, eje `ProductsAndServicesAxis` (Transactional Banking Services 45 %, Underwriting, Syndication and
   Commitment Fees 25 %, Brokerage Commissions 20 %, Management and Advisory 9 %), concilia con
   `RevenueFromContractsWithCustomers` (£11,1 bn). **Ojo:** en un banco ese concepto son solo las comisiones (NIIF 15),
   no los ingresos totales (sin intereses): ver avisos para E3. HSBC: sin_dato (su 20-F no desglosa ingresos en XBRL con
   los conceptos de la config).
4. **NEE:** no informa por `LegalEntityAxis` (ese eje solo trae FPL, no concilia). Sus segmentos están en
   `StatementBusinessSegmentsAxis` (FPL y NEER) con el concepto de eléctricas `RegulatedAndUnregulatedOperatingRevenue`,
   y el contexto de FPL repite el miembro en `LegalEntityAxis`. Arreglo: el concepto en `revenue_concepts` y
   `redundant_axes = ["LegalEntityAxis"]` (un miembro que repite el de otra dimensión no cuenta). NEE: **ok**, Florida
   Power & Light Company 68 %, NEER 32 %, concilia (−1,4 %). Test con la forma de NEE.

Los 9 recapturados (replay idéntico al vivo en los 9). Tabla actualizada de la Task 2: NEE ok (FPL 68 %, NEER 32 %); BCS
ok (comisiones); XOM con `dropped_axes`; RIVN con productos por partición.

### Rivales (sobre cc8828f) → este commit

1. **La industria sale del análisis de la propia empresa**, no del símbolo: `benchmark.industry` (la que usó la
   referencia sectorial; para un ADR, por nombre legal y país, o por el mapa de la industria de Yahoo). El hilo de fondo
   analiza primero la propia empresa (mismo turno de prioridad baja; resumen en la LRU) y de ahí lee
   `{industry, region (home_region si la referencia fue global), basis}` (`peers.reference`, también en
   `summary.reference`). Sin industria de referencia (mercado amplio, media de sector o provisional) o si la empresa no
   se puede analizar: `rivals: []`, `status: sin_dato` y la nota "sin industria de referencia para proponer rivales
   (puedes añadirlos a mano)". `candidates` con industria vacía devuelve `[]` (nunca más BNY, ECHO, FDXF…). Se quitó
   `classify`. La respuesta trae `company` (resumen de la propia empresa: la fila de arriba de la tabla de E3).
   Tests: ADR resuelto por nombre (BCS) y empresa sin industria / que no se puede analizar.
2. **Región ampliada:** si el universo y la propia región dan menos de `peers_count`, se añaden las demás regiones.
   Además, con la capitalización de la empresa conocida, **los candidatos sin capitalización no entran** (Finnhub
   gratuito no da las de fuera de EE. UU.: entraban de relleno y podían ser la cotización local de la propia empresa,
   como BARC.L para BCS).
3. **BP fuera de XOM:** no era por la región sino porque el universo no tenía su industria (el nombre de EDGAR "BP PLC"
   no emparejaba con "BP p.l.c." de Damodaran). La herramienta del universo (solo ella; el motor no cambia) prueba ahora
   un nombre más tolerante y el país tras la última coma ("Ontario, Canada" → "Canada"): BP, RY, TD, ENB, CNQ y BN
   ganan industria (530/543, 97,6 %; siguen sin ella ARM, BABA, PDD, SE y las 9 altas recientes del S&P).

Rivales automáticos tras la revisión (capitalizaciones recapturadas, industria del golden de cada empresa):

| Ticker | Industria (región) | Rivales |
|---|---|---|
| AAPL | Computers/Peripherals (us) | DELL, SNDK, STX, WDC, HPE |
| JPM | Bank (Money Center) (us) | RY, BAC, TD, WFC, HSBC |
| O | Retail (REITs) (us) | SPG, KIM, REG, FRT, BRX |
| NEE | Power (us) | SO, CEG, DUK, AEP, VST |
| XOM | Oil/Gas (Integrated) (us; referencia global) | CVX, SHEL, TTE, **BP**, OXY |
| PLTR | Software (System & Application) (us) | ORCL, PANW, CRWD, CRM, NOW |
| RIVN | Auto & Truck (us) | F, GM, THO, HOG, LCID |
| BCS | Bank (Money Center) (**europe**, por nombre legal) | NU, FITB, ING, PNC, USB (los más cercanos por tamaño entre los del universo con capitalización; HSBC, SAN y BBVA quedan más lejos) |

Replay: BCS, XOM y JPM automáticos → `company` con su referencia; BAC, HSBC y SHEL `listo` (cifras del golden), el resto
`fallo` sin fixtures. Suite: `4240 passed, 1 skipped`; golden sin diferencias; `npm run check`, tsc y vitest (55) en verde.

**Propuestas (no hechas, cambian el análisis):** el mismo emparejamiento tolerante en `industry_bench.firm` (país tras la
coma y nombre sin sufijos) daría a RY, TD, ENB, CNQ, BN y BP su industria también en el análisis; y para BCS, preferir
rivales de la propia región a igual cercanía de tamaño.

## Encargos finales del PM (2026-10-17)

1. **Cobertura de los segmentos (dc3c4d2).** `segments.build` añade `concept_label` (tabla `market.segments.concept_labels`;
   si no cubren el total, `partial_concept_labels`: en banca, los ingresos de contratos con clientes son "Comisiones"),
   `coverage` (segmentos del último ejercicio / ingresos consolidados), `covers_total` (dentro de `reconcile_tolerance`),
   `coverage_source` y `coverage_note`. Total consolidado, por orden: el primero de `total_revenue_concepts` sin
   dimensión en la instancia; un total propio del emisor de `extension_total_concepts` no menor que los segmentos (los
   bancos NIIF no tienen elemento estándar: BCS publica `bcs:OperatingIncome`, £29,14 bn, etiquetado "Operating Income");
   el `revenue` de companyfacts. Resultado: **BCS "Comisiones · cubren el 38% de los ingresos consolidados"**
   (£11,11 bn / £29,14 bn); AAPL, NEE, XOM, PLTR y RIVN cubren el total; JPM 98 % (no cubre: Corporate fuera de los
   segmentos); O 95 %. Fixtures recapturados (replay idéntico en los 9). Tests: BCS real, total estándar más amplio,
   total propio con su salvaguarda y sin total.
2. **Rivales de la propia región (8c23341).** Dentro de la banda de tamaño `size_band_low`–`size_band_high` (1/3–3
   veces la capitalización), primero los de su región de Damodaran (columna nueva `damodaran_region` del universo) y
   después el resto por cercanía. Las capitalizaciones se piden en `lookup_order` (universo primero, su región delante):
   si no, el tope de 20 se gastaba en cotizaciones locales sin capitalización. **BCS: ING, BBVA, NU, FITB, PNC** (ING y
   BBVA europeos en banda; SAN queda justo fuera, 3,03 veces; HSBC, 4,22 veces). Los demás: AAPL DELL, SNDK, STX, WDC,
   HPE; JPM BAC, RY, TD, WFC, HSBC; XOM CVX, SHEL, TTE, BP, OXY; O, NEE, PLTR y RIVN como antes.
3. **Motor (af0d302, commit propio).** `industry_bench.lenient_name` / `country_key` y el emparejamiento tolerante en
   `firm`, solo con coincidencia única; la herramienta del universo usa la misma función. Golden **sin diferencias** en
   panel y local (no se regeneró nada). Fuera del juego, solo BP cambia el texto de su clasificación (misma industria y
   veredicto). Detalle: `docs/fiabilidad/GOLDEN_DIFF_E2B.md`. Aprobado por el PM por delegación del usuario ("recuerda,
   que esto se autoapruebe. confío plenamente en ti").

Verificación final: `4254 passed, 1 skipped`; `diff_golden` panel y local sin diferencias; `npm run check`, tsc y
vitest en verde; `grep token=` vacío.

## Avisos para E3/E4 (no son de E2b)

- `dropped_axes` ya existe (revisión del PM). Los ejes con los mismos miembros que otro ya mostrado se omiten sin más.
- BCS: el desglose es de comisiones; la respuesta ya lo dice (`concept_label`, `coverage`, `coverage_note`): E3 solo
  tiene que mostrarlo.
- El plan de E3 (Task 8) pide una columna "crecimiento de ingresos" en la tabla de rivales: `summary.metrics` solo trae
  las claves de `display.charts.comparison` (P/E, P/B, EV/EBITDA, ROE, ROIC, márgenes, D/E, cobertura; según el tipo de
  empresa) más `market_cap`. Sin cambio, esa columna saldrá "Sin dato".
