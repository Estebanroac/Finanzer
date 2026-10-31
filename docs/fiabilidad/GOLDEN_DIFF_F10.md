# GOLDEN_DIFF_F10: cambios de golden de F10 y su causa

Ronda F10: la revisión externa del informe de NVIDIA (`revision-nvda-2026-10-28.md`, plan
`docs/superpowers/plans/2026-10-28-fiabilidad-revision-nvda.md`). Rama `fiabilidad/f10-motor`, que sale de
`rediseno/v4-f8` en e20de9f8, y `fiabilidad/f10-presentacion` (N5 y N6, al final). Un commit por hallazgo. Las dos
se fusionaron en la v4: la presentación en ccacd828 y el motor encima (sección «Fusión del motor en la v4»).

Evidencia en vivo (`tools/f8_evidencia.py`): NVDA, las 26 de la auditoría, NU y BRK-B, en
`docs/fiabilidad/f8_evidencia/f10_*`. El «antes» es `f10_antes` (e20de9f8).

## N1 · Ganancias no operativas en el beneficio normalizado

**Verificado en EDGAR (companyfacts de NVDA).** La partida es `GainLossOnInvestments`: las ganancias de las
inversiones de NVIDIA en acciones, cotizadas y no cotizadas.

| Trimestre | Ganancias en inversiones | Qué hacía el motor |
|---|---|---|
| Abril de 2026 | 15,94 B$ | Las dejaba en el beneficio normalizado: estaban en `OtherNonoperatingIncomeExpense` y Yahoo no las marca como inusuales |
| Julio de 2026 | 7,77 B$ | Las quitaba: Yahoo sí las marca («Total Unusual Items») |

Sin ese ajuste, en el TTM a julio de 2026:

- el beneficio antes de impuestos (229,7 B$) supera en 30,4 B$ a operativo (197,6) + financieros netos (+1,8);
- el normalizado se quedaba en 186,4 B$;
- el pico de abril se infería (z robusto 3,9), pero no se aplicaba por debajo de `one_off_pct`.

**Regla** (`lib/normalize.coherence`; config `[thresholds.normalization] nonoperating_tolerance_revenue = 0.02`):

- **Qué se mide:** no operativo = beneficio antes de impuestos − (operativo + financieros netos + participadas por
  puesta en equivalencia).
- **Qué sale:** lo que pasa del 2 % de los ingresos, descontadas las ganancias ya normalizadas por otras filas, neto al
  tipo efectivo acotado a [0, 35 %]. Sale del beneficio que puntúa (P/E normalizado, ROE, ROA y margen neto) como una
  partida más, de tipo «coherencia» y confianza alta, con su cifra y su fórmula en la nota de normalización.
- **Es la regla del PM** (beneficio frente a (operativo + financieros netos) × (1 − t)), aplicada al beneficio
  continuado antes de minoritarios. En la primera versión, sobre el beneficio neto, los créditos fiscales y la parte de
  los minoritarios de NEE (tipo efectivo negativo) y las operaciones discontinuadas de UL (la escisión de los helados)
  salían como «ganancias no operativas»: falsos positivos y etiqueta falsa. Antes de impuestos, minoritarios y
  discontinuadas, desaparecen.
- **Continua:** sale solo lo que pasa de la tolerancia (test).
- **Las participadas cuentan como operación:** KO y sus embotelladoras, recurrentes.
- **No se aplica:**
  - con partidas estructurales: aseguradoras y conglomerados como BRK-B, cuya cartera ya sale entera;
  - donde el margen operativo no aplica (`not_applicable(…, "operating_margin")`): bancos, aseguradoras y REIT.

**Comprobado en vivo** (`f10_antes` → `f10_n1`):

| Empresa | Sale | Efecto |
|---|---|---|
| NVDA | 13,91 B$ (30,4 no operativos − 7,77 ya normalizados − 6,06 de tolerancia, al 16,0 %) | P/E normalizado 28,4x → 30,6x (el revisor estimaba ≈ 31x); margen neto normalizado 57 %. Sin cambio de nivel: los votos del precio son N2–N4 |
| NEE | 0,60 B$ (ganancias de los fondos de desmantelamiento nuclear, ventas de negocios y otros ingresos no operativos por encima de la tolerancia) | P/E normalizado 14,7x → 15,5x; sin cambio de nivel |
| BA | 2,13 B$ (la ganancia de la venta de un negocio) | Sin calidad ni precio: no cambia nada que puntúe |
| MSFT | 0,04 B$ | — |
| UNP | 0,02 B$ | Muestra un P/E normalizado casi igual al reportado |
| GOOGL, AMZN | 0 | Yahoo ya marca sus ganancias como inusuales (GOOGL 148,8 B$ en bruto; AMZN, Anthropic) y salían |
| ASML, LLY, WMT, KO | 0 | Dentro de la tolerancia |
| BRK-B | 0 | No se mira: partida estructural, sin resultado operativo en Yahoo |

- **KO cambia por otra causa:** precio 30 → 35 y confianza alta → media. Entre las dos corridas, EDGAR recibió el 10-Q
  de KO del trimestre cerrado el 2-oct-2026, y la regla de estados desfasados (F8 · E6) acota la cobertura. Es un dato
  nuevo, no N1.

**Golden.**

- Todos llevan el bloque de diagnóstico nuevo `earnings_normalization.coherence`: `null` donde no se mira, y si no,
  con sus piezas.
- Cambian cifras en cuatro del panel:
  - **NVDA:** normalizado 186,4 → 172,5 B$; P/E normalizado 28,95x → 31,29x.
  - **NEE** (el panel tiene otra fecha): 0,61 B$ fuera; P/E normalizado 18,1x → 19,4x. El P/E pasa de «atractivo» a
    «en línea» (+3 → 0) y el forward pasa de 0 a +1. Calidad y precio, sin cambio de nivel.
  - **PLTR:** 0,05 B$ (intereses y otros ingresos por encima de la tolerancia); ROE, ROA y margen neto pasan a
    «normalizados» (30,9 % → 30,4 %).
  - **MSFT:** 0,04 B$; P/E normalizado 30,41x → 30,42x.
- Fixtures de /v2: NEE y PLTR con esas cifras; los demás, solo el bloque de diagnóstico.

## N3 · PEG con el crecimiento del BPA desde un año valle

**Verificado.** El crecimiento del BPA ya usaba el mismo método que los ingresos (`historical_metrics.growth_rate`:
CAGR, o regresión log-lineal si el año base es anómalo).

- **El problema en NVDA:** el BPA diluido de FY2023 (0,17) es el 6 % de la mediana de los demás, así que la regresión
  se aplica, pero sobre los 4 únicos ejercicios de la ventana, uno de ellos el anómalo. Da 198 % (el CAGR, 204 %),
  y el PEG queda en 0,14, «muy atractivo» (+1 en el bloque de múltiplos).
- **Sin ejercicios fuera de la ventana**, la regresión no tiene con qué diluir el año anómalo y no es una alternativa
  robusta. Sin FY2023, la regresión daría 103 %.

**Regla.**

- `growth_rate` dice si la regresión tuvo ejercicios más allá de la ventana (`robust`).
- En GROWTH_PROFITABLE, con año base anómalo y sin esos ejercicios, el PEG a 3 años es «no significativo»:
  - no puntúa (cobertura «no significativo», como en F8 · E4);
  - no entra en la convergencia;
  - la tabla dice por qué, con el crecimiento y el año base.
- Con más ejercicios, la regresión es la alternativa y el PEG se calcula con ella.
- El crecimiento que proponía el revisor (el de consenso) no se usa: F3 · T6 decidió que el PEG de GROWTH_PROFITABLE es
  el de 3 años, no el de consenso.

**Comprobado en vivo** (`f10_n1` → `f10_n3`):

- **NVDA:** PEG 0,14 → n.s. Sin su +1, el precio bruto pasa de 65 a 60, y con Ke − 1 pp ya no cruza a «atractivo»: el
  veredicto deja de depender de Ke, la confianza sube de baja a media y la calidad deja de contraerse hacia 50
  (87 → 93). La convergencia no cambia: es media en las dos corridas. El precio, igual (58, razonable): 65 contraído
  con baja y 60 contraído con media dan lo mismo. *Corregido en el commit de N4: la primera redacción atribuía la
  subida a la convergencia.*
- **MSFT, LLY y GOOGL:** sin año base anómalo; su PEG no cambia.
- **FCX** cambia de nivel por otra causa: su precio pasó de 65,62 a 66,18 $ entre las dos corridas, y el P/E cruzó un
  tramo.

**Golden.** Solo NVDA: PEG 0,1413 → n.s.; el bloque de múltiplos pasa de +0,40 (5 múltiplos) a +0,25 (4); sin cambio
de nivel en el panel.

## N4 · Votos correlacionados en el bloque de múltiplos y tasas base

### Familia del BPA

**Regla** (`financial_ratios.multiples_block`; config `[thresholds.score.valoracion] multiples_earnings_family =
["P/E", "Forward P/E", "PEG"]`):

- **Por qué son una familia:** los tres dividen el mismo precio por el mismo BPA (el de doce meses, el esperado o su
  crecimiento). Un salto del BPA los mueve a la vez: en NVDA daban +1, +1 y +1, tres de cinco votos.
