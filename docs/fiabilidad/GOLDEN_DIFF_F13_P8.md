# F13 · Paso 8: sin veredicto de precio sin precio de hoy, y sin beta negativa (5-nov-2026)

Familia F de la revisión de 110 empresas: EA y WBD recibían «precio exigente» con un perfil vacío y un solo precio en
el historial, y WBD llevaba una beta negativa al coste del capital.

## Lo que pasaba (banco de 110, paso 7)

- **EA:** un solo precio, del 4 de agosto de 2026, 93 días antes que la última sesión del mercado (5-nov). La empresa
  está en una operación corporativa y su cotización ya no es activa. Perfil vacío («Unknown»).
- **WBD:** igual, con el último precio del 5 de octubre de 2026 (31 días). Beta de Finnhub de −0,60, sin regresión
  propia (0 semanas) ni industria de Damodaran. Con Blume daba −0,07 y un CAPM del 5,0 %, por debajo de Rf; el piso Kd
  + 1 pp lo tapaba (Ke del 15,1 %).
- KVUE, citada en la revisión, no está en el banco de 110.

## Qué cambia

- **Abstención del veredicto de precio** (`verdict.abstention`, `verdict.abstain`). No hay veredicto de precio en dos
  casos:
  - la cotización lleva más de `thresholds.score.price.abstain_stale_days` = 10 días sin sesiones frente al mercado;
  - no hay perfil ni `abstain_min_sessions` = 20 sesiones de historial.

  El veredicto dice «precio sin veredicto» con el motivo en lugar de la confianza, por ejemplo: «la cotización no tiene
  sesiones desde el 4 de agosto de 2026, 93 días antes que el mercado: el precio no es de hoy y no se compara con el
  valor». La puntuación cruda queda como referencia. `reprice` (la sensibilidad a Ke) no la reabre. En el texto de la
  confianza ya no aparece «Contrae el atractivo del precio hacia 50: de 20 a None».
- **Beta negativa de la fuente fuera del CAPM** (`beta.choose`). Sin beta propia ni industria, una beta negativa de la
  fuente queda «sin dato» con su motivo, y el Ke usa la beta de mercado por defecto. WBD: CAPM del 5,0 % al 9,7 %; su Ke
  sigue en el 15,1 % por el piso de Kd + 1 pp.

## Efecto en las 110 congeladas (paso 7 → 8)

| Empresa | Antes | Después |
|---|---|---|
| EA ★ | sólida · exigente (baja) | sólida · **precio sin veredicto** |
| WBD ★ | débil · exigente (baja) | débil · **precio sin veredicto** |

Reglas: `abstencion_sin_datos` 2 → **0**; `beta_sin_signo_negativo` 1 → **0**. Ninguna otra empresa cambia.

El PDF v2 de EA y WBD se genera sin errores: dice el motivo en el veredicto, y «precio —/100» en la puntuación.

Tabla y corridas: `archivo-historico/evidencias-de-pruebas/f13_banco110_2026-11-05/paso8_vs_paso7.md` y `paso8/`.

## Golden

Ningún golden cambia: ninguna de las empresas del golden tiene la cotización parada ni beta negativa.

Tests: `tests/test_f13_paso8.py` (4). Suite: 6664 passed.
