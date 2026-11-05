# F13 · Paso 6: utilities, tipo fiscal recurrente, espectro e IPR&D (5-nov-2026)

Familia G de la revisión de 110 empresas: ajustes que dependían de la empresa y no de la industria. Son cuatro:
(6a) utilities con «Destruye valor», (6b) la normalización restando beneficio recurrente a las utilities, (6c) el
espectro de las telecom y (6d) IPR&D.

## 6a · Utilities sin el diferencial ROIC − WACC

`config/sectors.toml [archetypes.not_applicable] UTILITY` añade `roic_wacc`, con su motivo en `classify`: «el
regulador fija el retorno que puede obtener sobre su base de activos; un ROIC por debajo del WACC de mercado es la
tarifa autorizada, no destrucción de valor».

En las 10 utilities del banco se retira la alerta «Destruye valor» (spread de −1,2 a −3,6 pp) y su resta en la nota,
de −1 a −4. Con el diferencial no aplicable, el ROE ya no se cambia por el ROIC por apalancamiento (F8 · E9): puntúa el
ROE, que en una utility regulada es el retorno autorizado. Regla `utility_regulada`: 10 → **0**.

## 6b · Residuo de la normalización en utilities: medido

Medido contra los companyfacts completos de EDGAR de las 10 utilities. Hay **dos causas distintas**, las dos en origen.

**1 · Créditos fiscales recurrentes (corregido).** `normalize.tax_rate_normalized` descartaba todo tipo efectivo
negativo, aunque su propio docstring dice que un beneficio fiscal recurrente (créditos fiscales de una utility) es su
tipo. Con todos los años negativos caía al tipo legal del 21 %, y la normalización quitaba los créditos como «beneficio
que la operación no explica».

- XEL: tipo efectivo de −4,6 %, −8,4 %, −9,0 %, −26,2 % y −13,8 % en 2021–2025. Créditos fiscales de 0,57 B$ y AFUDC
  de capital de 0,28 B$ en 2025, frente a un residuo de 0,60 B$.
- Ahora los tipos negativos entran en la mediana si no bajan de `tax_median_floor` = −30 %. Por debajo no son un tipo
  sino un suceso, y quedan fuera: es el caso de UBER, con la liberación de la provisión por activos fiscales diferidos
  (−46 % a −140 %), y sus tests de F10 siguen en pie. Un beneficio fiscal puntual sigue fuera, porque se usa la mediana
  de 5.

| Empresa | P/E normalizado | Residuo quitado | Forward P/E |
|---|---|---|---|
| XEL ★ | 28,3x → **21,1x** | 0,60 B$ → nada | 17,8x |
| PCG | 15,8x → 13,2x | 0,48 B$ → nada | 7,4x |
| NEE | 17,1x → 16,4x | 0,67 B$ → 0,25 B$ | 19,3x |
| AMD (cíclica, beneficios fiscales recurrentes) | 113,6x → 105,4x | 0,46 B$ → nada | 39,8x |

**2 · Participadas después de impuestos (SRE): sin cambiar, decisión pendiente.** Sempra presenta las ganancias de
Oncor (participada regulada al 80 %) **después** del beneficio antes de impuestos: 1,6 B$ al año en EDGAR,
`IncomeLossFromEquityMethodInvestments`. Yahoo no las trae y la fórmula las lee como un beneficio fiscal, así que la
normalización quita 1,08 B$, el 48 % del beneficio (P/E normalizado de 34,3x frente a un forward de 15,7x). Aun
trayéndolas de EDGAR, el diseño de F10 trata las participadas netas de impuestos como no operativas y las recorta (era
el caso FIS: su participación en Worldpay). **Hace falta decidir** si una participada de la misma industria (Oncor
para Sempra) cuenta como operativa. Mientras tanto, la base frágil del paso 3 ya deja la confianza de SRE en «media»
como máximo. Regla `normalizacion_utility`: 3 → **1** (SRE).

## 6c · Espectro solo en operadoras

`telecom_spectrum.adjustment` recibe la industria de Damodaran. Si la empresa está clasificada, solo ajusta en
`damodaran_industries` = «Telecom. Services» y «Telecom (Wireless)».

- **CMCSA:** Yahoo la pone en «Telecom Services», pero Damodaran en «Cable TV». Ya no se le resta como espectro una
  media de 2,5 B$ que en Comcast es **software**. Su veredicto no cambia.
- **Anotado:** el software capitalizado (CMCSA 1,6–3,3 B$/año) sigue fuera del capex en todas las empresas. Es una
  inversión recurrente, y entra en la definición del capex, no en el espectro.
- **AT&T, pendiente.** Etiqueta sus compras de espectro con una extensión propia: no hay ningún concepto estándar de
  pagos por espectro o intangibles en sus companyfacts. Sigue «sin dato» y lo declara (no se suponen ceros). Leerla
  exige ir a la instancia de cada 10-K (`sec_edgar.instance_facts`, unos 4 informes para 10 años) y volver a capturar
  el banco. Regla `espectro_coherente`: sigue en 1 (T).

## 6d · IPR&D: medido, sin cambio

MRK y ABBV etiquetan la I+D adquirida con el mismo concepto estándar
(`ResearchAndDevelopmentAssetAcquiredOtherThanThroughBusinessCombinationWrittenOff`), y a las dos se les aplica la
misma regla: si el cargo es recurrente, solo sale lo que pasa de su propia media.

| Empresa | Serie anual | TTM | Qué sale |
|---|---|---|---|
| ABBV | 0,7–5,0 B$ todos los años | 2,5 B$, en su media | nada |
| MRK | 1,6 / 0 / 11,4 / 3,5 / 0 B$ | 13,8 B$ (Verona) | el exceso: 7,7 B$ netos |

La diferencia que vio el revisor es la regla funcionando, no una asimetría. Medir la recurrencia por tipo de cargo y no
sobre la suma apenas cambiaría estos dos casos: queda como mejora, no como error.

## Efecto en las 110 congeladas (paso 5 → 6)

Ninguna banda de precio ni de confianza cambia. Calidad:

| Empresa | Antes | Después |
|---|---|---|
| EXC | media | **sólida** |
| PCG | débil | **media** |
| XEL ★ | débil | **media** (nota de precio de 38 a 40) |

XEL sigue con confianza «baja»: la base frágil del paso 3 (caja libre −7,6 B$) y el limitador de Ke.

Tabla y corridas: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso6_vs_paso5.md` y `paso6/`.

## Golden

| Golden | Qué cambia |
|---|---|
| panel NEE | Sin «Destruye valor». Puntúa el ROE normalizado (14,1 %, excepcional para su sector) en lugar del ROIC apalancado, y desaparece el techo de rentabilidad de 10/20 por ROIC < WACC. Tipo normalizado de 13,8 % a 5,6 % (2025: −17,7 %): P/E normalizado de 21,8x a 20,3x. **Calidad de media (55) a sólida (66)**, en la frontera; precio y confianza iguales |
| panel DUK | Sin «Destruye valor»; puntúa el ROE (8,9 %). Rentabilidad de 10/20 a 15/20 |
| panel DOW, CRWD, NVDA | Solo el tipo de la normalización: con los tipos negativos dentro de la mediana hay suficientes válidos (DOW 23,8 %, CRWD 30,5 % en lugar del legal; NVDA de 14,2 % a 13,3 %). Ningún veredicto cambia |

PDF v2 regenerado (NEE, DUK).

Tests: `tests/test_f13_paso6.py` (5). Suite: 6654 passed.