- **Qué cambia:** en el bloque cuentan como un voto, la media de los que tengan dato.
- **El máximo sale de los votos,** con la misma tabla de antes (`multiples_block_max_by_members`: ±2 con 1, ±4 con 2,
  ±6 con 3 o más).
- **Es la regla más simple que se puede justificar:**
  - no pondera ni toma el extremo;
  - no añade umbrales: solo dice qué múltiplos comparten numerador y denominador;
  - cada lectura sigue visible en la tabla y en el motivo del bloque («BPA (P/E, Forward P/E, PEG): P/E −0,50,
    Forward P/E +0,67, PEG +0,00 → +0,06; …»).
- **Lo que no toca:** los ajustes de cada múltiplo y el DCF; la convergencia sigue leyendo cada lectura.

### Tasas base

**Regla** (`valuation_confidence.verdict_confidence`; config `[thresholds.confidence] base_rate_min_share = 0.05`):

- **Cuándo actúa:** el DCF inverso exige un crecimiento que, según las tasas base de Mauboussin y Callahan, sostuvo
  menos del 5 % de las comparables.
- **Qué hace:** la confianza visible baja un escalón, con su motivo: «un escalón menos por las tasas base: el precio
  exige un 23.2% anual 10 años, que sostuvo el 0.06% de las comparables (< 5%)». Desde baja no puede bajar más, y el
  motivo lo dice.
- **Decisión del PM (opción a):**
  - el precio y la calidad se contraen con la confianza previa al escalón, que se guarda en
    `confidence.contraction_basis`;
  - hay una sola confianza a la vista;
  - la nota del precio dice «ajustado de 15 a 10 hacia 50 (las tasas base no lo mueven)».
- **Por qué:** contraer con la confianza rebajada acercaría a 50 justo los precios que exigen un crecimiento casi
  imposible y los haría más atractivos. Era el efecto perverso de la opción b.
- **El test** `test_base_rate_step_does_not_move_price_or_quality` fija AAPL, MSFT y AMZN en el panel: bajan un
  escalón y su precio y su calidad son los de `contraction_basis`.
- **Lo que no cambia:** el escalón de Ke (veredicto dependiente de Ke ± 1 pp) sigue bajando las dos, la visible y la de
  contraer, porque es incertidumbre del propio precio.

### TSM, de 28 a 10 (panel): el salto lo explica la familia

| Paso | Antes | Con N4 |
|---|---|---|
| Lecturas (±1) | P/E −0,50 · Forward P/E +0,67 · PEG 0,00 · P/FCF −1 · EV/EBITDA −1 | Las mismas |
| Votos del bloque | 5, media −0,37 | 3: BPA +0,06 · P/FCF −1 · EV/EBITDA −1, media −0,65 |
| Bloque (máx. ±6) | −2,2 → −2 | −3,9 → −4 |
| Valoración (/20) | 4 | 2 |
| Precio bruto | 20 | 10 |
| Con Ke − 1 pp | 30, «exigente»: cruza el nivel, dependiente de Ke | 20, «muy exigente»: no lo cruza |
| Confianza con la que contrae | media (alta − el escalón de Ke) | alta |
| Contracción hacia 50 | 50 + (20 − 50) × 0,75 = 27,5 → **28** | × 1,0 → **10** |
| Tasas base (0,06 % de las comparables) | — | La confianza visible pasa de alta a media; no contrae |
| A la vista | 28, muy exigente, confianza media | 10, muy exigente, confianza media |

Diez puntos del salto son el bruto: la familia pasa de tres votos a uno. Los otros ocho son la contracción que
desaparece: con el bruto en 10, el veredicto deja de estar en la frontera de Ke. Las dos cosas salen de la familia; las
tasas base solo cambian la confianza visible.

### NVDA: los dos efectos sobre la confianza, por separado

| Corrida (en vivo) | Precio bruto → visible | Convergencia | Confianza visible | Contrae con | Por qué |
|---|---|---|---|---|---|
| `f10_n1` | 65 → 58 | media | baja | baja | Dependiente de Ke: con Ke − 1 pp pasa a «atractivo» |
| `f10_n3` | 60 → 58 | media | **media** (sube N3) | media | PEG n.s.: el bruto baja y deja la frontera de Ke |
| `f10_n4` | 55 → 55 | **alta** | **media** (baja N4) | **alta** | La familia: el bloque deja de llevar la contraria al DCF (convergencia alta, confianza alta), y las tasas base (0,16 %) bajan la visible a media |

- **N3 sube** la confianza un escalón: de baja a media.
- **La familia de N4 sube otro:** la confianza con la que contrae pasa de media a alta, y el precio ya no se contrae.
- **Las tasas base de N4 bajan** la visible un escalón, de alta a media, y no tocan el precio.
- **En el panel,** igual: la confianza visible es media antes y después, pero ahora contrae con alta. El precio pasa de
  58 a 50 (bruto 60 → 50).

### Comprobado en vivo (`f10_n3` → `f10_n4`)

| Empresa | Precio | Confianza visible (contrae con) | Causa |
|---|---|---|---|
| NVDA | 58 → 55 | media → media (alta) | Lo de arriba |
| MSFT | 35 → 31 | media → baja (media) | Familia (bloque 0 → −1); tasas base 0,05 % |
| LLY | 39 → 38 | media → baja (baja) | Familia (bloque −2 → −4: bruto 35 → 25, ya en la frontera de Ke); tasas base 0,22 % |
| JPM | 42 → 35 | media → **alta** (alta) | Familia (bloque +1 → 0: bruto 40 → 35); con Ke − 1 pp ya no pasa a «razonable», así que deja de depender de Ke y no contrae |
| AMZN | 35 → 31 | media → baja (media) | Familia (bloque 0 → −1); tasas base 0,29 % |
| GOOGL | 39 → **28, muy exigente** | media → baja (media) | Familia: el BPA (+0,67) eran tres de cinco votos frente a P/FCF −1 y EV/EBITDA −0,5; bloque +1 → −2. Tasas base 0,00 % |
| WMT | 15 → 10 | alta → media (alta) | Familia (bloque −3 → −4); tasas base 0,20 % |
| LIN | 10 → 10 | alta → media (alta) | Tasas base 1,14 % |
| SAP | 31 → **28, muy exigente** | media → media (media) | Familia (bloque −1 → −2) |
| KO | 35 → 31 | media → media | Familia (bloque −2 → −3) |
| MCD | 48 → 45 | baja → baja | Familia (bloque +3 → +2) |
| UNP | 10 → 15 | alta → alta | Familia: el BPA (−0,67) ya no pesa por tres; bloque −4 → −3 |
| VZ | 45 → 48 | baja → baja | Familia (bloque −1 → 0) |
| NU | 20 → 25 | alta → alta | Solo tiene la familia (−0,50): un voto, máximo ±2; bloque −2 → −1 |
| ASML | 35 → 35 | baja → baja | Tasas base 0,18 %: ya era baja |

- **Sin cambio:** UNH, CB, XOM, KMI, NEE, AWK, PLD, O, FCX, MRNA, BA y BRK-B.
- **CAT,** al 5,41 %, no llega al escalón; en el panel, al 4,84 %, sí, pero ya era baja.

### Golden

- **Todos llevan dos campos nuevos:**
  - `confidence.contraction_basis` y `confidence.base_rate_step`;
  - en el bloque de múltiplos, `block_votes` y el motivo y la fórmula con la familia.
- **Cambian de cifra en el panel:**
  - **Por la familia:** AAPL, BAC, BCS, BRK-B, JNJ, JPM, KO, MSFT, NEE, NVDA, NVO, PLTR y TSM.
    - JPM deja de depender de Ke: confianza media → alta, precio 42 → 35.
    - KO pasa a depender de Ke: confianza alta → media, precio 30 → 31; el bruto baja de 30 a 25 y la contracción lo
      sube a 31.
    - BRK-B pasa a depender de Ke, pero ya era baja.
  - **Escalón de las tasas base** (solo la confianza visible):
    - AAPL alta → media (1,60 %);
    - AMZN media → baja (0,32 %);
    - MSFT media → baja (0,05 %);
    - NVDA alta → media (0,14 %);
    - PLTR alta → media (0,13 %);
    - TSM alta → media (0,06 %);
    - ASML (0,19 %) y CAT (4,84 %): ya eran baja.
  - **Ningún nivel de precio cambia en el panel,** ni ninguna calidad.
- **Local:** JPM, igual que en el panel. FCX, NFLX, O, SNOW y V solo llevan los campos nuevos.
- **Forzados:** solo los campos nuevos.
- **Fixtures de /v2:** reexportados.
- **Dos tests de /v2 (de E3) siguen a los datos:**
  - `src/v2/lib/confidence.test.ts`: NEE contrae de 40 a 45 (antes, de 45 a 48); BCS de 55 a 54 (antes, de 60 a 58);
  - `src/v2/components/CompanyHeader.test.tsx`: el bloque de AAPL pasa de −3 a −4.
- **Tests del motor que siguen a los datos o a la regla:**
  - `invariants` y `guardian`: la contracción usa `contraction_basis`, y el máximo del bloque sale de los votos;
  - `test_quality_price` y `test_cost_of_capital`: MSFT contrae con media;
  - `test_f8_referencia`;
  - `test_coverage`: Valoración 10 → 11 en el caso sintético;
  - `test_pdf_v2_report`: la frase «el DCF directo y los múltiplos coinciden» pasa de KO a JNJ, porque KO ahora depende
    de Ke y su frase de confianza es otra.

