# V6 · Arreglos del backend (sesión E4, rama `rediseno/e4-portada`)

Hallazgos de la revisión de código y seguridad del PM (`docs/rediseno/verificacion/V6_revision_codigo_seguridad.md`
en main, d96c9a8). Cada arreglo lleva su test. Ninguna cifra ni veredicto cambia: `diff_golden` sin diferencias en
el panel (38) y en local (6).

| # | Gravedad | Arreglo | Tests |
|---|---|---|---|
| B1 | CRÍTICO | `/api/v2/scenario` valida el cuerpo antes de calcular (`lib/scenario.parse_request`, pydantic estricto con `extra="forbid"`): solo números finitos, límites en todos los campos (`[scenario] input_*` en TOML) y años dentro de `years_min..years_max`. La `base` del cliente se recorta como los supuestos (las del motor ya están dentro: test sobre el panel entero). Nunca un `inf`/`NaN` en la respuesta. Turno propio (`scenario_concurrency = 2`) | `test_v6_http.py`: 24 cuerpos malos → 422 en < 100 ms por HTTP real (años 2·10⁷, NaN, infinito, texto, booleano, lista, claves de más o que faltan, `decay_type` raro, acciones 0 o minúsculas, importes y tasas absurdos, texto largo, cuerpo que no es objeto); el panel entero pasa y da lo mismo |
| B4 | MEDIO | Cubierto por B1: lo que antes daba 500 da 422 | ídem |
| B5 | MEDIO | `lib/web_guard.BodyLimit`: más de `max_body_bytes` (32 KB) → 413 sin leer el resto, por Content-Length y también en chunked | 413 con Content-Length y en chunked; por debajo, 200 |
| B2 | ALTO | Segmentos con su propio turno de lectura (`_segments_parsing`, `segments_parse_concurrency = 1`); `Budget.turn` suma la espera a `queued_s` mientras espera (a tramos de `turn_poll_s`) y abandona al agotar `queue_max_s` («EDGAR ocupado») | lectura de segmentos lenta en curso: el análisis toma su turno sin esperar; la espera cuenta mientras se espera; abandono al agotar la cola |
| B3 | ALTO | Rankings con la empresa fallida o sin su capitalización, y capitalizaciones `None`: caducan a `fail_ttl_s` (600 s), no a 7 días | los tres casos y el reintento al caducar |
| B6 | MEDIO | `norm_symbol` solo pasa a guion las clases de `share_classes` (A, B, C): `BARC.L`, `MC.PA`, `7203.T` conservan el punto | ídem |
| B7 | MEDIO | Cola: cupo por cliente (`max_per_client = 10`; IP de `cf-connecting-ip`/`true-client-ip` o del socket) y, por empresa, `peers_count`. Con la cola llena, «en_cola» con `retry` y sin estado: la tabla sigue «calculando» y el cliente vuelve a preguntar | cola llena → reintento y después listo; un cliente no llena la cola de otro; el endpoint pasa el cliente; muestra de contrato `cola_llena` |
| B8 | MEDIO | `lib/lazy_gate.Gate` para la gráfica y los segmentos: 2 a la vez, una descarga por clave, fallos recordados 60 s. `/api/v2/prices` valida el símbolo con `_v2_symbol` | consultas simultáneas → una descarga; pico de concurrencia = 2; fallo recordado; símbolos malos → 422 |
| B9 | MEDIO | `/api/v2/pdf`: turno de usuario (`_slot`, ya en la verificación V4) y segmentos solo de caché (`segments.cached`) | el PDF no llama a `segments.build` dentro del turno |
| B10 | BAJO | Topes: `peers._caps` (512), `_rankings` (64), `yf_adapter._unreachable`; purga de los fallos caducados de `analysis_queue._state`. `_ranking_pending` no crece más que la cola (si no entra, sale) | topes y purga |
| B11 | BAJO | `peers_for`: mirar la caché y marcar «en marcha» en una sola sección con el lock | 8 consultas a la vez → un solo ranking encolado |
| B12 | BAJO | «Hoy» de los próximos resultados = fecha de Nueva York, reloj inyectable (`market_context.TODAY`); el replay usa el día de su captura | 02:00 UTC = ayer en Nueva York; `build` usa el reloj inyectado |
| B13 | BAJO | `as_of` (UTC) en el resumen de cada rival y en el `engine` de cada tarjeta (tipos opcionales en `api.ts`) | ídem; contrato de tipos |
| B14 | BAJO | `segments.build` nunca lanza (sin_dato con motivo genérico; el detalle, al registro). La descarga de la instancia cuenta los bytes ya descomprimidos (`max_instance_mb`) y el presupuesto a cada trozo | gzip que se infla, descarga lenta que agota el presupuesto, error inesperado |
| B15 | BAJO | CORS de localhost solo fuera de Render | con y sin `RENDER_EXTERNAL_URL` |
| B16 | BAJO | Los 500 dicen `INTERNAL_ERROR`; la excepción, solo al registro | la ruta secreta del error no sale |
| B17 | BAJO | Enlace de un titular solo si es `http(s)://` (`market_context.safe_url`) | `javascript:`, `data:`, `//`, `ftp:` y URL enormes → None |
| F23 | (frontend, en el backend) | `lib/web_guard.SecurityHeaders`: CSP (`[server] csp`: `script-src 'self'` + el sha256 de cada script en línea del propio HTML, `img-src 'self' https: data:`, `frame-ancestors 'none'`…), `nosniff` y `Referrer-Policy: strict-origin-when-cross-origin` en cada respuesta | `legado:comparar`: `/` y `/stock/AAPL` idénticas píxel a píxel a main (4/4); `e2e/legado/csp.spec.ts`: ninguna violación en `/`, `/stock/AAPL`, `/v2`, `/v2/AAPL` y `/v2/AAPL/valor`, escritorio y móvil (10/10). Contraprueba: sin los hashes, falla |

## A confirmar en producción

- **B7, IP del cliente.** Se toma de `cf-connecting-ip` (o `true-client-ip`), que pone Cloudflare delante de Render y
  el cliente no puede elegir. Si en Render no llegara ninguna, todas las peticiones compartirían la IP del proxy y,
  con ella, un cupo de 10 trabajos: los rivales no fallarían, pero esperarían más («en_cola» con reintento). La lista
  de cabeceras está en `[server] client_ip_headers`.
- **CSP.** Si una página nueva añade un script en línea, su hash entra solo (se calcula por documento). Un script
  externo de otro dominio, en cambio, la política lo bloquearía: hay que añadir su origen a `[server] csp`.
