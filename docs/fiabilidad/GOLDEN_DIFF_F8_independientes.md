# GOLDEN_DIFF · F8 correcciones independientes (auditoría externa del 26-oct-2026)

Cambios de los golden de la rama `fiabilidad/f8-independientes`, por corrección, con su causa y su justificación
financiera. Aquí **se esperan cambios de veredicto**: cada uno tiene causa (E3, E6, E10, historia, BRK-B). Evidencia y
arreglo: `F8_INDEPENDIENTES_REGISTRO.md`.

## E3 · FFO según Nareit

Solo cambian los REIT (industria «REIT - …»): local O; panel O, PLD y AMT. Ningún otro golden cambia.

| Golden | Precio | Calidad | Veredicto antes → ahora | P/FFO |
|---|---|---|---|---|
| panel/PLD | 50 razonable → **40 exigente** | 79 → 75 sólida | Calidad sólida · precio razonable → **Calidad sólida · precio exigente** (confianza alta) | 17,9x → 20,6x |
| panel/O | 61 razonable → **75 atractivo** | 59 media → **65 sólida** | Calidad media · precio razonable (confianza media) → **Calidad sólida · precio atractivo (confianza alta)** | 13,7x → 13,1x |
| panel/AMT | 61 → 54 razonable | 75 → 71 sólida | sin cambio de nivel (confianza media; el DCF inverso pasa de «en precio» a «cara») | 15,3x → 15,0x |
| local/O | 61 razonable (=) | 59 media → 65 sólida | Calidad media → **Calidad sólida** · precio razonable; P/FFO **sin dato** | 13,5x → sin dato |

**Causa y justificación:**

- **PLD:** el FFO baja de 6.940 a 6.035 millones (TTM al 2T-2026), al restar 905 millones de ganancias por venta de
  inversiones inmobiliarias que PLD realiza cada año y que Nareit excluye. Queda a −6,4 % del FFO Nareit que publica
  (6.449) y a +3,9 % de su Core FFO (5.809); antes estaba a +7,6 % y +19,5 %. Con un P/FFO de 20,6x (umbral «caro»: 20x)
  el precio pasa a «exigente», que es lo que ve el mercado con el Core FFO (unas 21x). La auditoría lo anticipaba
  (P/FFO real de unas 21x, no 17,7x). Rentabilidad: el FFO/activos baja de 6,87 % a 5,97 % («bajo», −3).
- **O:** el FFO sube de 3.810 a 3.975 millones: sus deterioros de inmuebles (356) superan a sus ventas (190), y Nareit
  suma los primeros y resta las segundas. Queda a **+0,5 %** del FFO que publica O (3.957); antes estaba a −3,7 %. El
  FFO por acción de 2023–2025 crece +3,6 % anual en lugar de −0,1 % (los deterioros de 2024–2025, 426 y 471 millones,
  deprimían el FFO antiguo): el crecimiento por acción y el retorno total suben, el DCF inverso pasa de «en precio» a
  «barata» y coincide con los múltiplos (confianza alta). Precio «atractivo» con P/FFO 13,1x.
- **AMT:** el FFO sube un 1,5 % (suma 83 millones de deterioros y pérdidas por venta); la serie anual cambia por los
  deterioros de cada año (su CAGR por acción a 3 años pasa a −7,1 %: el DCF inverso la ve cara). El nivel no cambia.
- **local/O:** el juego `local` se capturó **sin clave de Finnhub**, así que no hay estado presentado del que sacar los
  ajustes: el FFO Nareit es «sin dato» («sin clave de Finnhub: no se puede leer el estado de flujos que presentó el
  emisor») y no puntúa (P/FFO, payout sobre FFO, FFO/activos, retorno total). Es el comportamiento correcto sin la
  fuente: el FFO antiguo no era el de Nareit. La calidad sube porque las categorías se reescalan sobre los componentes
  con dato (regla de cobertura, que no es de esta rama). En producción Finnhub participa.

**PDF y web:** filas nuevas «FFO según Nareit (por acción)» y «AFFO (por acción)» en la tabla de múltiplos del REIT, con
la fórmula y las cifras; el texto del crecimiento por acción dice la definición nueva.

**Pendiente de la fusión:** los fixtures del frontend (`frontend/src/v2/__fixtures__/O.json`) salen del replay del
panel (`frontend/scripts/export-v2-fixtures.mjs`) y llevan aún el FFO antiguo; se regeneran al fusionar.

