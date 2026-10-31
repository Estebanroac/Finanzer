# V6b · Revisión de código y seguridad del delta final (E4, 2026-10-18)

## Alcance y método

Solo lectura, sin checkout de la v4. Revisado con `git diff`/`git show` desde el worktree e4:

- **Delta de la v4:** `fa9e870..rediseno/v4`. La v4 seguía creciendo; las citas de archivos de E3 son de **05c0bdf**.
  Desde la última V6 (`V6_revision_codigo_seguridad.md`, base d96c9a8).
- **P8b:** `rediseno/p8b-portada`, hasta 956bffe, más los arreglos de esta revisión (abajo).
- **Backend (lo revisó E4):**
  - `sparklines.py`, `period_change.py`, `trending.py`, `names.py`, `names.toml` y `prose.py`;
  - los cambios de `display.py` y `peers.py` de la fusión;
  - `web_guard.py` (cabeceras y CSP) y los errores de `main.py`.
- **Frontend:**
  - de la portada (lo revisó E4): `TickerStrip`, `useCarousel`, `tickerModel` y `sparklines.ts`;
  - de E3: `Floating`, `AnalyzeLoading`, `LoadError`, `analysis.ts`, `ScoreScale`, `MetricTip`, `CompanyHeader`,
    `Concentration`, `RivalsMini`, `SegmentsStory`, `PeersTable`, `SearchBox`, `usePeers`, `story`, `terms`,
    `confidence` y `companyName`. Una primera pasada la hizo un revisor de solo lectura y **E4 ha verificado cada
    hallazgo** leyendo el código en 05c0bdf.
- **Pruebas:** donde hacía falta, el comportamiento se midió o se reprodujo con Playwright contra el replay.

**Resumen:**
- No hay hallazgos críticos.
- Uno ALTO, de la portada y ya arreglado: la copia del bucle no se podía pulsar.
- Tres MEDIOS:
  - uno de la portada, arreglado: las mini-gráficas aceptaban símbolos fuera del universo;
  - dos de E3: orden del foco y Escape del panel del «?»; gesto de cerrar la hoja.
- Varios BAJOS e INFO.
- No hay XSS ni fugas de temporizadores o listeners en el código de E3, y la CSP no necesita cambios.

## Hallazgos de la portada (arreglados en `rediseno/p8b-portada`)

| # | Gravedad | Hallazgo | Archivo:línea (antes) | Arreglo y test |
|---|---|---|---|---|
| P1 | **ALTO** | La copia que cierra el bucle del cintillo era `inert`. Con el bucle, media vuelta se ve la copia y sus tarjetas no respondían al clic ni al dedo. Reproducido con Playwright: con `scrollLeft` = ancho de una copia, el clic no navega. | `TickerStrip.tsx:267` (956bffe) | **30536a2**: sin `inert`; la copia sigue con `aria-hidden` y sus enlaces con `tabIndex` −1, así que queda fuera de los lectores y del tabulador. e2e «con la copia del bucle a la vista, sus tarjetas se pulsan»; axe sin infracciones. |
| P2 | MEDIO | `/api/v2/sparklines` aceptaba cualquier símbolo de forma válida. El fallo no se guarda en caché, así que una lista de símbolos inventados convertía cada petición en descargas nuevas de Yahoo (hasta 2 llamadas por petición en 1D). Un cliente podía provocar que Yahoo limitara la IP del servidor para todos (tendencias y análisis). | `sparklines.py:79-94` (956bffe) | **5fb0d39**: un símbolo fuera del universo es un 422 antes de descargar. `test_only_universe_symbols` (422 y ninguna llamada a Yahoo); el e2e de rutas revisa el 422. |
| P3 | BAJO | `/api/v2/trending` pasó de 14,6 KB a 63,6 KB con gzip al llevar las listas de los 4 periodos, y la portada la repite cada `poll_s` (5 s) mientras se analizan tarjetas. | `trending.py:310-326` (956bffe) | **a45b88c**: `?period=` devuelve solo las listas, notas y sectores de ese periodo (16,5 KB con gzip); sin él, todo, como hasta ahora; otro valor, 422. Test `test_endpoint_returns_only_the_requested_period`. **Pendiente:** la portada aún no lo usa (ver «Para E3»). |
| P4 | BAJO | Si el backend no devolviera la gráfica de un símbolo pedido, el efecto de las mini-gráficas lo pediría en bucle. Hoy no pasa porque el universo va normalizado; lo marcó el revisor del frontend. | `TickerStrip.tsx:121-134` (956bffe) | **508c4ce**: el símbolo que no vuelve queda «sin dato» con su motivo. e2e: una sola petición aunque falte un valor. |
| P5 | BAJO | Con «reducir movimiento», el bucle de `requestAnimationFrame` de `useCarousel` seguía corriendo sin nada que mover (batería en móvil). | `useCarousel.ts:155-176` (956bffe) | **508c4ce**: con «reducir movimiento» no arranca. e2e: menos de 5 fotogramas por segundo. |