## N2 · La referencia de la industria nunca incluye a la propia empresa

**Hallazgo.** NVIDIA era el 58 % de la capitalización de los semiconductores de EE. UU. en el conjunto de Damodaran
(5-ene-2026). Compararla con ese agregado era, en buena parte, compararla consigo misma.

**No le pasa solo a NVIDIA.** Peso a la fecha del conjunto:
- AAPL el 91 %, GOOGL el 69 %, AMZN el 63 %, CB el 61 %, MSFT el 50 % y KO el 45 %;
- casi todas las grandes pesan mucho en su agregado.

Por eso es una regla continua y sin umbral (decisión del PM, que además es la regla del modelo general).

**Regla** (`lib/self_exclusion.py`, `lib/industry_bench._self`):

1. **Cifras de la empresa a la fecha del conjunto** (`industries.dollar_as_of`):
   - doce meses que acaban en el último periodo presentado en SEC EDGAR a esa fecha, a la moneda del precio con el
     tipo medio de esos doce meses;
   - balance de Yahoo de ese trimestre o ejercicio;
   - capitalización de ese día = cierre × acciones de la clase que cotiza × acciones de entonces / acciones de hoy.
2. **Sin cifras en tres casos:**
   - cotiza en otra moneda que USD (los totales de Damodaran son en USD): MC.PA;
   - sin EDGAR;
   - doce meses que acaban más de `stale_coverage_days` + `report_date_tolerance_days` (114 días) antes. Es la regla de
     estados desfasados de F8 · E6, con la tolerancia de cierres de 52/53 semanas (KO, al 26-sep). Un emisor con 20-F
     solo tiene en XBRL su ejercicio: SAP salía con el de 2024 (reestructuración) y una referencia de 15,5x.
3. **Totales de la industria:** `Dollar{US, Europe, Japan, emerg, Global}.xls` de Damodaran (5-ene-2026), versionados
   en `config/industries.toml` (`[regions.R.dollars]`) por `tools/damodaran_import.py`.
4. **Sin la empresa.** De los dos totales de cada columna, uno sale de Dollar (el ancla, que la definición no recorta)
   y el otro de la cifra publicada:
   - múltiplos (P/E, EV/EBITDA, P/B, cobertura de intereses): (A − a) / (A / valor − d);
   - rentabilidades, márgenes y D/E: (valor × A − n) / (A − a).

   Propiedades:
   - con peso 0 da la cifra publicada;
   - respeta la definición de Damodaran: el P/E solo con empresas con beneficio y el EV/EBITDA con EBITDA positivo;
     una empresa en pérdidas no está en ese agregado y no se quita;
   - con el beneficio de todas las empresas, NFLX salía con 221x.
5. **Respaldo, la mediana de los pares del universo** de la misma industria:
   - fuente: `config/peer_metrics.tsv`, Yahoo a 28-oct-2026, 543 empresas, generada por
     `tools/build_peer_metrics.py`;
   - sin la empresa ni sus otras clases;
   - al menos `market.peers.min_peers` pares, y P/E ≤ `pe_meaningful_max`;
   - se usa sin cifras a la fecha, si pesa ≥ `self_max_weight` (0,90: AAPL), o por columna si falta una cifra concreta
     (CB, SHEL y DOW, sin resultado operativo en EDGAR; GOOGL sin deuda: con 2 pares, sin referencia);
   - si sin la empresa la fila de su región no llega a `min_firms`, primero la industria global sin ella (lo que ya
     hacía el motor con una fila pequeña): TM.
6. **Declarada:**
   - en la lectura: «frente a 53,2x de su industria sin ella»;
   - en la nota de la referencia: «Referencia de la industria sin NVIDIA, que pesa el 58 % de su capitalización: el
     agregado menos sus cifras al 5 de enero de 2026 (doce meses a 26 de octubre de 2025)»;
   - en el respaldo: «Referencia: mediana de 8 pares del universo de la industria «Ordenadores y periféricos»…: la
     industria de Damodaran es casi solo Apple (91 %)…»;
   - la columna de las tablas pasa a «PARES».
7. **Precio contraído con el escalón de las tasas base** (texto de N4): la nota queda en «ajustado de X a Y hacia 50».
   Una sola confianza a la vista; la base de contracción va en `confidence.contraction_basis`. Hacía falta para la
   página 2 del PDF clásico (MSFT, NVDA).

**Comprobado en vivo** (`f10_n4` → `f10_n2`; `tools/f10_n2_tabla.py`):

| Empresa | Referencia | Peso | P/E ref. | EV/EBITDA ref. | Bloque | Precio | Nivel |
|---|---|---|---|---|---|---|---|
| NVDA | sin ella | 58 % | 48,8 → 53,2 | 25,9 → 17,7 | 1 → −1 | 55 → 46 | razonable |
| MSFT | sin ella | 50 % | 37,5 → 42,7 | 18,0 → 15,5 | −1 → −2 | 31 → 28 | exigente → **muy exigente** |
| LLY | sin ella | 43 % | 24,9 → 18,1 | 10,0 → 10,3 | −4 → −4 | 38 → 25 | exigente → **muy exigente** |
| UNH | sin ella | 31 % | 21,1 → 23,2 | 11,0 → 10,7 | −1 → −1 | 54 → 54 | razonable |
| JPM | sin ella | 45 % | 14,2 → 13,2 | 14,0 → 14,0 | 0 → 0 | 35 → 35 | exigente |
| CB | sin ella | 61 % | 13,0 → 13,2 | 10,7 → 7,8 | 0 → 0 | 60 → 65 | razonable → **atractivo** |
| AMZN | sin ella | 63 % | 33,5 → 35,0 | 12,1 → 7,9 | −1 → −2 | 31 → 28 | exigente → **muy exigente** |
| MCD | sin ella | 34 % | 32,8 → 38,6 | 17,0 → 15,4 | 2 → 2 | 45 → 45 | razonable |
| GOOGL | sin ella | 69 % | 29,6 → 27,4 | 15,2 → — | −2 → −3 | 28 → 24 | muy exigente |
| VZ | sin ella | 42 % | 8,0 → 7,8 | 6,5 → 6,3 | 0 → 0 | 48 → 48 | razonable |
| CAT | sin ella | 51 % | 25,8 → 21,9 | 14,9 → 10,9 | −4 → −4 | 30 → 30 | exigente |
| UNP | sin ella | 22 % | 16,7 → 16,0 | 10,9 → 10,4 | −3 → −4 | 15 → 10 | muy exigente |
| KO | sin ella | 45 % | 26,3 → 30,5 | 16,6 → 14,5 | −3 → −3 | 31 → 31 | exigente |
| WMT | sin ella | 23 % | 33,5 → 32,1 | 12,1 → 10,7 | −4 → −4 | 10 → 10 | muy exigente |
| XOM | sin ella | 15 % | 15,5 → 15,1 | 6,1 → 6,0 | −2 → −2 | 45 → 45 | razonable |
| KMI | sin ella | 21 % | 18,5 → 17,7 | 11,6 → 11,1 | −2 → −2 | 35 → 35 | exigente |
| NEE | sin ella | 16 % | 21,0 → 20,2 | 12,3 → 11,7 | 0 → 0 | 30 → 30 | exigente |
| AWK | sin ella | 54 % | 20,2 → 18,2 | 14,1 → 13,6 | 0 → −1 | 35 → 38 | exigente |
| PLD | sin ella | 10 % | 28,1 → 27,2 | 19,9 → 19,6 | 0 → 0 | 40 → 42 | exigente |
| O | sin ella | 26 % | 31,1 → 27,0 | 16,7 → 18,0 | 1 → 1 | 58 → 58 | razonable |
| LIN | sin ella | 37 % | 21,4 → 18,8 | 11,2 → 9,4 | −4 → −5 | 10 → 5 | muy exigente |
| FCX | sin ella | 34 % | 29,4 → 26,5 | 11,3 → 13,1 | −1 → 0 | 42 → 45 | exigente → **razonable** |
| ASML | mediana de 5 pares | — | 38,2 → 43,0 | 20,2 → 30,8 | −4 → −4 | 35 → 35 | exigente |
| SAP | mediana de 21 pares | — | 32,0 → 26,1 | 12,4 → 21,9 | −2 → 0 | 28 → 35 | muy exigente → **exigente** |
| MRNA | sin ella | 1 % | 32,1 → 32,1 | 7,4 → 7,4 | — | — | — |
| BA | sin ella | 11 % | 35,3 → 35,3 | 16,8 → 16,8 | — | — | — |
| NU | mediana de 19 pares | — | 9,1 → 12,2 | 69,4 → 10,8 | −1 → −1 | 25 → 25 | muy exigente |

**Cada cambio de nivel sale de la referencia:**
- **MSFT y AMZN:** el EV/EBITDA frente a la industria sin ellas empeora.
- **FCX:** el EV/EBITDA normalizado mejora.
- **LLY:** el Forward P/E frente a una referencia más baja pasa de +3 a 0. La convergencia sube y el veredicto sale de
  la frontera de Ke, así que contrae con alta.
- **SAP:** frente a la mediana de 21 pares, el EV/EBITDA pasa de −4 a +2.
- **CB:** sin cambio en la Valoración, porque el EV/EBITDA es «No aplica» en aseguradoras.
  - El P/B y el ROE de su industria sin Chubb (Chubb es el 78 % de su patrimonio) le dan un P/B frente al sector
    «barata» y un P/B justificado de dos etapas de 6,5x (ROE del resto, 30 %).
  - La convergencia sube a alta y deja de depender de Ke.
  - El PM pidió N2b por esto: región por dónde opera y ROE estable global.

