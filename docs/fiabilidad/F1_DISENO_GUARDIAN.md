# Fase 1 · Diseño del guardián narrativo (propuesta para el punto de parada 1)

*Operador F1, 14-oct-2026. Objetivo: que cada afirmación del informe (PDF y web) sea verdad según el dato
estructurado, y cerrar la **clase** de error, no solo PLTR.*

## 1. Enfoque: (b) en origen + (a) como red de seguridad, enlazadas

| | (a) A posteriori: patrones sobre el texto generado | (b) En origen: el generador declara la afirmación |
|---|---|---|
| Cómo | Expresiones sobre el texto del PDF y de `display`, cada una con un predicado | Cada lector (`read_coverage`, `read_growth`…) devuelve la frase **y** la afirmación estructurada que hace |
| A favor | Independiente del código; ve todo lo que llega al lector (también lo que solo pinta el PDF) | Exacto: no hay que adivinar a qué campo se refiere "+30%"; sin falsos positivos de redacción |
| En contra | Frágil con la redacción en español; ambigüedad cifra → campo; falsos positivos | Solo cubre los generadores instrumentados; el texto podría decir algo distinto de lo que declara |

**Propuesta: las dos, enlazadas.**

1. **En origen (b):** los lectores de `display.py` (y los textos de `alert_interpretations.py` que llegan al
   informe) registran, junto a cada frase, sus afirmaciones: `Claim(tipo, campo, operador, valor, cita)`, donde
   `cita` es el trozo literal del texto que la expresa ("EBIT negativo", "12.5%", "caja neta").
2. **Red de seguridad (a):** una lista cerrada de **palabras de afirmación** ("EBIT negativo", "caja neta", "deuda
   neta", "en máximos", "en mínimos", "recompr", "diluy", "crecen", "se contraen", "superior", "inferior",
   "autofinanciada"…). Si una de ellas aparece en un texto que **no** tiene una afirmación declarada que la
   respalde, el guardián falla con "afirmación sin respaldo". Así un generador nuevo o no instrumentado no puede
   colar una frase sin predicado.
3. **Enlace texto ↔ afirmación:** la `cita` de cada afirmación tiene que aparecer literalmente en su frase. Si el
   texto cambia y deja de decir lo que declara, falla.
4. **Lista negra (a) pura:** inglés y códigos internos sobre el texto final (PDF y `display`), fuera del anexo
   técnico (D1).

**Sin cambio en la salida:** las afirmaciones no se escriben en el JSON del análisis (cambiarían los 37 golden y el
contrato de la web). Se recogen con un colector (`contextvars`) que solo se activa en los tests:
`build_display(..., )` se ejecuta igual; con el colector activo, cada lector deposita sus `Claim` con la ruta de su
texto. En producción el colector está apagado y el coste es nulo.

## 2. Catálogo de afirmaciones (predicados)

Tolerancia de cifras: la cifra del texto debe coincidir con el valor del campo **redondeado como se imprime**
(mismo número de decimales; porcentajes ×100).