## Para E3 (no se han tocado sus archivos)

Citas de `rediseno/v4` en 05c0bdf.

| # | Gravedad | Hallazgo | Archivo:línea | Arreglo propuesto |
|---|---|---|---|---|
| E1 | MEDIO | **Foco y Escape del panel del «?» en escritorio.** El panel va en un portal al final de `.fz2`. Al abrir, el foco entra en «Cerrar»; Tab sale al final del documento, no al elemento siguiente al «?». El panel no se cierra al perder el foco. El Escape se escucha en `window` y en captura: con el foco ya fuera (por ejemplo, en el buscador), Escape cierra el panel y devuelve el foco al «?». Con teclado se pueden abrir dos «?» a la vez, y un Escape cierra los dos. | `MetricTip.tsx:34-35`, `:52`, `:56-57`; `Floating.tsx:139-142`, `:186-188` | En modo panel: cerrar en `focusout` cuando `relatedTarget` cae fuera del panel y del «?»; con Tab o Shift+Tab en los bordes, cerrar y devolver el foco al «?»; atender Escape solo con el foco en el panel o en el «?». |
| E2 | MEDIO | **El gesto de cerrar la hoja inferior choca con su desplazamiento interno.** En móvil, con una hoja larga ya desplazada hacia abajo, arrastrar hacia abajo para volver arriba la cierra en cuanto pasa de 80 px: el gesto no mira `scrollTop`. | `Floating.tsx:179-181` | Empezar el gesto solo si `scrollTop <= 0` al tocar, o solo desde la cabecera de la hoja. |
| E3 | BAJO | Cerrar la hoja del «?» con el gesto pierde el foco: `onClose` es `close`, que hace `blur()` en lugar de devolverlo al «?». ScoreScale sí lo devuelve. | `MetricTip.tsx:25-28`, `:73` | En hoja, `btn.current?.focus({ preventScroll: true })`. |
| E4 | BAJO | Floating recalcula hoja o panel en cada render y el consumidor lo fija al abrir. Al girar una tableta con el panel abierto, cruzando los 768 px, Floating pinta el panel de escritorio mientras el consumidor sigue con el fondo bloqueado, el Tab atrapado y `aria-modal`. | `Floating.tsx:88` frente a `MetricTip.tsx:70` | Pasar `sheet` como prop, o cerrar al cambiar la media query. |
| E5 | BAJO | El desglose de escritorio que se abre al pasar el ratón no se cierra con Escape si el foco está fuera de la tarjeta (WCAG 1.4.13). | `ScoreScale.tsx:107-110` | Mientras esté abierto, Escape en `window` → `setDismissed(true)`. |
| E6 | BAJO | En móvil la tarjeta de puntuación se comporta como botón (`tabIndex`, Enter o Espacio) pero no lo anuncia: sin `role` ni `aria-expanded`. Tampoco basta `role="button"`, porque contiene botones «?». | `ScoreScale.tsx:97-110` | Un botón propio «Ver detalle», con `aria-expanded` y `aria-controls`. |
| E7 | BAJO | El sondeo de rivales no tiene tope: mientras la respuesta sea «calculando» pregunta cada `poll_s` sin límite y también con la pestaña oculta. | `usePeers.ts:26` | Tope de tiempo o de intentos, y pausa con `document.hidden` (como la portada). |
| E8 | BAJO | «Bajan en el último ejercicio (FY → FY2024)» cuando `prev_fy` es null. | `Concentration.tsx:29` | Pintar el rango solo con `prev_fy`. |
| E9 | INFO | `raw in EXCEPTIONS` encuentra claves del prototipo («constructor», «__proto__»): el nombre llega de resultados de búsqueda guardados en sessionStorage, y React fallaría al pintar un objeto. Improbable. | `companyName.ts:18` | `Object.hasOwn(EXCEPTIONS, raw)`. |
| E10 | INFO | Rendimiento, sin fuga: cada tarjeta escucha `pointermove` en `document` con 3 setState por movimiento; un `onClose` en línea vuelve a suscribir `autoUpdate` en cada render con el panel abierto. | `ScoreScale.tsx:55-65`, `:138`; `Floating.tsx:135` | Memorizar `onClose`; agrupar el estado del puntero. |
| E11 | — | **La portada usaría `?period=` (P3).** El e2e F16 de `v6.spec.ts` intercepta `**/api/v2/trending`, sin comodín, y no casa con la URL con consulta. | `e2e/v2/v6.spec.ts:266` | Cambiar el patrón a `**/api/v2/trending*` (el de `home.spec.ts` ya va así). Con eso, E4 pasa la portada a pedir solo el periodo que muestra; el cambio está hecho y probado (176 e2e en verde) y se retiró para no romper F16. |