**NVDA:**
- El EV/EBITDA de su industria sin ella baja de 25,9x a 17,7x, y su lectura pasa de +2 a −2.
- El bruto pasa de 55 a 45: frontera de Ke. La confianza visible queda en baja (contrae con media).

## N2b · ROE estable global en el P/B de dos etapas

**Origen.** N2 dejó al descubierto en CB una regla previa.
- Chubb es el 78 % del patrimonio de «Seguros de daños» de Europa.
- Sin ella, el resto son 18 aseguradoras pequeñas con un ROE del 30 %.
- El P/B justificado de dos etapas (F9 · R1b) convergía a ese ROE: 6,5x.

**Regla** (decisión del PM; `industry_bench.global_roe`):
- **El ROE estable del P/B en dos etapas converge a la industria global sin la empresa.** La convergencia a largo plazo
  no es regional.
  - Es la regla de N2 sobre la fila global, o la mediana de pares si toca.
  - Si no hay industria global, el de su referencia regional, declarado.
  - El texto de las dos etapas nombra la fuente: «después ROE de la industria (17.6 %, industria «Seguros de daños»
    global sin la empresa, que pesa el 10 %)».
- **El PM retiró la otra regla que había pedido** (región de la referencia por la geografía de los ingresos):
  - el múltiplo de una empresa se compara con el del grupo en el que la clasifica Damodaran, de cuyo agregado se quita
    en N2;
  - la sede operativa, solo si no aparece en ningún conjunto (lo de siempre);
  - la prima país sigue con la geografía de los ingresos, porque ahí mide exposición al riesgo.

**Comprobado en vivo.** Antes: `f10_n2_hoy`, el mismo día y con el código de N2 en un worktree aparte. Después:
`f10_n2b`.
- **CB**: el ROE estable pasa de 30,1 % (el resto europeo sin Chubb) a 17,6 % (la global sin ella). El P/B justificado
  baja de 6,52 a 3,60, y con Ke + 1 pp el veredicto vuelve a cambiar de nivel. Resultado: confianza baja, precio de 65
  a 60, de **atractivo** a **razonable**.
- **PGR**: el ROE estable pasa de 16,9 % a 16,4 %; ni precio ni nivel cambian.
- **AIG, NU, JPM e ITUB**: sin cambio. AIG, JPM e ITUB no activan las dos etapas; NU ya convergía a lo mismo.
- **Ninguna otra de las 26 + NU + NVDA cambia por N2b.**
- **LIN** se mueve (precio de 5 a 16, confianza baja) por un dato nuevo: entre las dos corridas EDGAR recibió su
  10-Q del 30-sep-2026 y la regla de estados desfasados (F8 · E6) acota la cobertura.

**Golden.**
- **PGR** (panel): el ROE estable y el P/B justificado de dos etapas cambian; el texto de las dos etapas nombra la
  fuente. Sin cambio de nivel.

## B3 · Las alertas leen la misma referencia que su fila

**Origen.** Escaneo del modelo general (`alertas_coherentes`, 20 casos en 543 empresas): fortalezas y alertas con el
tono contrario a su fila.
- **Causa:** la fila lee cada métrica contra la industria de Damodaran (sin la propia empresa, N2), mientras que la
  alerta usaba:
  - el margen y el ROE contra las tablas por sector (`ThresholdConfig`);
  - el P/E y el EV/EBITDA contra absolutos (35x y 25x) o contra otros múltiplos del sector (+30 %, −20 %, ×1,3).

**Regla** (`lib/vs_reference.band`):
- Las bandas de la fila frente a su referencia (`thresholds.pdf.vs_sector_bounds`, ±35 % / ±10 %) en un solo sitio.
  La usan la fila (`display.read_vs_sector`) y la alerta de la misma métrica, con la misma referencia.
- **P/E y EV/EBITDA:**
  - fila en verde → fortaleza (descuento);
  - en línea → sin alerta;
  - prima moderada → aviso (salvo crecimiento que lo justifique, como antes);
  - prima elevada → riesgo, o aviso si el crecimiento la justifica.
  - Sin referencia, los absolutos de siempre (`premium_abs`, `strong_abs`, `high_abs`).
- **ROE y margen neto:** fila en verde → fortaleza; en rojo o ámbar → aviso; en línea o sin referencia → sin alerta.
  Las de signo se mantienen: ROE negativo, ROE negativo por recompras y margen neto negativo.
- **Margen bruto:** fortaleza solo con la fila en verde.
- **Config retirada** (ya no la usa nada): `alerts.pe.premium_dev`, `strong_dev`, `discount_dev`;
  `alerts.ev_ebitda.premium_mult`, `discount_mult`; `alerts.margins.net_solid_mult`, `gross_high`.
- **El score no se toca.** Ninguna puntuación cambia en el panel ni en local (`tools/f10_b3_efecto.py`). Retirar las
  tablas por sector del score es el paso M2 del modelo general; se mide y se enseña al PM antes.

**Comprobado** (`tools/f10_b3_tono.py`): contradicciones en el panel, 1 → 0 (PGR, «Margen neto estrecho — 12.8%» con
la fila «Superior» frente a 10.8 %); en local, 0 → 0.

**Golden** (alertas y sus textos; ninguna puntuación). Principales cambios en el panel:

| Empresa | Antes | Ahora |
|---|---|---|
| PGR | «Margen neto estrecho» | «Margen neto sólido»: 12,8 % frente a 10,8 % de su industria |
| AAPL, KO, V, NVDA, PLTR, CRWD | «EV/EBITDA alto» (por encima de 25x) | «EV/EBITDA sobre su industria / sus pares / el mercado», frente a su referencia |
| BAC, NFLX | — | «Cotiza con descuento», con la fila en verde |
| O, AMT, NFLX | — | «EV/EBITDA barato», con la fila en verde |
| JPM, MC.PA | — | «Prima sobre su industria / sus pares» (P/E con prima moderada en la fila) |
| BAC, DUK, AMZN, BCS, MC.PA | — | «ROE bajo» frente a la industria |
| FCX, SHEL | «Margen neto / ROE sólidos», por la tabla del sector | «estrecho» / «bajo» frente a su industria, como su fila |
| AAPL, MSFT, XOM, PLTR | «ROE elevado / excepcional», por la tabla del sector | sin alerta: la fila no tiene referencia (AAPL) o está en línea |
| SNOW | «Margen bruto muy alto», por el absoluto del 60 % | sin alerta: en línea con su industria |

Con el tope de 6 por grupo, alguna fortaleza de otra métrica entra o sale: «Deuda baja», «Solvencia sólida»,
«Liquidez muy holgada».

**Textos.**
- **Detalle de la fortaleza del ROE:** ya no repite la cifra ni su periodo, que van en el rótulo. Queda «Retorno sobre
  el patrimonio por encima de X de su industria…».
- **Tarjetas cortas** («Fortaleza clave», «A vigilar»): si el rótulo dice «normalizado», el periodo queda en «(TTM)».
  El periodo entero sigue en la sección de alertas.
- **Motivo:** TM pasaba a tener «ROE normalizado elevado — 11.8% (TTM, sin partidas no recurrentes)» como fortaleza
  clave, y la portada del PDF clásico se encogía a 0,846.

**Tests que siguen a la regla:** `test_f9_r4.test_bank_net_margin_raises_no_alert`. La aseguradora lleva el margen de
su industria en el contexto (la alerta ya no lee la tabla del sector); el banco sigue sin alerta.

**Aviso de datos (no es de B3).** TM no tiene cifras a la fecha del conjunto (20-F, N2): su referencia es la mediana de
3 pares del universo (TSLA, GM y F), con un ROE del 3,8 % y un margen neto del 2,1 %. Las lecturas de TM frente a
«sus pares» salen de ahí.

## Fusión del motor en la v4 (f10-motor 96ae72a9 sobre ccacd828)

Conflictos de código, resueltos en origen conservando las dos intenciones:

| Conflicto | Resolución |
|---|---|
| `alert_interpretations._roe`: B3 lee el ROE frente a la referencia de su fila (sin referencia, sin alerta); N6 dice de dónde sale un ROE alto con el DuPont | Las bandas de B3 deciden si hay fortaleza o aviso; el motivo de la fortaleza lleva la causa del DuPont de N6 (sin DuPont, ninguna). El texto: «Retorno sobre el patrimonio muy por encima de X % de su industria sin ella. No lo infla un patrimonio reducido (DuPont …)» |
| `display` (resumen de la confianza): N4 añadía «Un escalón menos por las tasas base (…); no contrae el precio» tras el paréntesis del techo; N6 cambió ese paréntesis por qué la limita, en orden | El escalón de las tasas base es un límite más de `plain_language.confidence_limits`, entre los techos y la dependencia de Ke (el orden en que se aplican): «(TSM) … la limitan: la convergencia es media —…—, hasta media; las tasas base —solo el 0.06% de las comparables sostuvo el crecimiento que exige el precio; no contrae el precio—» |
| `GOLDEN_DIFF_F10.md` (añadido en las dos ramas) | Un documento: el motor y, al final, la presentación |

