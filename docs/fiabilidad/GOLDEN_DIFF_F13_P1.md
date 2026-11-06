# F13 · Paso 1: par Rf–ERP de noviembre y alarma de vencimiento (5-nov-2026)

## Qué cambia

- **Par Rf–ERP de Damodaran a 1-nov-2026:** prima implícita **4,41 %** (antes 4,20 % a 1-oct), con el **mismo** Tesoro
  a 10 años de **5,29 %** como Rf (fuente: Damodaran Online, *New_Home_Page/home.htm*, consultada el 5-nov). Actualizado
  en `config/valuation.toml` y `config/review.toml`, con su fuente y fechas.
- **Alarma de vencimiento en ejecución** (decisión del usuario): `lib/parameter_review.py` (la lógica de la herramienta
  de revisión, ahora en `lib/`). `cost_of_capital.capm_rates` añade `risk_free.review` y, si el par está vencido, lo
  dice en `risk_free.reason` y en los avisos de la portada (`display.data_notices`). El test
  `test_market_pair_is_not_overdue_today` **falla** el día en que vence la revisión mensual. En el replay, la
  revisión se juzga el día de la captura de cada ticker: los golden no dependen del día en que corre la suite.
- La revisión del 1-nov venció el 2-nov sin que nada lo avisara. Con este paso, eso ya no puede pasar en silencio.

## Efecto en las 110 congeladas (`tests/f13_comparar.py`, antes 69e76bd6 → paso 1)

- **Ninguna cambia de banda de precio**: muy exigente 27, exigente 38, razonable 34 y atractivo 9, igual que antes.
- Confianza: baja 58 → 61, media 39 → 36 y alta 13 → 13 (con movimientos en las dos direcciones).
- Cambian 12 empresas, solo en notas, confianza o calidad. Ke +0,21 pp × β; WACC +0,1–0,2 pp. CL y PM pasan de
  calidad «excelente» a «sólida» (el diferencial ROIC − WACC). V: nota de precio de 16 a 5. MCD y V suben de confianza
  (el limitador de Ke deja de saltar); AMGN, CL, PM, RTX y SBUX bajan.
- **Conclusión para la decisión 4 (E7):** el par no explica el sesgo hacia «caro». Ahora lo confirma la medida, no solo
  el razonamiento: la prima nueva lo endurece ligeramente.

Tabla completa: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso1_vs_antes.md`.

## Golden (fixtures congelados)

Cambian todos los que tienen WACC (la prima entra en cada Ke): notas de valoración algo más bajas y textos con el Ke y
el WACC. El único veredicto que cambia es **O** en el panel (fixture de octubre): de «sólida · atractivo (media)» a
«media · razonable (baja)». Ya estaba en la frontera del limitador de Ke. Sin cambios en la estructura.
