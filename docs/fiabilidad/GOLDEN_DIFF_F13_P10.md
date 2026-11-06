# F13 · Paso 10: riesgos del sector, aplicados como se decidió (5-nov-2026)

Medida previa y propuesta: `F13_P10_RIESGOS_MEDIDA.md`. Decisión del usuario: «Sí, aplicar así». Eso es: a nivel 1, la
refinanciación; a nivel 2, solo los incendios y los huracanes; los riesgos que saldrían en el 100 % de su industria
quedan fuera.

## Qué cambia

- **`lib/sector_risks.py`**, aparte y sin puntuar: ni la calidad ni el precio lo cuentan.
  - **Nivel 1 · refinanciación.** Salta si se cumplen las dos condiciones:
    - la deuda que vence en 24 meses supera la caja (año 1 + año 2 + papel comercial + préstamos a corto, del último
      balance anual en EDGAR, con conceptos us-gaap estándar: `sec_edgar.MATURITIES`);
    - el rating sintético del motor es especulativo (BB+ o peor).

    No en financieras, utilities ni REIT. Un balance de más de ~15 meses no se lee. El texto da las cifras, la fecha
    del balance, la caja, el rating y la cobertura.
  - **Nivel 2 · industria** (`config/sectors.toml [sector_risks.industry]`): incendios forestales (utilities con sede
    en el oeste de EE. UU.) y huracanes (golfo y atlántico sur). Llevan la etiqueta «riesgo de la industria, no
    verificado en esta empresa» y dicen que la sede no siempre es el territorio que sirve. La industria de Yahoo llega
    con raya o con guion según la vía («Utilities—Diversified»): se normaliza.
  - **No medido** (se dice, no se estima): la concentración en un inquilino o en un producto.
- **Dónde se ve:**
  - en la vista, `display.sections.sector_risks`;
  - en el PDF v2, el capítulo de riesgos, «Riesgos del sector (no puntúan)»;
  - en la web, la página Riesgos, con la sección «Riesgos del sector (no puntúan)», su píldora «Del sector», el nivel
    («De la empresa» / «De la industria»), la etiqueta y el «No medido».
- **Fixtures:** a los companyfacts congelados (banco de 110 y tests) se les añaden solo los cuatro conceptos de
  vencimientos, con los hechos presentados hasta la fecha del último hecho que ya tenía cada fichero. El resto no se
  descongela.

## Efecto en las 110 congeladas (paso 9 → 10)

Ningún veredicto cambia: los riesgos del sector no puntúan.

| Riesgo | Empresas |
|---|---|
| Refinanciación (nivel 1) | **MOS**: vencen 1,53 B$ en 24 meses frente a 0,29 B$ de caja, rating sintético B− |
| Incendios (nivel 2) | PCG, SRE |
| Huracanes (nivel 2) | DUK, NEE, SO |

Vencimientos leídos en 79 de las 110. Con deuda a 24 meses por encima de la caja pero rating de grado de inversión
quedan fuera, como se quería: VZ (A−), HD, CAT, LIN, PM (AAA), T (A−) y otras 16.

## Golden

Todos los análisis llevan el bloque nuevo (`sector_risks`, con `debt_due`), así que se regeneran todos los golden
(local, panel, forzados y PDF v2). De fondo, en el panel: **NEE** y **DUK** tienen «Huracanes», con su etiqueta, en el
capítulo de riesgos del PDF, que gana una página. El guardián exige declarar todo texto de 4 palabras o más: `lib/prose.py`
declara `sections.sector_risks.not_measured` como fragmento. Suite: 6685 passed.

Tests:
- `tests/test_f13_paso10.py` (6);
- web: `src/v2/pages/Riesgos.test.tsx` (2). Tipos, lint y 173 tests de la web, en verde.