Tests ajustados a la fusión: `test_f10_roe_dupont` (el contexto lleva el ROE de la industria, sin el que B3 no alerta;
el motivo sin DuPont termina en la referencia; AAPL, sin ROE de referencia en su fila tras N2, no lleva alerta del ROE) y un test nuevo en `test_f10_confianza` (el escalón de las tasas base,
entre los techos y Ke).

**Golden.** Regenerados sobre la fusión. Ninguna puntuación, nivel, confianza ni veredicto difiere de f10-motor (los
cambios frente a ccacd828 son los de N1–N4, N2, N2b y B3, arriba). Los textos nuevos, que no estaban en ninguna de las
dos ramas:

| Cambio | Golden |
|---|---|
| Fortaleza del ROE: referencia de la fila (B3) + causa del DuPont (N6) | NVDA, MU, ASML, NVO, V (panel, local y V_caja_neta), CAT, UL (amplificado), NEE (elevado, en parte por patrimonio reducido) |
| Resumen de la confianza con el escalón de las tasas base como límite | AAPL, AMZN, MSFT, NVDA, PLTR, TSM (y sus PDF) |
| Resumen de la confianza con el formato de N6 sobre la confianza del motor | BAC, BCS, BRK-B, FCX (panel y local), HSBC, KO, MC.PA, NEE, NFLX (panel y local), PGR, SHEL |
| Fixtures del frontend: lo anterior más N5 y N6 (PEAD fiscal, persistencia) | AAPL, BCS, JPM, NEE, PLTR |

## F10 presentación (N5 y N6): `fiabilidad/f10-presentacion`, fusionada en la v4 en ccacd828

Cambios de golden de `fiabilidad/f10-presentacion` frente a e20de9f8 (rediseno/v4-f8), con su causa. Evidencia y
arreglo: `F10_PRESENTACION_REGISTRO.md`. Cada punto va en su commit con sus golden.

### Veredictos

**Ningún veredicto, puntuación ni nivel de confianza cambia** (comprobado en todos los golden JSON: calidad, precio,
confianza, puntuación total y texto del veredicto, antes y después). Solo cambian textos y la marca del PEAD.

### N5 · Rivales en el PDF (b4b3807f)

| Cambio | Golden |
|---|---|
| Sin rivales que pasarle, el capítulo de Rivales dice «este informe se generó sin leer sus rivales» en lugar de «el comparador con los rivales se calcula aparte y aún no estaba listo». Los golden del PDF se generan sin rivales (`peers=None`); en producción el PDF lleva los listos y nombra los que faltan con su motivo | los 36 de `panel_pdf_v2` (más recolocación de páginas) |

### N6 · ROE y DuPont (284bd31b)

| Cambio | Golden |
|---|---|
| ROE excepcional con apalancamiento DuPont < 3.5: «No lo infla un patrimonio reducido (DuPont de FYn: apalancamiento x): sale del margen neto y de la rotación de activos de ese ejercicio» en lugar de «suele estar amplificado … por recompras acumuladas» | NVDA (1.31), MU (1.53), ASML (2.58), V (2.63; también local y el forzado V_caja_neta), NVO (2.80) |
| ROE excepcional con apalancamiento ≥ 3.5: «está amplificado por un patrimonio reducido frente a los activos (DuPont de FYn: apalancamiento x: los activos son x veces el patrimonio)», sin atribuirlo a recompras | AAPL (4.87), CAT (4.62), UL (4.54) |
| ROE elevado con apalancamiento ≥ 3.5: «en parte por un patrimonio reducido frente a los activos» en lugar de «uso muy eficiente del capital» | NEE (3.90) |
| Texto del PDF: lo anterior | los mismos, en `panel`, `local` y `panel_pdf_v2` |

### N6 · PEAD con el trimestre fiscal (40123f52 y 56253a67)

| Cambio | Golden |
|---|---|
| Periodo del cierre fiscal (10-Q/10-K de EDGAR) en lugar de la fecha de Finnhub, y la lectura dice «trimestre fiscal cerrado el …» | AAPL 06-30 → 06-27, CRWD 06-30 → 07-31, KO 06-30 → 07-03, NVDA 06-30 → 07-26, SNOW 06-30 → 07-31 (anuncio, reacción y deriva iguales) |
| PEAD medido donde antes salía «sin dato»: el 8-K de resultados caía el mismo día que la fecha de Finnhub y la ventana (posterior a esa fecha) lo excluía; desde el cierre fiscal entra | MU (fiscal 2026-09-03, anunciado 2026-09-30) |
| Sin el 10-Q del trimestre en los fixtures, «del trimestre cerrado el 2026-09-30 según Finnhub (su 10-Q aún no está en la SEC)» | JNJ, JPM, BAC, PGR (56253a67) |
| Marcas nuevas `period_basis` («fiscal» o «proveedor») y `provider_period` | todos los del panel con PEAD medido |
| Texto del PDF: lo anterior | los mismos |

### N6 · Nota de persistencia (8f40b0f6 y 4d1e1ae3: solo maqueta del PDF clásico, ningún golden de texto)

| Cambio | Golden |
|---|---|
| «Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), la calidad exige persistencia: …» | los que la aplican: ASML, MU, NFLX (panel y local), NVDA, PGR, PLTR, TSM |

### N6 · Motivo de la confianza (3e4b61e6 y 070b1342)

| Cambio | Golden |
|---|---|
| El resumen dice qué limita la confianza, en orden y con el nivel de cada paso («por sus dimensiones sería alta; la limitan: …, hasta media; el veredicto depende de Ke —…—»; el último paso no repite el nivel final) en lugar de «techo en X: …; sin techo sería Y» (o «techo de la confianza» cuando el último paso era la sensibilidad a Ke) | los que tienen techo o dependencia de Ke: 29 golden de `panel` y `local` y sus PDF |
| Los que solo dependían de Ke (sin techo) ganan la explicación: antes no decían nada | incluidos en los anteriores |
| La línea de la portada (web y PDF), que omite la primera frase del resumen, no cambia | — |

## B2 · Una sola serie FY (2d717cf1, más TKO e IDXX)

Escaneo del modelo general (`docs/modelo/ESCANEO_2026-10-28.md`, rama modelo/general-inventario): 11 empresas con cifras
dobles (EIX, IVZ, TKO, NTAP, LHX, KDP, IDXX, APA, BE, CBOE, SO). Con el arreglo, las 11 en vivo: 0 cifras dobles en el
display y en el PDF (`tests/coherence.py <carpeta>` y `FINANZER_SCAN_CACHE`).

| Golden | Cambio | Causa |
|---|---|---|
| BAC | Precio 50 → 48 (sigue «razonable»); Valoración 10 → 9 / 20 | Beneficio FY del accionista común (sin los preferentes, ~1,500 millones al año): ROE del ejercicio menor, P/B justificado 0.99x → 0.93x (141 % en vez de 132 %) |
| BCS | Calidad 71 → 68, precio 58 → 52, confianza media → baja | Beneficio del ordinario (sin los cupones AT1, ~1,000 millones de GBP): P/B justificado 0.79x → 0.64x; el P/B frente al sector dice barata y el justificado cara: convergencia baja, confianza baja y la regla E11 contrae la calidad |
| HSBC | Calidad 69 → 72; P/E 13.78x → 13.05x | La serie FY era `ProfitLoss` (con minoritarios); ahora la del ordinario, como el corte: el BPA TTM aproximado (BPA del ejercicio × beneficio TTM / beneficio del ejercicio) ya no mezcla definiciones y Calidad de ganancias sube de 10 a 13 |
| JPM, DUK, O, PG, PGR, PLD (y JPM y O de local) | Beneficio FY e historia de 10 años del accionista común | Decisión del PM; ningún veredicto cambia |
| NEE | Crecimiento de ingresos a 3 años 3.9 % → 9.4 % | Ingresos: el total entre los conceptos que llegan al último ejercicio (`Revenues`, los operativos), no los de contratos con clientes; cuadra con el «Total Revenue» de Yahoo |
| RIVN, SHEL, TM | Historia de 10 años | Relevo de conceptos del beneficio solo con la misma definición; TM: redondeos de JPY |
| V, BCS | `data_provenance.edgar.primary.reconciliation` | Diferencias de la fuente frente a EDGAR (beneficio del común) registradas |
| Todos | El desglose de la puntuación con la precisión de la tabla (dos decimales en porcentajes y múltiplos: «ROE 119.91%» en vez de «119.9%») | IDXX: 70.6 % en la puntuación frente a 70.67 % en la tabla; una sola precisión, como las tarjetas de R3. Ningún veredicto cambia |
| (TKO en vivo) | El ejercicio anterior al primer informe anual: «la empresa presenta sus cuentas en la SEC desde 2023» bajo la celda | Ningún golden tiene ese caso |

Fixtures: `tests/fixtures/f2b/edgar/companyfacts` de BCS y HSBC con el concepto IFRS del ordinario
(`ProfitLossAttributableToOrdinaryEquityHoldersOfParentEntity`), copiado de `tests/fixtures/edgar/` hasta la fecha de
presentación más reciente del juego: el recorte de la captura no lo pedía.

## B1 · Ningún vacío sin motivo

Escaneo: 289 vacíos sin motivo en 97 empresas. Regla en `lib/empty_reasons.py` (puntuación y display). En vivo, 12 de
las de más vacíos (ABBV, AZO, BKNG, AMZN, BXP, FERG, HONA, ANET, MRNA, BA, FISV, NTRS): 0.

