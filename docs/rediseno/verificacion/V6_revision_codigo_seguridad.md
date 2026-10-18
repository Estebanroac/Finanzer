# V6 · Revisión de código y seguridad de la v4 (PM, 2026-10-18)

Dos revisores independientes (solo lectura) sobre `main...rediseno/v4` y `main...rediseno/e4-portada`. Hallazgos
verificados leyendo el código (el crítico, además, medido ejecutando la función). Reparto de arreglos: backend → sesión
E4 (rama `rediseno/e4-portada`); frontend → sesión E3 (rama `rediseno/v4`). Cada arreglo en origen, con su test.

## Backend (sesión E4)
| # | Gravedad | Hallazgo | Arreglo exigido |
|---|---|---|---|
| B1 | CRÍTICO | `/api/v2/scenario` acepta `base` del cliente sin recortar: `high_growth_years` = 2·10⁷ → ~40 s de CPU y ~800 MB: tumba el proceso | Modelo pydantic `extra="forbid"`, números finitos, límites en todo; `base` recortada a `[scenario]` (o no aceptarla del cliente); `isfinite` antes de responder; turno propio |
| B2 | ALTO | El parseo de segmentos ocupa el único turno de lecturas de EDGAR del análisis → análisis concurrentes sin EDGAR (cifras de Yahoo, caso BRK-B) | Semáforo propio para segmentos; contabilizar la espera en `queued_s` |
| B3 | ALTO | Rivales guardan fallos pasajeros 7 días (ranking sin empresa, capitalizaciones `None`) | No cachear fallos (o `fail_ttl_s` corto) |
| B4 | MEDIO | Entradas de scenario (NaN, tipos, claves) → 500 | Cubierto por B1 → 422 |
| B5 | MEDIO | Sin límite de tamaño de cuerpo en POST | Middleware 413 (> 32 KB) |
| B6 | MEDIO | `norm_symbol` cambia `BARC.L` → `BARC-L` | Normalizar solo clases conocidas |
| B7 | MEDIO | Cola sin reparto por cliente; "cola llena" → `listo` y el cliente deja de preguntar | Tope por cliente/empresa; con FULL, `calculando` con reintento |
| B8 | MEDIO | `prices` y `segments` sin validar símbolo ni turno; descargas duplicadas | `_v2_symbol`, semáforo 2, fallos cacheados 60 s, una descarga por clave |
| B9 | MEDIO | `/api/v2/pdf` toma el semáforo sin `_slot()` y descarga segmentos dentro del turno | `_slot()`; segmentos solo de caché |
| B10–B17 | BAJO | Cachés sin tope (`_caps`, `_rankings`, `_state`, `_unreachable`); carrera en `peers_for`; "hoy" de `next_earnings`; resúmenes de rivales sin `as_of`; `segments.build` puede lanzar y descargar sin tope; CORS localhost en producción; `detail=str(e)` en 500; URL de noticias sin validar | Todos, con test |

## Frontend (sesión E3)
| # | Gravedad | Hallazgo | Arreglo exigido |
|---|---|---|---|
| F1 | ALTO | Rentabilidades por periodo, base 100 y tono calculados en el navegador (rompe la regla del proyecto; pueden no cuadrar con el PDF) | `/api/v2/prices` devuelve `returns[range]` y series en base 100; el cliente solo pinta; `returns.ts`/`chartEvents.ts` al guardián |
| F2 | ALTO | `StoryPageClient` usa `analyzeStock` (errores en inglés, sin reintentar) | `fetchAnalysisV2` + "Reintentar" y "Volver a la portada" |
| F3–F12 | MEDIO | URL de noticias sin lista de esquemas; carreras en quitar/añadir rivales; sondeo de rivales que muere con un 502; buscador de rivales sin orden ni limpieza; "$" fijo en el precio (MC.PA en EUR); ruta mal codificada rompe la página y símbolo sin validar; sin `document.title` ni foco al cambiar de capítulo; hoja inferior sin devolver foco ni bloquear scroll; Enter del buscador a un resultado oculto; peticiones repetidas sin caché ni cancelación | Todos, con test |
| F13–F25 | BAJO | División de código por página y de lightweight-charts; sessionStorage sin tope ni versión; datos raros que tumban componentes; sondeo infinito de la portada; escenario sin abortar ni leer `detail` y color de celdas decidido en cliente; mensajes técnicos; `role="tab"` incompleto; `listbox` sin opciones; tarjeta de noticia (alt, aviso de pestaña nueva, sin url); desglose sin Escape; sin cabeceras de seguridad (CSP, nosniff, Referrer-Policy, frame-ancestors — backend); parpadeo del botón de tema; `/v2` sin símbolo en v4 | Todos, con test (las cabeceras de seguridad, en el backend: sesión E4) |
