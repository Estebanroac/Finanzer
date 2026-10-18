# Aprobaciones del PM en el rediseño (v4)

Delegación del usuario, literal (2026-10-17, en la sesión del PM): «recuerda, que esto se autoapruebe. confío
plenamente en ti. no me vuelvas a avisar hasta que todo el plan esté 100% hecho. y que el último paso sea solo migrar
del modelo actual al nuevo si el nuevo marcha de maravilla». La migración (E6) queda fuera de esta delegación: requiere
el visto bueno del usuario tras probar la v4.

Cada aprobación se verificó en la sesión del PM antes de darla (comparación independiente de veredictos en los golden,
revisión de capturas o del diff).

| Fecha | Qué | Rama / commit | Verificación del PM |
|---|---|---|---|
| 2026-10-17 | E1 (sistema visual y página-historia) | `rediseno/e1-sistema-historia` 966f576 | «aprobado» literal del propio usuario en la sesión de E1 |
| 2026-10-17 | Golden E2a (textos A–C, noticias D y D2, claves aditivas E) | `rediseno/e2a-datos-motor` 4ac27c6, 7784935 | 0 cambios de veredicto en 43 golden frente a main (script propio) |
| 2026-10-17 | E2b (segmentos, rivales, tendencias) y emparejamiento tolerante de ADR (golden sin cambios) | `rediseno/e2b-segmentos-rivales-tendencias` 9c6be6d | revisión de salidas de los 8 tickers; diff_golden sin diferencias |
| 2026-10-18 | E5 (PDF nuevo), hueco al pie ≤ 106 pt | `rediseno/e5-pdf` 8b9fb00 | revisión de las 21 páginas de AAPL y de BCS |
| 2026-10-18 | E3 (9 páginas de profundidad) y golden E3 (solo altas en `scenario_inputs`) | `rediseno/v4` 4b96e78, 203b086 | 0 cambios de veredicto en 43 golden frente a main; capturas revisadas. (La cita no figura dentro de `GOLDEN_DIFF_E3.md`: los permisos de la sesión operadora bloquean escribir una aprobación recibida de otra sesión; vale este registro.) |
| 2026-10-18 | Golden de texto `panel_pdf_v2` con los datos de E2 | `rediseno/v4` 328d3b3 | revisión del operador: solo bloques con dato |
| 2026-10-18 | E4 (portada, cola compartida, servido de /v2, móvil, oscuro) | `rediseno/e4-portada` 4dd7512, 84c877d · `rediseno/v4` 3c8a3a7 | capturas y Lighthouse revisados |
| 2026-10-18 | P8 (encargo): portada con cintillo rotativo y mini-gráficas 1D/1S/1M/6M, pedida por el usuario («hasta el momento me gusta mucho… seria increible si nos traemos las graficas…») | `rediseno/e4-portada` (pendiente) | maqueta del PM; se revisará con capturas, e2e y Lighthouse antes de fusionar |
| 2026-10-18 | V7 · P2–P6 (presentación: glosario, concentración, rivales en capítulo 6, segmentos en capítulo 2, Enter/PDF/cabecera compacta) | `rediseno/v4` 5779ae5 | 4819 tests, e2e:v2 662/0, diff_golden sin cambios; aprobado con condición: nota de calidad de KO arreglada en origen, no relajando el test |
| 2026-10-18 | V7 · índice sin «Resumen», regla general de página nueva, «?» en las puntuaciones y «(sigue)» en filas partidas | `rediseno/v4` a389397, 408597e, 3e91dea | captura de KO p1–3 revisada; 4857 tests |
| 2026-10-18 | V7 · M1–M3 (DCF en %, periodos, etiquetas) | `rediseno/e4-portada` d97fe55, 6e4f2fd, ca7259c | GOLDEN_DIFF_V7: 0 cambios de veredicto |
| 2026-10-18 | V7 · M4–M7, M5 bis, P8 (cintillo, mini-gráficas, sectores) y P (puntuación) | `rediseno/e4-portada` 0b83184, e8fa669, 4f86cec, de05dbe, e7cfa4d, eb02c65, e310768 | 0 cambios de veredicto; capturas P8 revisadas (3 retoques pedidos). Excepción aceptada: P toca 3 componentes de la web actual (charts, GrowthTab, InstitutionalTab) solo para no duplicar el punto que ahora pone el motor compartido; sin cambio visual |
