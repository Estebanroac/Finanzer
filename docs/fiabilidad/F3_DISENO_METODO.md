# Fase 3 · Diseño de método por tipo de negocio (planificación)

*Planificador, 2026-10-15. Documento de criterio, no de código: fija **qué** debe hacer el motor con cada tipo de
empresa y **por qué**, para que el prompt de la fase 3 no tenga que inventar método. Se escribe antes de cerrar la
fase 2; las piezas que dependen de la 2b están marcadas con **[2b]**.*

*Decisiones del usuario que lo fundan: **D3 = DCF inverso** (+ no contraer cuando solo falta el segundo método) y
**D4 = clasificar por la historia real** (tipo "crecimiento rentable"; la ciclicidad se mide con datos, no con la
industria). Ver `BITACORA.md`.*

---

## 0. Principios

1. **El tipo de negocio decide las herramientas** (Damodaran): ninguna métrica es universal. Antes de puntuar, el
   motor debe saber qué preguntas tienen sentido para esa empresa.
2. **Con datos, no con etiquetas.** La industria de Yahoo es un indicio, no una prueba. Donde haya historia suficiente
   (EDGAR da 10+ ejercicios **[2b]**), manda el comportamiento observado.
3. **El precio se juzga con dos métodos independientes** (intrínseco y relativo). Si el intrínseco directo no concilia,
   se usa al revés (§2) en lugar de descartarlo.
4. **Nada de cotas silenciosas.** Si el método necesita acotar un dato, lo dice y explica por qué (lección de la cota
   −5%/+10% del ciclo medio).
5. **Tasas base antes que extrapolación.** Un crecimiento esperado se contrasta con lo que logran empresas comparables
   (Mauboussin y Callahan, *The Base Rate Book*, 2016). Las cifras de tasas base se verifican en la fuente antes de
   usarlas; no se citan de memoria.

---

## 1. Clasificador (D4)

### 1.1 Orden de decisión

| Paso | Pregunta | Resultado |
|---|---|---|
| 1 | ¿Es un fondo/ETF? | Rechazo (ya existe, 422) |
| 2 | ¿Banco, aseguradora, mercados de capitales? (industria + balance: préstamos/depósitos o primas) | FINANCIAL (subtipo: banco, aseguradora, conglomerado) |
| 3 | ¿REIT? | REIT |
| 4 | ¿Utility regulada? | UTILITY |
| 5 | ¿BPA ≤ 0 sostenido y crecimiento alto? | GROWTH_PRE_PROFIT |
| 6 | **¿Ciclicidad observada en su historia?** (§1.2) | CYCLICAL (con nota de "crecimiento estructural" si además cumple §1.3) |
| 7 | **¿Crecimiento rentable?** (§1.3) | GROWTH_PROFITABLE (nuevo) |
| 8 | Resto | MATURE |

La **ciclicidad va antes que el crecimiento**: una empresa que crece mucho en la parte alta del ciclo (memoria,
semiconductores, acero) es la que más necesita el análisis de ciclo medio. Su crecimiento estructural se reconoce en
la nota y en la base de crecimiento, no cambiando de herramienta.

### 1.2 Ciclicidad con datos **[2b: historia de 10+ ejercicios de EDGAR]**

Medidas sobre ≥ 8 ejercicios (con < 8, la regla de industria actual con confianza baja):

- **Caída máxima de ingresos** de pico a valle (en moneda de los estados, por acción si hubo emisión relevante).
- **Amplitud del margen operativo**: máximo − mínimo del periodo, frente a su media.
- **Años con BPA negativo o caída de BPA > 50%.**

Umbrales propuestos (calibrar con el panel ampliado y anotar la calibración): cíclica si la caída máxima de ingresos
≥ 20% **o** la amplitud del margen operativo ≥ 1.0× su media **o** hay ≥ 2 años con caída de BPA > 50%, siempre que
**no** se explique por un cambio de perímetro **[2b]**.

