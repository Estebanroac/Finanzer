# F14 · Paso 1: la tasa libre de riesgo, de la hoja de Damodaran (6-nov-2026)

Segunda revisión externa (`informes-pdf/Revision_Finanzer_v2_2026-11-06.pdf`, punto 1 de su sección 3). Aprobado por el
usuario: «Sí, paso 1».

## Qué estaba mal

El Ke, el Kd y el WACC usan el par Rf–prima de Damodaran de la misma fecha (F8 · E1). El 5-nov (F13 · paso 1) se copió
de su portada: «Implied ERP on November 1, 2026 = 4.41% … with the US treasury rate of 5.29% used as the riskfree rate».

El 5,29 % era el texto de octubre sin actualizar. La hoja con la que Damodaran calcula la prima dice otra cosa:
- `ERPNov26.xlsx`, «Enter current 10-year US treasury rate» = **4,94 %**;
- `ERPbymonth.xlsx`, hoja «Historical ERP», fila del 1-nov: «T.Bond Rate» 4,94 %, prima 4,41 %; la del 1-oct, 5,29 % y
  4,20 % (la de octubre sí era correcta).

Las 102 empresas con coste de capital llevaban 35 pb de más en el Rf. El aviso de deriva frente al ^TNX del día (4,84 %)
no saltó: 0,45 pp, por debajo de su umbral de 0,5 pp.

Copias de las dos hojas: `archivo-historico/evidencias-de-pruebas/revision_v2_2026-11-06/damodaran/`.

## Qué cambia

- **`tools/damodaran_erp.py`**: lee la hoja mensual de Damodaran, sin dependencias.
  - Toma la última fila: el mes, el «T.Bond Rate» y la «ERP (T12 m with sustainable payout)», que es la prima que
    publica en la portada.
  - El libro usa fechas de 1904.
  - Con `--write`, escribe la serie en `tests/fixtures/damodaran/erp_by_month.csv` y actualiza a la vez el par
    (`valuation.toml`) y sus fechas (`review.toml`).
- **Par:** Rf 5,29 % → **4,94 %**; la prima sigue en el 4,41 %. La fuente de `review.toml` apunta a la hoja, no a la
  portada.
- **`tests/test_damodaran_erp.py`** (4 tests):
  - el par de la configuración tiene que ser la fila de su fecha en la hoja;
  - las fechas de la revisión siguen al par;
  - el caso del 1-nov;
  - el lector maneja las fechas de 1904.

  Un par copiado a mano de la portada falla.

Ajustes del evaluador (respuesta del 6-nov), aplicados en este mismo paso:
- **Aviso de deriva: de 0,5 a 0,3 pp** (`pair_drift_warning`). Con 0,5 pp no saltó por 5 pb; con 0,3 pp habría
  saltado. Test: `test_drift_warning_catches_a_pair_copied_wrong`. Hoy (^TNX 4,84 % frente a 4,94 %) no salta.
- **La herramienta avisa si el Rf repite el del mes anterior**, que fue la señal que delató el error. No escribe sin
  `--igual-comprobado`.
- **El paso 1 va solo y se mide antes del 2.**

## Efecto en las 110 congeladas (base F14 = paso 12 de F13 → paso 1)

- Cambian 24 empresas. Tres bandas de precio se mueven, las tres hacia barata:
  - KMI: exigente → razonable;
  - MRK: muy exigente → exigente;
  - T: razonable → atractivo.
- El WACC baja entre 0,1 y 0,4 pp. Las mayores bajadas:
  - LMT: 9,3 % → 8,9 %;
  - WELL: 7,3 % → 6,9 %;
  - T: 6,7 % → 6,3 %.
- Confianza: baja 69 → 66, media 34 → 38, alta 7 → 6 (PG pasa de alta a media).
- Reglas de cordura: ninguna empeora; `crecimiento_dcf_representativo` pasa de 12 a 10.

- **Contracción hacia 50:** cambia la banda de 31 empresas, frente a 33 en la base. Salen BAC, CL, SRE y T; entran LMT
  y MRK. Las «razonable» que vienen de otra banda son 13: AEP, BMY, CRM, CSCO, CVX, EOG, LMT, NUE, O, PEP, TGT, VZ y
  XOM. Es el punto de partida del paso 4.

  En producción eran 29 y 13. El banco congelado es la captura del 5-nov y difiere en algunas empresas.

- **Panel (golden):** cambian 4 veredictos, los cuatro hacia barata:
  - PG: muy exigente → exigente;
  - BAC: exigente → razonable;
  - UL: exigente → razonable;
  - O: razonable → atractivo, y su calidad pasa de media a sólida.

  Golden regenerados: panel, local, forzados y PDF v2. Suite: 6704 passed, 19 skipped.

AT&T sube a «atractivo» con su DCF todavía sin restar el espectro: eso es el paso 5, no este.

Tabla: `archivo-historico/evidencias-de-pruebas/f14_banco110_2026-11-06/paso1_vs_base.md`.