### E3 bis · participadas materiales → FFO «sin dato» (decisión del 27-oct-2026)

| Golden | Cambio |
|---|---|
| local/O | Solo texto: el P/FFO y el payout sobre FFO de la portada (sin dato) dicen por qué: «FFO según Nareit sin dato: sin clave de Finnhub…». Sin cambio de cifras ni de veredicto. |
| panel O, PLD, AMT | Sin cambios (participadas: O 0,3 %, PLD 7,8 %, AMT 0 %; umbral 10 %). |

**Fuera de los golden (análisis en vivo):** SPG (participadas 12,7 % del FFO calculado) pasa a FFO «sin dato» y el
P/FFO deja de puntuar: precio 25 «muy exigente» (confianza alta) → 39 «exigente» (confianza media, un solo método
evaluable). **Causa:** su FFO calculado quedaba un 25 % por debajo del que publica, porque no puede sumar la parte de
la D&A de sus participadas. Un P/FFO de 22,9x sobre ese FFO lo hacía parecer caro sin serlo.

## E6 · Frescura de los estados

Todos los golden con EDGAR ganan `data_provenance.staleness` («al_dia» y los días desde el corte; MC.PA «sin_dato»).
Cambian de verdad cuatro del panel, los que EDGAR ya tenía con un periodo posterior en la fecha de captura:

| Golden | Corte → periodo en EDGAR | Días | Cobertura | Confianza (nivel) |
|---|---|---:|---|---|
| panel/AMZN | 31-mar-2026 → 10-Q 30-jun-2026 | 197 | alta → **media** | alta (=), puntuación 1,0 → 0,9 |
| panel/BAC | 31-mar-2026 → 10-Q 30-jun-2026 | 197 | alta → **media** | = (puntuación 0,6 → 0,5) |
| panel/MU | 31-may-2026 → 10-K 3-sep-2026 | 136 | alta → **media** | media (=); el techo deja de ser por estabilidad, porque sin él ya sería media |
| panel/UL | 31-dic-2025 → 6-K (XBRL) 30-jun-2026 | 288 | alta → **media** | = (puntuación 0,7 → 0,6) |

**Causa:** el análisis usa estados de un periodo anterior al último que el emisor ya presentó en la SEC (auditoría
§E6). El aviso de la portada y del PDF pasa de «la empresa publicó resultados…» a «Estados desfasados: …». **Ningún
veredicto cambia de nivel.** La regla de confianza es de E11: AMZN sigue en confianza «alta» con la cobertura media.

## E10 · Altman por SIC

Todos los golden con EDGAR ganan `altman_z.model_basis` (el SIC y si es manufactura; sin la descripción de EDGAR,
que está en inglés) y la frase «Variante elegida…» en la tarjeta. MC.PA: «por sector (sin SIC)». Cambio de variante sin cambio de zona ni de puntos: KO, PG, JNJ, MU, NVDA,
TSM, ASML, NVO y UL (Z'' → Z original, todas en zona segura). Cambios de puntuación:

| Golden | Variante y Z | Solidez | Calidad | Veredicto |
|---|---|---|---|---|
| panel/AAPL | Z'' 2,32 gris → Z 13,27 segura (SIC 3571) | 10 → 20 | 75 → 87 | sólida → **excelente** · precio muy exigente |
| panel/SHEL | Z 2,53 gris → Z'' 3,23 segura (SIC 1311) | 11 → 19 | 76 → 86 | sólida → **excelente** · precio atractivo |
| panel/TM | Z'' 2,67 segura → Z 1,59 riesgo (SIC 3711) | 19 → 7 | 70 → 55 | sólida → **media** · precio exigente |
| panel/FCX, local/FCX | Z 3,29 / 3,42 segura → Z'' 2,46 gris (SIC 1000) | 20 → 17 | 72 → 69 | = (sólida) |

**Causa:** la variante sale del SIC (manufacturas 2000–3999 → Z original), la muestra con la que Altman calibró cada
modelo, y no del sector de Yahoo (auditoría §E10).
- **AAPL:** el Z'' usaba su patrimonio contable, deprimido por las recompras; el Z original usa la capitalización.
- **SHEL y FCX** (extracción y minería) no son manufacturas.
- **TM:** el Z original lee la financiera cautiva consolidada como pasivo industrial. Es un límite conocido del modelo,
  pendiente de decisión del PM (registro §E10).