Casos esperados para verificar (no son la respuesta, son la prueba): MU, DOW, FCX, XOM → cíclicas; CAT → cíclica
(caídas de ingresos de 2009, 2016 y 2020); TSM y ASML → a medir; NVDA → a medir (caídas de BPA en 2019 y 2023);
KO, PG, JNJ → no cíclicas.

### 1.3 Crecimiento rentable (GROWTH_PROFITABLE, nuevo)

Las tres a la vez:
- CAGR de ingresos **por acción** a 3 años ≥ 15% (y el de 5 años, si existe, ≥ 10%);
- BPA TTM > 0 y margen operativo ≥ 10% (o margen FCF − SBC ≥ 10%);
- no cíclica según §1.2.

Esperados: PLTR, CRWD (si su margen operativo GAAP no llega al 10%, valorar el margen FCF − SBC y documentarlo);
NVDA solo si §1.2 no la marca cíclica.

**Herramientas de este tipo:**
- **Rule of 40** (crecimiento de ingresos + margen FCF − SBC) como lectura de calidad, no como puntuación aislada.
- **SBC como coste real**: FCF − SBC en márgenes y en el DCF (ya existe en pre-beneficio; se extiende aquí).
- **PEG a varios años** con el crecimiento del BPA por acción a 3 años, no el de un año.
- **DCF inverso** (§2) como método intrínseco principal: el P/E de 174 de PLTR solo se puede juzgar contra el
  crecimiento que exige.
- Referencia relativa: frente a otras de crecimiento rentable o con EV/Ventas ajustado por crecimiento, nunca frente
  a la mediana del sector amplio.

### 1.4 FINANCIAL: subtipos y métricas que sí aplican