| Golden | Cambio | Causa |
|---|---|---|
| TM | Precio 31 → 25 (sigue «muy exigente»); confianza media → alta | P/FCF con FCF negativo (la financiera de Toyota) pasa de «sin dato» a «n. s.» (flujo de caja libre negativo): no cuenta en la cobertura, Valoración queda cubierta y la confianza sube; sin confianza baja o media el precio no se contrae hacia 50 |
| AMZN, RIVN | P/FCF «n. s.» (flujo de caja libre negativo) | Ídem, sin cambio de veredicto |
| AAPL, NVO | Cobertura de intereses «sin dato» con motivo | La empresa no presenta gasto por intereses |
| MC.PA | PEG con su motivo | |
| O (local) | P/FFO, payout sobre FFO, retorno total: el motivo de la puntuación (sin FFO según Nareit: sin clave de Finnhub) | |
| Todos los PDF nuevos con cifras sin dato | El motivo bajo la rejilla de cifras clave y en la tarjeta del resumen | Como la web |

## N6 · Escalón de las tasas base en el motivo de la confianza

Sin efecto en los golden de esta rama (el escalón de N4 llega con la fusión de `fiabilidad/f10-motor`): el motivo lo
nombra en su orden, «…; un escalón menos por las tasas base —el precio exige …—».

## Fusión de B1/B2 sobre f10-motor

Frente a b00993f3, cambian solo BAC (precio 48 → 42, «razonable» → «exigente»), BCS (calidad 71 → 68, precio 54 → 50,
confianza media → baja) y HSBC (calidad 66 → 69); TM no cambia de veredicto (la convergencia media de N2 pone el techo).
El resto de cambios son de B1 (motivos de los vacíos, en display y PDF) y de la precisión única de IDXX. Causas y la
interacción de BAC con N2 (referencia del P/E sin la empresa con el beneficio del común): `F10_BLOQUEANTES_REGISTRO.md`,
«Fusión en la v4».

## N1b · Discontinuadas y beneficio después de impuestos

**Origen.** El escaneo de control del 29-oct (`docs/modelo/CONTROL_F10_2026-10-29.md`) dejó 28 empresas con el margen
neto por encima de su techo operativo. N1 mira antes de impuestos, de minoritarios y de discontinuadas, y lo que entra
después se le escapa. Verificado en los estados de Yahoo (trimestres a junio de 2026):

| Empresa | Qué entra después del beneficio antes de impuestos |
|---|---|
| FIS | participadas netas de impuestos: 2,21 B$ en el trimestre de marzo (la venta de su parte de Worldpay). **No son discontinuadas**: Yahoo no tiene ninguna en el periodo |
| MKC | participadas netas de impuestos: 0,89 B$ (la revalorización de McCormick de México al tomar el control) |
| OXY, MLM, JCI | operaciones discontinuadas: 3,38 B$ (OxyChem), 1,53 B$ y 1,46 B$ |
| UBER, TWLO | beneficios fiscales: impuestos de −4,05 B$ y −0,99 B$ en un trimestre (liberación de la provisión de activos fiscales diferidos) |

**Regla** (`lib/normalize.py`; config `[thresholds.normalization] tax_median_years = 5`, `tax_median_min = 3`):

1. **Discontinuadas.** El normalizado parte del beneficio de operaciones continuadas: el resultado de las discontinuadas
   del periodo sale entero (positivo o negativo), sin tolerancia, como una partida «discontinuadas» con su fuente
   (Yahoo, «Net Income Discontinuous Operations», 4 trimestres o el ejercicio; en el corte de EDGAR,
   `IncomeLossFromDiscontinuedOperationsNetOfTax` o su equivalente IFRS con `sec_edgar.discontinued_ttm`).
   - **Solo si el beneficio usado las lleva**: más cerca del total del periodo que del total sin ellas. UL en vivo: el
     beneficio que usa el motor (6,48 B) ya es el continuado (el FY2025 da 9,47 B con 3,80 B de discontinuadas):
     restarlas otra vez las contaría dos veces. Se dicen sin restarse.
   - **P/E normalizado con discontinuadas = capitalización / beneficio normalizado.** El BPA de Yahoo del P/E reportado
     no tiene una base fija con discontinuadas (MLM: ya es el continuado, 15,38 $; JCI: ni el total ni el continuado):
     escalarlo las restaría dos veces o ninguna. Se declara en `pe_normalized_basis`.
2. **Después de impuestos.** Tras las demás partidas, el beneficio no puede superar (operativo + cargos devueltos +
   financieros netos + participadas) × (1 − t normalizada) + minoritarios + 2 % de los ingresos (la tolerancia de N1).
   Lo que pasa sale como una partida «después de impuestos» con su fórmula y su motivo (participadas netas de impuestos,
   tipo efectivo del periodo negativo o distinto del normalizado). Continua.
   - **t normalizada:** la mediana de los tipos efectivos no negativos del periodo y de los últimos ejercicios (hasta
     5). Un beneficio fiscal puntual queda fuera por la mediana; uno recurrente (créditos fiscales de una utility) es su
     tipo. Un tipo negativo no cuenta (es un beneficio fiscal, no un tipo). Con menos de 3 válidos, el tipo legal (21 %).
   - **Minoritarios como se reportan** (Yahoo, «Minority Interests»): con minoritarios que absorben pérdidas (NEE,
     +1,86 B$ al accionista) el beneficio del accionista supera al consolidado; es una atribución, no una ganancia.

**Comprobado en vivo** (29-oct, mismo día; antes = 8df00bdb en un worktree desechable, después = esta rama; 28 + 20 de
control con `tools/universe_scan.py --no-pdf`):

| Empresa | Sale | Beneficio normalizado | P/E normalizado | Nivel |
|---|---|---|---|---|
| FIS | 2,04 B$ después de impuestos (participadas) | 3,41 → 1,37 B$ | 5,7x → 14,1x | sin cambio (calidad 53 → 49, media) |
| UBER | 3,07 B$ (tipo del periodo negativo; t legal 21 %) | 9,61 → 6,54 B$ | 14,4x → 21,1x | sin cambio (precio 52 → 50, razonable) |
| OXY | 3,38 B$ de discontinuadas | 6,53 → 3,15 B$ | 17,9x → 20,0x | sin cambio |
| MLM | 1,53 B$ de discontinuadas | 2,49 → 0,96 B$ | 34,3x → 39,6x | sin cambio |
| JCI | 1,46 B$ de discontinuadas | 3,62 → 2,16 B$ | 33,1x → 44,3x | sin cambio (precio 10 → 5) |
| MKC | 0,49 B$ (participadas) | 1,65 → 1,16 B$ | 7,7x → 10,9x | sin cambio |
| TWLO | 0,85 B$ (tipo del periodo negativo) | 1,15 → 0,29 B$ | 33,4x → 130,5x | precio exigente → muy exigente |
| COO | 0,17 B$ | 0,57 → 0,40 B$ | 20,7x → 29,5x | calidad sólida → media |
| META (control) | 4,53 B$ (tipo del periodo 4,6 % frente a la mediana 17,6 %) | 76,0 → 71,5 B$ | 21,1x → 22,4x | sin cambio |

En las 48: cambia el nivel de calidad en 1 (COO) y el de precio en 1 (TWLO). De las 28, siguen violando la regla del
escaneo 15 (detalle en el informe de la ronda).

**Golden.**

- Todos llevan el bloque nuevo `earnings_normalization.after_tax` (o `null`) y las piezas nuevas de la coherencia
  (participadas netas de impuestos, minoritarios, tipos de los ejercicios).
- **UL (panel):** 4,29 B de discontinuadas (la escisión de los helados): normalizado 10,76 → 6,46 B; P/E normalizado
  13,2x → 21,5x (capitalización / continuado); precio 50 razonable → 39 exigente, confianza baja → media; calidad 72 → 71.
- **NEE (panel):** 1,45 B después de impuestos (tipo del periodo −8,6 % frente a la mediana 13,8 %; minoritarios ya en
  el techo): P/E normalizado 19,4x → 23,4x; sin cambio de nivel. Utility fuera de alcance que la regla toca sola.
- **PLTR:** 0,04 B (normalizado 2,97 → 2,93 B; P/E normalizado 174,5x → 177,0x).
- **DUK:** 0,01 B de discontinuadas que el beneficio usado no lleva: quedan en los datos, sin restarse ni salir en la
  nota (con ellas la nota se alargaba una línea y el salto de página partía «Duke Energy»).
- **Nota de normalización:** el tipo de la partida con su nombre («después de impuestos»), no la clave.

## Margen operativo con una sola verdad · reglas 1 y 2

**Origen.** La puerta de la v4 (`docs/modelo/PUERTA_V4_2026-10-29.md`, regla `margen_operativo_unico`) encontró 46
empresas con dos márgenes operativos del mismo periodo que difieren más de 3 pp. **Los rótulos de la puerta están al
revés** (lo confirma la verificación de «Modelo general»):

- **El margen que se enseña y puntúa** (`key_metrics.operating_margin`) ya es EDGAR: `OperatingIncomeLoss`, el TTM del
  corte (`edgar_primary`, fase 3, D2).
- **La normalización** (las piezas de N1 y N1b) usaba la fila trimestral «Operating Income» de Yahoo. Yahoo la construye
  sin cargos y, a veces, sin ganancias.