| # | Afirmación en el texto | Predicado sobre el análisis |
|---|---|---|
| 1 | "EBIT negativo", "resultado operativo negativo" | `key_metrics.operating_income < 0` |
| 2 | "caja neta" / "deuda neta" | `key_metrics.net_debt < 0` / `> 0` |
| 3 | "en máximos / en mínimos de 52 semanas", "cotiza en el X% del rango" | posición en el rango ≥ / ≤ umbral de config; X = posición redondeada |
| 4 | "recompró / retiró un X% de las acciones" / "diluyó un X%" | variación de acciones < 0 / > 0 y cifra |
| 5 | "crecen / se contraen un X%" (ingresos, BPA, FCF, FFO) | signo y cifra del valor que **puntúa**; si está en la cota del modelo (−5% / +10% de ciclo medio), el texto **debe** decir que es la cota |
| 6 | "superior / inferior al sector", "+N% vs sector", "prima / descuento" | signo de la brecha y N redondeado |
| 7 | Veredicto, nivel de calidad, nivel de precio, confianza | `verdict.*`, `quality.level`, `price_attractiveness.level`, `confidence.level` |
| 8 | Arquetipo nombrado en la prosa ("banco", "REIT", "utility", "cíclica", "madura", "pre-beneficio") | `classification.archetype` |
| 9 | Cifras de las tarjetas KPI y de las métricas citadas | valor del campo redondeado como se imprime |
| 10 | Métrica "no aplica" citada con cifra | prohibido (`sectors.archetypes.not_applicable`) |
| 11 | Inglés (lista cerrada ampliable: STRONG, GOOD, NEUTRAL, WEAK, MATURE, CYCLICAL, FINANCIAL, UTILITY, N/A en prosa…) y códigos internos (`snake_case`, `por_defecto`, `industria_*`, `pe_implausible`…) | prohibido fuera del anexo "Detalle técnico para auditoría" |
| 12 | Cobertura de intereses: "fácilmente servible: Nx", "cubre N veces", "sin carga financiera neta" | `interest_coverage` y su estado; "EBIT negativo" exige #1 |
| 13 | ROIC frente a WACC: "crea / destruye valor", "spread de +X%" | signo y cifra de `roic_wacc_spread` |
| 14 | DCF: "fiabilidad alta / media / baja", "prima / descuento del X% sobre el valor intrínseco", "un solo método evaluable" | `dcf.reliability.level`, signo y cifra de `dcf.upside`, nº de métodos evaluables en `confidence` |
| 15 | Altman "zona segura / gris / de riesgo", Piotroski "N/9" | `altman_z.zone`, `piotroski_f.score` |
| 16 | "autofinanciada", "runway de N años" | `archetype_metrics.runway` (estado y años) |
| 17 | Moneda: "TWD convertidos a USD", factor ADR "5.00 acciones" | `data_provenance.currency` |
| 18 | Beta: "se mueve en línea / más / menos que el mercado" | banda de `beta` en config |
| 19 | Payout "cubierto / justo / insostenible" | banda de `payout_ratio` según su base (FFO en REIT) |

## 3. Alcance y prueba de que detecta

- **Alcance:** los 30 análisis del panel en replay (SPY se rechaza) y los 6 de `local`; texto de `display` (lo que
  pinta la web y maqueta el PDF) y texto extraído del PDF (red de seguridad y lista negra).
- **Fallos actuales:** xfail estricto por (predicado, ticker); cada arreglo de T3 los convierte en XPASS y se quitan.
- **Prueba de que detecta** (`test_guardian_detecta.py`, como `test_invariants_detectan.py`): por cada predicado, un
  análisis real que lo cumple pasa y, con una violación inyectada (cambiar el dato o el texto), falla. Además: una
  palabra de afirmación sin `Claim` falla, y una `cita` que no está en su frase falla.

## 4. Qué cambia en el código (T2)

- `backend/lib/claims.py` (nuevo, ~60 líneas): `Claim`, el colector (`contextvars`) y `record(path, text, claims)`.
  Inerte si no hay colector activo.
- `backend/lib/display.py` y `alert_interpretations.py`: cada lector añade `record(...)` con sus afirmaciones. **Sin
  cambio en la salida** (golden idénticos tras T2; se comprueba con `diff_golden.py`).
- `backend/tests/guardian.py` (predicados y red de seguridad) y `test_guardian.py` (panel + local, xfail por caso),
  `test_guardian_detecta.py`.

## 5. Dos avisos para el punto de parada

1. **La cobertura de intereses de PLTR también llega al WACC.** `cost_of_capital.synthetic_rating` usa el mismo
   estado erróneo: la regla M le da rating BBB "por EBIT < 0" (spread 1.11%). Con el estado corregido (EBIT > 0 y
   gasto financiero neto ≤ 0 → "sin carga financiera neta"), el rating pasa al tramo de mejor cobertura: cambia el
   Kd, el WACC, el DCF y quizá el precio de PLTR. Es la misma causa de T3.1 (lógica, no método), pero el efecto va
   más allá de la Solidez. Propongo tratarlo en el mismo commit y explicarlo en el diff de golden.
2. **PLTR no tiene gasto financiero en los estados del plan B:** la cobertura de −1.53 viene de Finnhub. El signo del
   gasto se deducirá así: `interest_expense` de los estados si existe; si falta y la cobertura es negativa con EBIT
   > 0, el gasto neto es negativo (ingreso financiero neto). Lo dejo explícito en el test unitario.
