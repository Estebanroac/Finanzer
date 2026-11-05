# F13 · Paso 2a: rating sintético con el beneficio limpio (5-nov-2026)

Patrón 3 de la revisión de 110 empresas: un beneficio operativo contable hundido por partidas sin caja (deterioros,
cancelación de proyectos; en REIT, la depreciación inmobiliaria) daba rating D o CC, y el piso Ke ≥ Kd + 1 pp llevaba
el WACC a su tope (KHC, APD, MOS, F: 20 %; WELL: 18,5 %).

## Qué cambia (`lib/cost_of_capital.rating_coverage`, `main.py`)

La cobertura con la que se busca el rating sintético (Kd y, por su piso, el Ke) es, por orden:
1. **REIT:** EBITDA / intereses.
2. **EBIT normalizado** / intereses, si es mayor que el contable. Es el operativo sin los cargos que la normalización
   ya quita (los mismos de la etapa 7, con lo que va por debajo de la línea separado: INTC queda en 6,0 B$ y no en 18,9).
3. Si aun así sale **CCC, CC, C o D con la caja operativa positiva**, el rating es incoherente y se busca con la
   cobertura de caja: (flujo operativo + intereses − D&A) / intereses, en la escala del EBIT.

Para que el rating lo use, la normalización de ganancias se calcula ahora **antes** del coste de capital. El bloque de
la etapa 7 usa ese mismo resultado: no se recalcula ni cambia ninguna cifra de la normalización (comprobado en el
golden). La nota y las alertas siguen con la cobertura contable: este paso es solo el coste de la deuda. La nota del
WACC dice con qué se midió la cobertura cuando no es el EBIT contable, y cuánto daba el contable.

## Efecto en las 110 congeladas (paso 1 → 2a)

- Cambian 20 ratings y 5 veredictos; 3 bandas de precio van hacia «barata».
- **Los cinco WACC del tope se corrigen:** KHC D → A+ (7,0 %; precio razonable → atractivo; DCF −95 % → +63 %),
  APD D → AA (8,6 %), WELL CC → A- (7,3 %), MOS D → B- (9,9 %; razonable → atractivo con el flujo medio del ciclo,
  P/FCF normalizado 6,3x), F D → B- (9,0 %; exigente → razonable).
- REIT con EBITDA: DLR B → A+, CCI BB → BBB, O BB+ → A, EQIX A- → AA, AMT, PLD, PSA, SPG un escalón.
- Normalizado: INTC B- → A, MRK A- → AAA, PFE A+ → AAA, DOW BB+ → A-, D B+ → BB, SRE BB → BBB.
- GM BBB → AAA y F B-: sus intereses no incluyen los de la financiera cautiva (paso 2b).
- La regla `rating_contable` del paso 0 pasa de 6 (APD, F, KHC, MOS, WBD, WELL) a 1 (WBD, que el paso 8 dejará sin
  veredicto por falta de datos).

Tabla: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso2a_vs_paso1.md`.

## Golden

Nuevo bloque `wacc.rating_coverage` en todos. Cambian el rating y el WACC de O (BB+ → A), PLD (A → AA) y AMT (A- → A),
y la cobertura de V y UL (sin cambiar su rating). Ningún veredicto cambia. Suite: 6630 passed. Tests:
`tests/test_f13_paso2.py`.