Ningún golden tiene un emisor excluido por SIC que no fuera ya «no aplica» por arquetipo (utilities, REIT y
financieras). Los excluidos nuevos se comprueban en vivo (KMI y UNH) y con tests.

## Historia de 10 años en cascada

Todos los golden con EDGAR ganan `history_10y.field_reasons` y `history_10y.relays`. Los fixtures del juego f2b ganan
los hechos de los conceptos de relevo presentados hasta su captura (`tests/capture_history_relay_f8.py`). Cambios:

| Golden | Cambio | Causa |
|---|---|---|
| panel/SHEL | BPA diluido 0 → 10 ejercicios. Crecimiento 12 → 16, calidad 86 → 91 (excelente, =) | BPA de continuadas validado por identidad. **Ojo:** el BPA de ciclo medio (+52,3 %) sale de un método que toma el BPA en picos de ingresos (2015, BPA hundido): seguimiento para el PM (registro §historia). |
| panel/TM | Resultado operativo y beneficio de 2016–2019 desde US GAAP (verificado en el FY2020). Persistencia de Calidad de ganancias 0,2 → 0,6 | Sin capex en la SEC, la prueba del FCF no se hace (antes contaba como «no cumple»). |
| panel/JNJ | Calidad 86 → 85 (excelente, =) | Sin resultado operativo en la SEC desde 2014: Rentabilidad persiste con el margen neto (antes, con el de Yahoo). |
| panel/NEE | Persistencia de Calidad de ganancias 0,6 → 1,0 | Capex con conceptos propios: sin la prueba del FCF. |
| panel/O, XOM, SHEL, DOW | Ancla de Rentabilidad: margen operativo (Yahoo) → margen neto (SEC) | El emisor no presenta un resultado operativo estándar. DOW: el margen neto del último ejercicio es negativo, así que persistencia 0 (su calidad no llega a 80: no cambia). |
| panel/FCX, local/FCX | BPA: relevo de continuadas declarado | Ejercicios en los que cuadra con beneficio / acciones. |
| resto (JPM, BAC, PGR, V, BRK-B, local JPM, O, V) | Solo los motivos de lo que falta en la ficha | — |

Ningún veredicto cambia de nivel.

## E10 bis · financiera cautiva → Altman referencial (decisión del PM, 27-oct-2026)

Todos los golden con el Altman aplicable ganan `business_model.captive_finance`.

| Golden | Cambio | Causa |
|---|---|---|
| panel/TM | Altman referencial (Z 1,59 ya no puntúa). Solidez 7 → 13, calidad 55 → 62 (media, =) | Segmento «Financial Services Business», el 9,7 % de los ingresos (20-F). |
| panel/CAT | Altman referencial (Z 4,88 ya no puntúa). Solidez 20 → 15, calidad 84 → 78: **excelente → sólida** · precio muy exigente | Cat Financial en la deuda del XBRL y segmento «Financial Products», el 6,2 %. |
| panel/NFLX, MC.PA, local/NFLX | Solo texto: el Altman declara el límite (sin segmentos) | Opción (a). |

**Justificación:** el Z mide el riesgo de insolvencia con el pasivo total. En un fabricante que consolida su financiera,
ese pasivo incluye la deuda con la que financia a sus clientes, que no es apalancamiento industrial. CAT pierde los +6
del Z en zona segura y TM deja de restar −6 por una zona de riesgo que no es real. AAPL, SHEL y FCX no cambian.

## BPA de ciclo medio entre las medias de las dos mitades del ciclo

| Golden | BPA de ciclo medio | Crecimiento | Calidad (nivel) |
|---|---|---|---|
| panel/SHEL | +52,3 % → +9,2 % | 16 → 12 | 91 → 86 (excelente, =) |
| panel/MU | +17,7 % → +3,5 % | 16 → 12 | 90 → 87 (excelente, =) |
| panel/XOM | +7,2 % → −1,4 % | 10 → 8 | 82 → 80 (excelente, =; justo en el umbral) |
| panel/CAT | +6,0 % → −1,4 % | 10 → 8 | 78 → 75 (sólida, =) |
| panel/FCX, local/FCX | −13,2 % → sin tasa (BPA medio negativo en 2015–2018); la fila sale «Sin dato» con el motivo | = | = |
| panel/TM | — | = | = (solo la fila del BPA a 3 años, «Sin dato» con su motivo, que antes no se mostraba) |