Además, ya visto en la pasada final de P8b y ajeno a este delta: `e2e/v1/panel.spec.ts` falla en SHEL (escritorio,
claro y oscuro) con «riesgos: el visual se estira 111px» en la página-historia. P8b no toca esa página.

## Comprobado y correcto

- **Validación de entradas:**
  - `/api/v2/sparklines`: `symbols` (`max_length` 600, regex `^[A-Z0-9.\-]{1,10}$`, como mucho 40, y ahora solo del
    universo) y `period` (`max_length` 8 y de la config): 422 con un motivo que no repite lo que envió el cliente;
  - `/api/v2/trending?period=`: de la config, o 422;
  - los 500 ya no exponen el error (`INTERNAL_ERROR`, V6 B16).
- **Topes:**
  - caché de las mini-gráficas acotada (`cache_max` 600, `bounded.put`);
  - la puerta de descargas de la gráfica limita la concurrencia (2), recuerda los fallos con caducidad y tiene tope
    (`lazy_gate.Gate(chart_concurrency, chart_fail_ttl_s, chart_cache_max)`);
  - `peers` con `caps_cache_max` y `rankings_cache_max`, y las sustituciones con `max_substitutions`.
- **Coste de 30 símbolos × 4 periodos:**
  - Por periodo visitado: una petición de como mucho 40 símbolos, que son 1 o 2 llamadas a Yahoo con la caché fría y
    ninguna con la caché caliente (5 min en 1D, 1 h en el resto). Cuatro periodos con la caché fría: 5 llamadas por
    lista. Los sectores, igual.
- **Tendencias:**
  - La descarga del universo (543 símbolos, lotes de 100, dentro de un turno de fondo) tarda 18 s, igual que con 5
    días. Pico del proceso: +39 a +49 MB, frente a +48 a +50 MB antes.
  - El cálculo retiene 1,2 MB de Python y tiene un pico de 13 MB; solo se guardan listas compactas y las variaciones.
- **XSS:**
  - Todo se pinta como texto de React. El único `dangerouslySetInnerHTML` es el de `app/v2/layout.tsx` (constante, con
    su hash en la CSP).
  - Los enlaces se construyen con `stockHref` o `chapterHref`: prefijo fijo y `encodeURIComponent`.
  - El `detail` del backend en el error, como texto (`LoadError.tsx:14`).
  - Las noticias pasan por `safeNewsUrl`, y los nombres de empresa del cintillo son texto.
- **Fugas:**
  - `useCarousel` quita sus 10 listeners, incluidos `pointerup` y `pointercancel` en `window`, y cancela el
    requestAnimationFrame.
  - El sondeo de la portada se cancela con AbortController y su temporizador, y se para con la pestaña oculta. Las
    mini-gráficas se abortan al cambiar de periodo o lista.
  - En E3 todo se limpia: `Floating` (scroll, resize, autoUpdate), `ScoreScale`, `MetricTip`, `AnalyzeLoading`
    (requestAnimationFrame y timeouts), `SearchBox`, `usePeers`, `Concentration`, `SegmentsStory` y `PeersTable`.
  - `fetchAnalysisV2` tiene presupuesto de espera.
- **Cabeceras y CSP:**
  - Valores de `data.toml:112-114`: `script-src 'self'` más los hashes de los scripts en línea y `style-src 'self'
    'unsafe-inline'`.
  - Los estilos en línea de `@floating-ui` caben en `style-src` (y las escrituras por CSSOM no pasan por él).
  - `connect-src 'self'` cubre las nuevas rutas (mismo origen). Sin scripts en línea nuevos ni orígenes externos
    nuevos.
  - `nosniff`, `Referrer-Policy` y `frame-ancestors 'none'` siguen. HSTS y Permissions-Policy no están; no es algo
    nuevo y puede ponerlos Cloudflare (INFO).
- **Accesibilidad del carrusel:**
  - La copia va con `aria-hidden` y tabIndex −1 (ver P1: `inert` impedía el clic).
  - Foco de teclado, flechas, sin animación con «reducir movimiento» y pausa sin botón (WCAG 2.2.2), según el
    registro de P8b.
- **Dependencias nuevas:**
  - `@floating-ui/react-dom` fijada exacta (`"2.1.9"`, sin `^`); sus dependencias `@floating-ui/dom` 1.8.0, `core`
    1.8.0 y `utils` 0.2.12 quedan fijadas por el lockfile con su `integrity`.
  - Las cuatro, licencia MIT. La peerDependency `react>=16.8` se cumple.
  - El backend no tiene dependencias nuevas.
- **Backend nuevo:**
  - `names.py`: las regex salen de la config con `re.escape`, más un patrón fijo sin riesgo de ReDoS.
  - `prose.py`: recorre el `display` sin efectos fuera de él.
  - `period_change.py`: `bisect` sobre las fechas.
  - `display.py` y `peers.py` de la fusión: textos y los arreglos B3/B10 de la V6.