Ejemplos: GILD −8,2 % (EDGAR, con 10,3 B$ de cargos) frente a 38,5 % (Yahoo); KHC −12,8 % frente a 17,0 %.

**Regla** (`lib/normalize.py`: `pieces_operating_income` y `operating`; `main.py`; config
`[thresholds.normalization] operating_item_types`):

1. **Una sola cifra.**
   - Las piezas de la normalización (coherencia y después de impuestos) usan el resultado operativo del corte, el mismo
     que se enseña: el EBIT que presenta el emisor.
   - La fila trimestral de Yahoo solo entra como respaldo declarado, cuando el operativo del corte no es de los mismos
     doce meses. Queda en `earnings_normalization.operating.yahoo_quarterly` con su fuente en `pieces_source`.
2. **Puntúa el margen sin los cargos operativos que la normalización ya quita del beneficio, como el margen neto.**
   - Qué cuenta: las partidas explícitas aplicadas de los tipos de dentro del operativo (cargos especiales,
     reestructuración, deterioros, amortizaciones extraordinarias), con su signo y solo por el exceso no recurrente.
   - **Dentro o debajo del operativo.** La fila de Yahoo no lo dice. WDC lleva +5,77 B$ de «Special Income Charges», la
     ganancia de su participación en Sandisk, y GEV +4,19 B$ de la venta de Prolec: las dos van debajo del operativo.
     Lo decide la identidad del propio estado: no operativo = antes de impuestos − (operativo + financieros netos +
     participadas), sin las partidas no operativas ya identificadas. La parte del no operativo del mismo signo explica
     lo que va debajo; solo el resto estaba dentro.
   - **Por debajo de `label_min_diff`** puntúa el reportado.
   - **Se enseñan las dos cifras:**
     - la fila «Margen operativo normalizado», junto a la del reportado, con su motivo;
     - `key_metrics.operating_margin_normalized`;
     - la frase en la nota de la normalización;
     - en el desglose, «Margen operativo normalizado» y el periodo «sin partidas no recurrentes».

**Goldens:**

| Golden | Cambio | Causa |
|---|---|---|
| todos los no financieros | `earnings_normalization.operating` (nuevo bloque) | regla 1: el operativo de las piezas, su fuente y el de Yahoo |
| V (panel y local) | puntúa «Margen operativo normalizado» 62,90 % (+5, como antes); fila nueva y frase en la nota | regla 2: 0,99 B$ de cargos especiales (litigios) dentro del EBIT de EDGAR (60,68 %) |
| KO | después de impuestos: salen 70 M$; normalizado 14,32 → 14,25 B$; «normalizado» en ROE, margen neto y P/E; FCF/BN +1 → +3 | regla 1: con el EBIT del emisor (14,85 B$ frente a 15,94 B$ de Yahoo, que saca otros cargos operativos) el no operativo GAAP es 1,00 B$ y el techo baja |
| NEE | la coherencia saca 0,19 B$ en vez de 0,61 B$; precio 45 → 48 (Valoración 8 → 9) | regla 1: el EBIT del emisor es mayor que la fila de Yahoo |
| SNOW, V (forzados), FCX, NFLX… | solo el bloque `operating` | regla 1 |
| `confidence.test.ts` (NEE) | «de 40 a 45» → «de 45 a 48» | el precio de NEE de la fila anterior |

### Comprobación de las fuentes mientras se verifica el constructor de EDGAR

**Origen.** Con las piezas en el EBIT de EDGAR, un error del constructor del TTM se propaga a la normalización. FIX (7,9 %
frente a 16,7 %) y ECHO perdían 0,64 B$ y 10,8 B$ de beneficio normalizado.

**Regla** (Plan, 29-oct; `normalize.operating_check`; config `operating_sources_tolerance = 0.03`):
- El EBIT de EDGAR entra en las piezas solo si, sin los cargos que la normalización ya quita, cuadra con la fila
  trimestral de Yahoo a 3 pp de los ingresos.
- Si no cuadra, queda «por verificar» (`earnings_normalization.operating.check`). Las piezas usan entonces el respaldo
  declarado y la nota lo dice.
- Lo que se enseña y puntúa sigue siendo EDGAR, con la regla 2.

En vivo: FIX, ECHO, GILD, KHC y D por verificar, y FIX, ECHO y D recuperan su beneficio normalizado; KO cuadra (2,2 pp).

**Goldens:** solo el bloque `check`, con «coincide» en todos; ninguna cifra ni puntuación cambia.

### Constructor del TTM de EDGAR: el ejercicio solo de un informe anual, y cada pieza en su base

**Origen.** La verificación de «Modelo general» (`docs/modelo/VERIF_MARGEN_OPERATIVO_2026-10-29.md`) comparó las 28 de
la segunda causa con los trimestres presentados en EDGAR:
- en 20 acierta nuestro EDGAR;
- en 2 falla nuestro constructor: FIX e IFF;
- en 2 no acierta ninguna fuente: HON y SKYD;
- 3 no tienen TTM trimestral: CRL, FDXF y BTI;
- 1 queda sin verificar: DEO.

**Regla** (`sec_edgar.flow_ttm`, sus reglas 1 y 2):
1. **Un ejercicio (≥ 350 días) solo sale de un informe anual** (10-K, 20-F, 40-F, sus /A y el 10-KT). FIX: su 10-Q del 1T
   de 2026 etiqueta el comparativo del 1T de 2025 (209 M$) con el periodo del ejercicio entero, y por ser posterior
   ganaba al 10-K (1.315 M$).
2. **El acumulado del año anterior en la base del ejercicio:** el último presentado no después que el ejercicio, no el
   comparativo reexpresado de un 10-Q posterior. IFF: el primer semestre de 2025 reexpresado (+320 M$) con el ejercicio
   sin reexpresar daba −291 M$ en lugar de 754 M$.

En vivo, FIX pasa a 16,7 % (antes 7,9 %) e IFF a 7,4 % (antes −2,9 %); los dos cuadran ya con la fila de Yahoo.

**Goldens:** ninguna puntuación ni nivel cambia.

| Golden | Cambio | Causa |
|---|---|---|
| todos los de EDGAR | `data_provenance.edgar.primary.cut[].accns`: entra el 10-Q original del año anterior | regla 2 |
| BAC | ingresos de EDGAR 115,12 → 116,00 B$ (margen neto 26,3 % → 26,1 %, P/S 3,12x → 3,10x) | regla 2: el acumulado de 2025 original, en la base del ejercicio |
| NFLX, SNOW | referencia de la industria sin la empresa: décimas | regla 2 en el beneficio TTM de EDGAR con que se excluye a la empresa |

### Ajustes del Plan antes de fusionar (29-oct)

1. **Fuera la comprobación provisional «por verificar».** La verificación la invalida: EDGAR acierta en 20 de las 28 y
   Yahoo en 2, ya corregidas con fc5b79f7. La fila trimestral de Yahoo no es el operativo presentado. Las piezas de la
   normalización son siempre el EBIT de EDGAR del corte; Yahoo solo entra, declarado, cuando EDGAR no tiene el TTM de
   ese corte (`pieces_operating_income`).
2. **Ventas de negocios o de activos dentro del operativo, en las dos direcciones** (`operating_item_types`: + «Gain On
   Sale Of Business», «Gain On Sale Of Ppe» y el total de Yahoo cuando sus componentes no cuadran).
   - **Reparto por signo:** el no operativo del estado solo explica partidas de su mismo signo, hasta su importe; esas
     van debajo del operativo, y las demás estaban dentro.
   - En vivo: SOLV 25,0 % → 7,3 % (la venta de P&F, +1,47 B$); BA 4,6 % → −1,2 % (6,41 B$, de los que 1,0 B$ van
     debajo).
3. **Sin corte trimestral, el margen del último ejercicio de los estados** (regla 4 de la verificación;
   `normalize.fy_operating`).
   - Es el mismo que usan las piezas de la normalización, y su procedencia lo dice.
   - Antes era el `operatingIncome` de quoteSummary, otra definición o periodo: CRL 15,1 % → 2,3 %; FDXF −5,8 % → 6,1 %
     (11,7 % normalizado).

**Goldens:** desaparece el bloque `check`.

| Golden | Cambio | Causa |
|---|---|---|
| FCX (local) | 0,56 B$ del total de Yahoo dentro del operativo (0,16 B$ debajo); margen normalizado 24,6 %; Rentabilidad 19 → 17; calidad 67 → 65 | ajuste 2 |
| NEE | su total de Yahoo (0,34 B$) va debajo del operativo; nada cambia en la puntuación | ajuste 2 |

### Perímetro: el filing más reciente, comprobado con la suma de los trimestres (Plan, 29-oct)

**Regla** (`sec_edgar.flow_ttm`, `quarters_ttm`, `checked_flow_ttm`; `edgar_primary`; config
`data.edgar.ttm_quarters_tolerance = 0.01`):
- Por defecto, cada periodo del TTM (el ejercicio, el acumulado y el acumulado anterior) con el filing más reciente que lo
  presenta: el comparativo reexpresado (decisión del Plan).
- El TTM del resultado operativo tiene que cuadrar con la suma de sus 4 trimestres, cada uno del filing más reciente y
  con el 4T como ejercicio − 9 meses, a ± 1 pp de los ingresos del corte.
- Si no cuadra, se usa el de la base del ejercicio (IFF).
- Si ninguno cuadra, el TTM de EDGAR no es homogéneo: se queda el de la fuente, marcado «estimado por la fuente» con el
  motivo en el anexo (HON).

