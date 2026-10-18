# Rediseño · Verificación de la v4 ("las grandes pruebas") — Plan

> Etapa final antes de avisar al usuario. Literal del usuario (2026-10-17): *"quiero que me vuelvas a interrumpir cuando
> la v4 esté lista… lo probamos y si todo está perfecto sobre las grandes pruebas que le harás para saber que no se
> buggea, entonces migramos del modelo viejo al nuevo"*. La migración (E6) **no** forma parte de este plan: solo se
> hace con el visto bueno del usuario tras probar la v4.

**Goal:** Demostrar con evidencia que la v4 (rama `rediseno/v4`, con E1–E5 fusionadas) no falla: en todos los tickers
del panel, en todos los navegadores y tamaños, con fuentes caídas, con datos raros, con carga concurrente y servida
como en producción. Corregir todo lo que aparezca (cada fallo: causa en origen, test que lo reproduce, arreglo).

**Base:** `rediseno/v4` tras fusionar E3, E4 y E5. Build de producción (`npm run build`) servido por el backend real
(`uvicorn`), salvo donde se indique el replay.

## Batería

### V1 · Panel completo, sin red (replay)
- 37 tickers del panel + MC.PA: `/v2/{T}` y sus 9 páginas de profundidad, en Chromium, WebKit y Firefox, escritorio
  1440, tablet 768 y móvil 375, claro y oscuro: **sin errores de consola, sin excepciones no capturadas, sin
  peticiones fallidas inesperadas**, simetría con huecos internos, mínimo 12 px, sin desbordamiento, axe sin
  infracciones graves. Informe con la matriz completa (ticker × página × navegador × tamaño × tema).
- PDF v2 de los 38: geometría, letra mínima, enlaces y guardián en verde.
- "Nada se pierde" (E3 y E5) en los 38.

### V2 · Fuentes reales (local, con las claves del Llavero en el entorno)
- Los 8 tickers de verificación + 30 del universo elegidos al azar (semilla anotada) + casos raros: `BRK-B`, `GOOG` y
  `GOOGL`, un ADR con factor (TSM), un banco extranjero (BCS), una aseguradora, un REIT, una pre-beneficio, una
  recién salida a bolsa, una de París (MC.PA), un ETF (SPY: debe decir que no analiza ETF sin romperse), un ticker
  inexistente (`ZZZZZ`), uno con punto (`BF.B`), uno deslistado. Para cada uno: análisis, historia, 9 páginas,
  segmentos, rivales hasta completar, escenario con valores extremos, PDF v2. Resultado: tasa de éxito, motivos de
  cada `sin_dato`, tiempos por endpoint.

### V3 · Fuentes caídas (inyección de fallos)
- Con `fixture_backend` y monkeypatch: Yahoo caído, Yahoo devuelve 401 (plan B), EDGAR sin User-Agent, EDGAR lento
  (agota el presupuesto), Finnhub sin clave, Finnhub 429, serie de precios vacía, ETF del sector caído. En cada caso
  la v4 muestra la página entera con los motivos en su sitio, sin huecos ni errores, y el PDF se genera.

### V4 · Carga y memoria (como Render gratuito)
- Backend real limitado a 512 MB (`ulimit -v` o un contenedor con límite) y 4 análisis concurrentes: 20 usuarios
  simulados durante 5 minutos (análisis, páginas, gráficas, escenarios, rivales, tendencias, PDF) con `locust` o un
  script de `httpx` asíncrono. Criterios: ningún 5xx, memoria pico < 450 MB, p95 de `/api/analysis` en caché < 2 s,
  ninguna fuga (memoria estable en la segunda mitad), la cola de rivales/precalentado nunca retrasa a un usuario más
  que otro análisis de usuario.
- Arranque en frío: proceso nuevo → primera petición de la portada y de `/v2/AAPL` con tiempos.

### V5 · Producción simulada
- `frontend/out` de la rama servido por `main.py`: rutas `/`, `/stock/AAPL` (web actual intacta: capturas idénticas a
  las de `main`), `/v2`, `/v2/AAPL`, `/v2/AAPL/valor`, recarga directa en una página de profundidad (SPA fallback),
  recorrido de rutas maliciosas (`/v2/%2e%2e/...`) → 404.
- Lighthouse en el build: objetivos de E4.

### V6 · Revisión de código y seguridad
- `/code-review` de todo el diff `main...rediseno/v4` (nivel alto) y `/security-review`: entradas del usuario
  (`?symbols=`, escenario, búsqueda), endpoints nuevos, enlaces externos, contenido de terceros (titulares, imágenes de
  noticias: sin `dangerouslySetInnerHTML`, imágenes solo `https`), cabeceras. Cada hallazgo real se arregla con su test.

### V7 · Revisión de un lector nuevo
- Un subagente que no conoce la app recorre la v4 de AAPL, JPM y PLTR con una lista de preguntas de inversor ("¿es
  buena la empresa?", "¿está cara?", "¿qué podría salir mal?", "¿cómo le fue en 5 años?") y anota dónde se pierde o
  qué no entiende. Lo accionable se corrige; el resto se anota para el usuario. (La revisión con 2–3 personas reales de
  la spec §7.5 se propone al usuario, no se simula.)

## Cierre
- `docs/rediseno/V4_VERIFICACION.md`: matriz V1, tablas V2–V5, hallazgos V6–V7 y su arreglo, y la lista de lo que
  queda abierto (si algo). Solo con todo en verde, el PM avisa al usuario: qué es la v4, cómo probarla (enlace local;
  y, si quiere probarla en el teléfono, la propuesta de publicar `/v2` oculta, que requiere su "ok, pushea"), y qué
  implicaría la migración (E6) para que decida.
