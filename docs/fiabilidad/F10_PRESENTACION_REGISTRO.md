# F10 · Presentación (N5 y N6): registro

Rama `fiabilidad/f10-presentacion` desde `rediseno/v4-f8` en e20de9f8. Encargo: revisión externa de NVIDIA
(`docs/fiabilidad/revision-nvda-2026-10-28.md`, plan `docs/superpowers/plans/2026-10-28-fiabilidad-revision-nvda.md`).
Cambios de golden con su causa: `GOLDEN_DIFF_F10.md`.

## N5 · Rivales «aún no estaban listos» en el PDF

### Diagnóstico (NVDA en vivo, en proceso, 28-oct)

- La web solo pedía los rivales (`/api/v2/peers`) desde la página **Rivales** (`PeersTable` → `usePeers`). Quien veía
  el análisis y descargaba el PDF sin abrir esa página no los ponía nunca en marcha: `peers.cached_for` devolvía
  `None` y el PDF decía «aún no estaba listo».
- Con la página abierta, la primera consulta solo encolaba la **clasificación por tamaño**; los rivales iban a la cola
  en la consulta siguiente del sondeo (cada 4 s).
- Línea de tiempo medida (NVDA, proceso nuevo, datos de mercado en caché de disco):

  | t | Hecho |
  |---|---|
  | 4,6 s | análisis del usuario servido; `cached_for` = None |
  | 35,7 s | clasificación hecha: 21 capitalizaciones de Finnhub × 1,5 s (`finnhub_min_interval_s`) |
  | 36,7–50,8 s | AVGO, MU, AMD, INTC y TSM analizados de uno en uno (2–4 s cada uno con caché; 15–20 s en frío) |

  En producción, en frío, eso da los p50 110–135 s de la revisión: unos 30 s de capitalizaciones (la primera vez
  en 7 días) más un análisis completo por rival en la cola de un hilo.

### Arreglo (config `market.toml [peers]`)

1. **Con el análisis** (`start_with_analysis = true`): `/api/analysis` deja el resumen de la empresa en la cola
   compartida (`analysis_queue.store`: la clasificación no repite el análisis) y pone en marcha sus rivales con
   prioridad `user`, que adelanta al precalentado de tendencias (`peers.start`).
2. **La clasificación encola a sus rivales** en cuanto termina (`peers._do_rank`), con el cupo del mismo cliente.
3. **Espera acotada en el PDF** (`pdf_wait_s = 30`, mirando cada `pdf_poll_s = 1`): `peers.for_pdf` consulta como la
   web (encola lo que falte, sustituciones incluidas) hasta que todo está listo o se acaba el plazo. Va **entre** los
   dos turnos del semáforo (el análisis y el PDF), nunca dentro: mientras espera, la cola puede analizar a los
   rivales.
4. **Rivales de la caché y los que faltan, declarados**: el capítulo de Rivales pinta los listos y nombra cada uno
   que falta con su motivo («DELL: aún en cola», «HPQ: no se pudo analizar (motivo)»); sin tabla, dice por qué (la
   clasificación aún no había terminado tras esperar N s, o los rivales aún se analizaban) y remite a la web.

El ritmo de Finnhub no cambia (1,5 s entre capitalizaciones: 40/min, por debajo de los 60/min gratuitos).

### Verificación en vivo (NVDA)

| PDF pedido | Tardó | Rivales |
|---|---|---|
| justo tras el análisis | 31,7 s | ninguno: «la clasificación de sus rivales por tamaño aún no había terminado tras esperar 30 s» |
| a los 15 s | 12,4 s | AVGO, MU, AMD, INTC y TSM |
| a los 90 s | 0,3 s | los cinco, sin esperar |

## N6 · Menores

| Punto | Antes (NVDA) | Ahora |
|---|---|---|
| ROE «amplificado por recompras» | «Un nivel tan alto suele estar amplificado por una base de patrimonio reducida por recompras acumuladas» con un apalancamiento DuPont de 1.31 | El DuPont decide (`thresholds.alerts.roe.amplified_leverage_min = 3.5`): NVDA «No lo infla un patrimonio reducido (DuPont de FY2026: apalancamiento 1.31): sale del margen neto (55.6%) y de la rotación de activos (1.04) de ese ejercicio». Revisada la plantilla: «elevado» solo menciona el patrimonio reducido con ese apalancamiento; el ROE negativo con ROA positivo se atribuye al patrimonio negativo, no a recompras que no se miden |
| PEAD con el trimestre natural | «trimestre cerrado el 2026-06-30» (la fecha de Finnhub) | «trimestre fiscal cerrado el 2026-07-26»: el periodo del 10-Q/10-K de EDGAR más cercano a la fecha de Finnhub (`pead_fiscal_match_days = 46`); sin su 10-Q aún, «trimestre cerrado el … según Finnhub (su 10-Q aún no está en la SEC)». La ventana del 8-K cuenta desde el cierre fiscal (MU, antes «sin dato» porque su 8-K caía el mismo día que la fecha de Finnhub, ahora se mide) |
| Nota de persistencia | «Por encima de 80, la calidad exige persistencia» | «Por encima de 80 (umbral de persistencia; «excelente» empieza en 85), …» (los dos de config) |
| Motivo de la confianza | «baja (techo en baja: techo de la confianza; sin techo sería alta)» | «baja (por sus dimensiones sería alta; la limitan: la convergencia es media —alta exige convergencia alta—, hasta media; el veredicto depende de Ke —el nivel de precio pasa de «razonable» a «atractivo» con Ke − 1 pp—)». Sigue en la primera frase del resumen: la línea de la portada (web y PDF), que la omite, no cambia |

Causa del motivo vacío: el resumen buscaba un techo con el nivel final («techo en baja»), pero el último escalón lo
puso la sensibilidad a Ke (F8 · E1), que no es un techo; ahora se cuentan todos los pasos en orden.

## Commits

| Commit | Punto |
|---|---|
| b4b3807f | N5 · rivales con el análisis y espera acotada en el PDF |
| 284bd31b | N6 · ROE «amplificado» solo con el apalancamiento DuPont |
| 40123f52 | N6 · PEAD con el trimestre fiscal real |
| 8f40b0f6 | N6 · la nota de persistencia nombra su umbral |
| 3e4b61e6 | N6 · el motivo de la confianza dice qué la limita |
| 56253a67 | N6 · PEAD: redacción sin 10-Q que cita «cerrado el <periodo>» (la comprobación del guardián) |
| 4d1e1ae3 | N6 · persistencia: la nota del PDF clásico con el interlineado de su cuerpo (NFLX, página 2 a 0.848) |
| 070b1342 | N6 · confianza: motivo más corto (la fila de XOM saltaba de página en el PDF nuevo) |
| 997f52ab | fixtures del frontend |

Cada commit lleva sus golden regenerados (sin red, desde los fixtures). Ningún veredicto ni puntuación cambia.

## Suites (sobre 997f52ab)

- Backend: 6114 passed, 9 skipped (la primera pasada destapó tres efectos de maqueta y redacción, corregidos en
  56253a67, 4d1e1ae3 y 070b1342).
- vitest: 142 passed.
- e2e v2 (replay en 8781, web en 3011): 826 passed, 642 skipped (los condicionales de siempre), 0 fallos.