**En vivo** (contra companyfacts):

| Empresa | Filing más reciente | Base del ejercicio | Suma de trimestres | Resultado |
|---|---:|---:|---:|---|
| HON | 8,55 B$ | 4,09 B$ | 10,99 B$ | no homogéneo (los 9 meses de 2026 ya sin lo escindido; el 1T y el 2T de 3 meses, con ello); 16,2 % de Yahoo, declarado |
| BDX | 2,40 B$ ✓ | 1,92 B$ | 2,48 B$ | el más reciente, 11,5 % |
| IFF | −0,29 B$ | 0,73 B$ ✓ | 0,75 B$ | la base del ejercicio, 7,4 % |

**Goldens:** los registros del acumulado anterior vuelven al filing más reciente (NFLX, FCX, SNOW, V); ninguna cifra ni
puntuación cambia.

### N1/N1b solo recortan lo que pueden nombrar, y los cargos con etiquetas estándar de EDGAR (Plan, 29-oct)

**1. Recorte = el menor del exceso sobre el techo y de las partidas que lo nombran** (`normalize.coherence` y
`after_tax`):
- **Antes de impuestos:** las ganancias de inversiones que presenta el emisor en EDGAR (`investment_gains`, ahora en
  todas las empresas: `info["_named_gains"]`), sin las ya normalizadas.
- **Después de impuestos:**
  - las participadas netas de impuestos;
  - el beneficio fiscal frente al tipo normalizado de N1b, solo con beneficio antes de impuestos positivo;
  - las ganancias nombradas que N1 no recortó.
- **El exceso sin nombre** no se recorta. Queda en `earnings_normalization.unexplained` y lo dice la nota. Si se
  distingue del beneficio (más de `label_min_diff`), es una incidencia de la fuente y baja la confianza.
- **En vivo:**
  - Conservan su recorte NVDA (13,91 B$), FIS (2,13 B$), UBER (3,07 B$), TWLO (0,89 B$) y OXY (discontinuadas). UL no
    tenía recorte.
  - Ya no se recortan en falso ECHO (10,79 B$ declarados) y BEN.
  - D (0,62 B$ de ganancias de inversiones), XEL (0,65 B$) y WEC (0,06 B$) se recortan con nombre. XEL y WEC son los
    créditos fiscales de las utilities frente al tipo normalizado, el hueco que N1b dejó fuera de alcance.

**2. Cargos y ventas con etiquetas estándar** (`sec_edgar.charges_ttm`; solo us-gaap e IFRS estándar, nunca las propias
del emisor):
- **Qué cuenta:** deterioros de fondo de comercio, intangibles y activos, reestructuración, litigios, I+D adquirida y
  ventas de negocios o activos. Si el emisor presenta la etiqueta paraguas, manda ella: sus partes pueden solaparse
  (INTC).
- **Sin doble conteo:** sale solo lo que EDGAR identifica de más frente a todas las filas de Yahoo del mismo signo, con la
  prueba de recurrencia sobre su serie anual:
  - DLR: Yahoo trae su venta de inmuebles como «venta de valores».
  - Las ganancias por venta descuentan además las discontinuadas aplicadas, en bruto. MLM: la venta a Quikrete ya sale
    como discontinuada; contarla otra vez llevaba su beneficio normalizado a −0,37 B$.
- **Dentro del operativo:** los cargos que corroboran las etiquetas de EDGAR van dentro sin más (`known_inside`: ABBV,
  cuyo no operativo negativo de pagos contingentes no los explica). La identidad del estado reparte solo el resto.
- **En vivo:**

| Empresa | Margen operativo que puntúa |
|---|---|
| ABBV | 30,3 % (antes 26,2 %) |
| INTC | 7,6 % |
| GIS | 15,2 % |

**Fixtures:** `tests/f10_extend_charges_fixtures.py` añade a los companyfacts del juego f2b los hechos de los conceptos
nuevos presentados hasta la captura (16-oct): 7.021 hechos en 42 emisores; el resto no se toca. Solo hechos de filings
que el juego ya tiene: uno nuevo haría creer al replay que ya está incorporado y dejaría de leer su XBRL pendiente (KO
perdía el semestre de 2026). Sin ellos, el replay no podía nombrar el recorte de NVDA, que sí se nombra en vivo.

**Goldens:**

| Golden | Cambio | Causa |
|---|---|---|
| NEE | la coherencia ya no recorta 0,19 B$ sin nombre; después de impuestos, 1,56 B$ nombrados (beneficio fiscal); normalizado 7,37 → 7,51 B$ | 1 |
| PLTR | 47 M$ antes de impuestos sin nombre se declaran (1,6 % del beneficio): incidencia de la fuente, confianza media → baja; precio 15 → 24 (la confianza baja acerca el precio a 50) | 1 |
| PG | EDGAR identifica 0,06 B$ de cargos de más; margen operativo normalizado 22,8 %; normalizado 15,75 → 15,80 B$ | 2 |
| JPM, BAC, CAT | partida «EDGAR: cargos» recurrente, sin exceso (0) | 2 |
| todos | `unexplained`, `named` y el detalle de lo nombrado | 1 |

### Corrección de la regla 1 del constructor: un ejercicio nunca de un informe trimestral («Modelo general», 29-oct)

**Origen.** La regla «un ejercicio solo de un informe anual» (fc5b79f7) dejaba sin ejercicio a VRSN. En companyfacts, su
NetIncomeLoss anual solo aparece con el DEF 14A, las tablas de pay versus performance. `flow_ttm` daba None en lugar de
811 M$, y la referencia de la industria caía a la mediana de los pares: EV/EBITDA de referencia 15,5x → 46,9x, la fila
de −4 a +4 y el precio de 15 a 42.

**Regla** (`sec_edgar._flow_groups`, `QUARTERLY_FORMS`):
- Un ejercicio (≥ 350 días) nunca sale de un informe trimestral (10-Q, 10-Q/A, 6-K y 6-K/A).
- Si hay varios formularios para el periodo, manda el informe anual; si no lo hay, valen los demás.
- En vivo: FIX sigue en 16,7 %; VRSN vuelve a la referencia sin la empresa (EV/EBITDA −4, precio 15).

**Goldens:** sin cambios.

### Falsos «no homogéneo» en la suma de trimestres (comprobación de «Modelo general» sobre 030b30ad)

**Origen.** El escaneo de comprobación de las 543 encontró dos empresas cuyo TTM de EDGAR era el bueno, pero la suma de
trimestres de la comprobación no:
- **DLR** (corte del 31-03-2026): el 10-Q de julio de 2026 reexpresa el 2T de 2025, de 212 a 1.144 M$. La suma con ese
  trimestre da 1.662 M$; con los trimestres como se presentaron, 730 M$, que cuadra con el TTM (729 M$). Caía a Yahoo, y
  el precio pasaba de 20 «muy exigente» a 32 «exigente».
- **LHX:** companyfacts trae un «trimestre» de 3 meses que acaba al cierre del ejercicio con el valor del ejercicio
  entero (2.110 M$).

**Regla** (`sec_edgar.quarters_ttm`, `checked_flow_ttm`):
- La suma se calcula con los trimestres más recientes y con los presentados por primera vez, y vale cualquiera de las
  dos.
- Un «trimestre» con el valor del ejercicio que acaba ese mismo día es un error de etiquetado y se deriva como
  ejercicio − 9 meses.
- HON sigue sin cuadrar con ninguna (6.527 y 10.995 M$ frente a 8.555 y 4.087): no homogéneo, por diseño.
- En vivo: DLR 11,5 % y LHX 10,1 %, ya desde EDGAR; DLR vuelve a 20 «muy exigente».

**Goldens:** sin cambios.

### Memoria y la comprobación «no disponible» (Plan, 29-oct)

**Memoria.** Perfil con tracemalloc, un análisis a la vez, de las mismas 12 empresas (HON, GIS, ABBV, NVDA, KO, DLR,
INTC, BA, PFE, GE, XOM, AAPL) en la puerta (be9a0ea3) y en la rama:
- **No se retiene companyfacts completo:** la caché guarda los hechos reducidos, como antes.
- **El aumento es la caché de hechos de EDGAR** con los conceptos nuevos. Con `sec_edgar._recent_only`, de las etiquetas
  de cargos y ventas solo se guardan los periodos que se usan: el TTM y la ventana de recurrencia, más dos años.
- **Cifras:**

| | Puerta | Rama sin recortar | Rama con el recorte |
|---|---:|---:|---:|
| Memoria Python retenida (en 8 análisis) | 47,2 MB | 48,2 MB (+1,0) | — |
| Memoria Python retenida (en 12 análisis) | 56,2 MB | — | 56,8 MB (+0,6) |
| Coste por emisor en la caché (32 como máximo) | — | — | unos 0,05 MB (≤ 1,6 MB) |
| Pico por análisis | — | — | +0,1 a +0,5 MB (PFE +1,7) |
| RSS máximo | 347 MB | — | 332 MB |

**Comprobación.** `checked_flow_ttm` dice `check`: «cuadra», «no_disponible» (sin 4 trimestres válidos de 80 a 100 días:
el TTM se queda) o «no_homogeneo». Va en `data_provenance.edgar.primary.cut[].check`.

**Goldens:** solo el campo `check` (19 del panel y los de local).

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