**Causa:** el BPA se leía en los dos años de pico de ingresos, que pueden ser valles del BPA (SHEL 2015: 0,30 $) o
quedar en extremos del ciclo (MU: 2,47 $ en 2015 frente a 7,75 $ en 2022). Ahora es la media de cada mitad del ciclo, pérdidas incluidas. El BPA de ciclo medio de
estas cíclicas crece menos de lo que decían dos años sueltos. Ningún veredicto cambia de nivel.

## Fusión en `rediseno/v4-f8` (27-oct-2026)

- `rediseno/v4` (f9158ee4) + `fiabilidad/f8-independientes` (c6afa796), **sin conflictos**.
- **Golden:** los fusionados coinciden exactamente con lo que produce el código fusionado (`diff_golden` local y panel y
  `pdf_v2_golden`: sin diferencias). No hay interacción entre las dos ramas, así que no aparece ningún cambio sin causa.
- **Fixtures del frontend** (`src/v2/__fixtures__`, 8 tickers): regenerados desde el replay del panel. Son **idénticos
  campo a campo** a los golden del panel; sus cambios son los de las secciones anteriores.
- **Tests del frontend que fijaban cifras:**
  - AAPL: solidez 10 → 20 y calidad 75 → 87 (E10).
  - La línea de contracción del precio se prueba con BCS, la misma frase, porque O pasó a confianza alta (E3).
- **e2e:v2, un fallo con causa conocida, corregido después (decisión del PM): ver la sección siguiente.**

## V4-F8 · la cabecera resume y la sección detalla (decisión del PM, 27-oct-2026)

**Diagnóstico corregido.** El primer diagnóstico (la nota de persistencia alarga la cabecera) era erróneo: en el
teléfono la cabecera no pinta el texto base de las tarjetas. Medido en el iPhone (WebKit), el título de «La empresa» de
AAPL baja de 650 px con los datos de la v4 a 698 px con los fusionados, +48 px que salen de las palabras de nivel más
largas:
- **+30 px:** el veredicto «Calidad excelente · precio muy exigente» mide 363 px a 19 px de letra frente a 361 px
  disponibles, así que pasa a dos líneas («Calidad sólida · …» cabía en una).
- **+18 px:** «87 / 100 · excelente» no deja sitio al título «CALIDAD DEL NEGOCIO», que pasa a dos líneas. Con «muy
  exigente», el precio ya estaba en dos líneas en la v4.

**Arreglo:**
- **CSS del teléfono, solo en la cabecera** (`v2.css`), para que aguante el peor caso:
  - el veredicto a la letra de lectura (17 px; el más largo mide 325 px);
  - «/ 100 · nivel» a 14 px;
  - el hueco entre título y cifra, de 12 a 8 px.
  - Nada baja de 12 px (medido: mínimo 12 px en la cabecera, en el iPhone, el Pixel y el iPad).
- **Notas en forma corta (genérico, como pidió el PM):** cada nota de una puntuación tiene su forma corta
  (`cover.quality.note_short`, `cover.price.note_short`) para la cabecera, y la frase completa (`note`) sigue en el
  desglose de «La empresa».
  - Persistencia: «Exige persistencia (88 → 87)».
  - Frontera: «En la frontera con «media» (a 1 punto)».
  - Baja confianza: «Baja confianza: cobertura baja en Crecimiento».
  - Ajuste: «Ajustado de 45 a 46 por confianza media».
  - Las piezas se unen con « · ». En el escritorio la cabecera pinta la corta; en el teléfono no pinta ninguna.
  - En `lib/prose.py` se declara como «titular» (línea de cabecera sin punto final, como el veredicto).
- **Golden:** todos ganan `note_short` en `display.cover.quality` y `display.cover.price`. No cambia nada más y los PDF
  no cambian. Los fixtures del frontend se han regenerado.

**Resultado medido** (título de «La empresa» en la primera pantalla, 8 tickers del replay): iPhone 15, como mucho
647 px de 659; Pixel 7, 676 de 812; iPad Mini, 686 de 1.024.

**Tests:**
- `backend/tests/test_note_short.py`: piezas cortas; AAPL corta en la cabecera y completa en la sección; la corta
  existe si y solo si existe la completa, y nunca es más larga.
- `CompanyHeader.test.tsx`: la cabecera dice «Exige persistencia (88 → 87)» y el desglose, la frase completa.