| Subtipo | Valoración | Calidad | Notas |
|---|---|---|---|
| Banco | P/TBV frente a ROTE (justificado e **implícito**, §3), P/E, dividend yield | ROTE ajustado por AT1 **[2b]**, eficiencia, crecimiento del margen de intereses (NII) | El P/E y el dividend yield **sí aplican** (decisión del usuario, registro #14). FCF, EV/EBITDA, márgenes, ROIC, ROCE: no |
| Aseguradora | P/B frente a ROE, P/E | Ratio combinado si existe (si no, "sin dato"), crecimiento de primas | |
| Conglomerado (BRK-B) | P/B (la métrica que usa la propia empresa), suma de partes como texto | La volatilidad de sus "ingresos" incluye plusvalías de cartera: la regla de ciclicidad (§1.2) debe excluir ganancias de inversión | Subtipo explícito, no "aseguradora" |

Crecimiento bancario medido con el **margen de intereses neto y las comisiones**, no con "Total Revenue" (RECON §7.8).

---

## 2. DCF inverso (D3)

### 2.1 Qué responde

"**¿Qué crecimiento exige el precio actual?**" En lugar de "vale X", el motor resuelve el crecimiento anual del FCF
(o de los ingresos con márgenes constantes) que, con el WACC y el crecimiento terminal del modelo, iguala el valor al
precio de hoy. Después lo compara con lo que la empresa ha logrado y con las tasas base.

### 2.2 Especificación

- Horizonte: 10 años, con **convergencia lineal** del crecimiento exigido al terminal en los años 6–10 (misma
  estructura que el DCF directo, para que sean comparables).
- Base: FCF normalizado (− SBC donde aplique; mantenimiento en cíclicas, ciclo medio), por acción.
- Solución numérica acotada (bisección) entre −20% y +60%; fuera de ese rango, "el precio no es reconciliable con un
  crecimiento razonable" (y se dice así).
- **Comparación** (la señal):
  - frente al CAGR histórico por acción (3 y 5–10 años **[2b]**) del FCF y de los ingresos;
  - frente a la tasa base: proporción de empresas comparables (por tamaño) que sostuvieron ese crecimiento 10 años.
- Bandas de lectura (calibrar):

| Crecimiento exigido frente al logrado | Lectura | Señal de precio |
|---|---|---|
| < logrado − 5 pp | El precio exige menos de lo que ya hace | barata |
| ± 5 pp | Exige continuar lo logrado | en precio |
| > logrado + 5 pp y tasa base razonable | Exige acelerar | exigente |
| Tasa base muy baja (pocas empresas lo sostienen 10 años) | Exige algo excepcional | muy exigente |

- **Texto obligatorio** (pasa por el guardián): "El precio actual exige que el FCF por acción crezca un X% anual
  durante 10 años; en los últimos N años creció un Y%."

### 2.3 Cómo entra en el veredicto

- El DCF inverso es el **método intrínseco** cuando el directo tiene fiabilidad baja (el grid no contiene el precio).
  Con eso, la convergencia vuelve a tener dos métodos.
- **Confianza (opción 3 de RECON §7.17):** la contracción del precio hacia 50 se aplica por **discrepancia entre
  métodos** o por datos débiles, **no** por la mera ausencia de un segundo método.
- Se mantiene el DCF directo en la tabla (con su fiabilidad) para quien quiera el "valor X".

---

## 3. Bancos: ROTE implícito

Con P/TBV = (ROTE − g) / (Ke − g) → **ROTE implícito = P/TBV × (Ke − g) + g**.
Ejemplo BCS (15-oct): 0.81 × (11.0% − 2.5%) + 2.5% ≈ 9.4%.

Lectura: "El precio descuenta un ROTE sostenido del 9.4%; el banco obtiene un X% (ajustado por AT1 **[2b]**)." Con
sensibilidad a ±2 pp de ROTE. **No** se usan objetivos de la gerencia como dato del modelo (no son verificables);
el informe puede mencionarlos como contexto si en el futuro hay fuente estructurada.

---

## 4. Crecimiento: base, convergencia y perímetro

- **Base por acción** siempre que la emisión o la recompra sea relevante (ya existe la regla del 2%).
- **Perímetro [2b]:** si hubo escisión o venta relevante, el crecimiento se mide sobre el perímetro homogéneo
  (operaciones continuadas, años reexpresados) o se declara "no comparable" y no puntúa. Caso: UL.
- **Convergencia en el DCF directo:** el crecimiento de entrada no se mantiene plano; converge al terminal (años 6–10).
  Si el crecimiento histórico incluye inflación de precios atípica (TXRH: carne), se dice como riesgo, no se ajusta
  a ojo.
- **Cíclicas (sustituye la cota −5%/+10%):** con 10+ ejercicios **[2b]**, el crecimiento de ciclo medio es la
  tendencia entre picos (o entre valles) del ciclo completo, y los márgenes de ciclo medio son la media del ciclo. La
  cota solo queda como salvaguarda con historia corta, y dicha como tal.
- **Base ≤ 0 (AMZN):** si el BPA o el FCF inicial es ≤ 0, la categoría Crecimiento usa el CAGR de ingresos por acción
  y lo declara; no se excluye la categoría entera.
- **MATURE de dividendo alto (≥ 4%):** el crecimiento se lee como retorno total (crecimiento + rentabilidad por
  dividendo), no solo crecimiento de ingresos.
- **Interanual frente a 3 años (AAPL):** si difieren más de 10 pp, el DCF usa una mezcla declarada o abre escenarios;
  nunca elige en silencio.

---

## 5. Lecturas que entienden el modelo de negocio

| Caso | Hoy | Propuesto |
|---|---|---|
| Current ratio < 1 en restauración, comercio, aerolíneas, software por suscripción (capital circulante negativo estructural) | "Tensión" | Lectura por industria: "normal en un negocio que cobra antes de pagar"; la alerta solo si empeora frente a su propia historia |
| Altman Z con pasivos por arrendamiento | Castiga restauración y comercio | Coherente con la regla de deuda de la 2b (arrendamientos operativos US GAAP fuera); en industrias para las que el modelo no se diseñó, "referencial" y no vota |
| Piotroski en esas industrias | Liquidez y margen bruto pesan igual | Sin cambio de método (es un modelo cerrado), pero el texto avisa de qué criterios son poco informativos para esa industria |
| Cobertura de intereses en utilities | Bandas generales | Bandas de utility regulada (ya existe en el score) también en la lectura y las alertas |
| Número de Graham en REIT | Se calcula con un BPA deprimido por la depreciación | No se muestra en REIT |
| SBC > 5% de ingresos en MATURE | No se resta | FCF − SBC en márgenes y DCF |
| Compromisos fuera de balance relevantes (MSFT 329 mil millones en arrendamientos no iniciados) | No aparecen | Texto de contexto en Solidez, sin entrar en ratios; requiere lectura de la nota o fuente alternativa |
| DuPont del ROE, margen FCF con tendencia | No existen | Lecturas de calidad (backlog aprobado) |

---

## 6. Cómo se verificará la fase 3

- **Panel (36 tickers):** tabla de arquetipo obtenido frente a esperado; cada cambio de arquetipo, calidad o precio
  explicado por una regla de este documento.
- **Revisión experta por arquetipo:** para un ticker de cada tipo, una ficha "cómo lo analizaría un analista" frente a
  lo que hace el motor (PLAN §4 fase 3).
- **DCF inverso:** contraste numérico independiente (hoja de cálculo o script aparte) en 5 tickers.
- **Revisión externa (punto 11):** 2–3 tickers fuera del panel que estresen los tipos nuevos (p. ej. un software de
  crecimiento rentable, una cíclica industrial, un banco europeo).

## 7. Dependencias de la 2b

| Pieza de la fase 3 | Necesita de la 2b |
|---|---|
| Ciclicidad con datos (§1.2), ciclo medio (§4) | Historia de 10+ ejercicios (EDGAR) |
| ROTE ajustado (§1.4, §3) | AT1 y cupones separados |
| Perímetro (§4) | Detección de operaciones discontinuadas y reexpresiones |
| Altman coherente (§5) | Regla de deuda coherente con el EBITDA |
| DCF inverso con CAGR largo (§2) | Historia por acción (acciones de EDGAR) |

---

## 8. Ajustes tras la muestra de F3prep (**decididos** el 2026-10-15: el usuario delegó en el planificador la opción recomendada)

La muestra (`F3PREP_MUESTRA.md`, rama `fiabilidad/f3-prep`) mostró que el contraste de §2.2 frente al CAGR de FCF a 3
años da lecturas erróneas: PLTR (+52.6% exigido frente a +108.6% logrado), NVDA y NFLX salen "baratas" por partir de
una base baja; KO (−17.8%) y NVO (−21.5%) salen "exigentes" por un FCF de 3 años distorsionado por pagos puntuales.

1. **Referencia principal = tasas base**, no el histórico corto de la empresa. La banda se decide por la proporción de
   empresas comparables (por tamaño de ingresos) que sostuvieron el crecimiento exigido 10 años. El histórico propio
   (5–10 años **[2b]**, en **ingresos por acción**, más estable que el FCF) es la segunda referencia y nunca hace
   "barata" una exigencia que las tasas base consideran excepcional.
2. **Una sola estructura de DCF** para el directo y el inverso: crecimiento constante años 1–5 y convergencia lineal
   al terminal años 6–10. Se retiran los decaimientos lineal (> 15%) y exponencial (> 25%) desde el año 1.
3. **Topes:** el ±60% del inverso es solo el dominio de búsqueda; "exige más de +60%" se informa como tal. La
   plausibilidad la juzgan las tasas base, no un tope. El `growth_cap` del directo se revisa en la unificación.
4. **FCF − SBC siempre** que haya dato de SBC (coste real), en todos los arquetipos con DCF; sin umbral.
5. **Cíclicas, dos lecturas del inverso:** con el FCF de mantenimiento de ciclo medio ("qué exige el precio en un año
   normal") y con el FCF TTM ("qué exige si el nivel actual se mantiene"). MU: el precio solo se justifica si el pico
   actual persiste.
6. **Financieras cautivas** (CAT, DE, F, GM): la deuda de la financiera no entra en la deuda neta industrial del DCF
   ni en las ratios de apalancamiento; requiere separar los datos por segmento **[2b]**.
7. **REIT:** si se aplica el inverso, sobre FFO/AFFO por acción, no sobre FCF.
8. **Aseguradoras (PGR):** el ROE implícito se contrasta con el ROE medio del ciclo de suscripción, no con el de un
   año.
