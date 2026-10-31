# Rediseño · Etapa E4: portada, móvil, modo oscuro y build de producción — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar la v4 como producto: portada `/v2` con buscador y tendencias reales (spec §3.5), móvil al mismo nivel que el escritorio en todas las páginas (§3.6), modo oscuro completo, y la v4 compilada y servida por el backend exactamente como lo hará producción (export estático + FastAPI).

**Architecture:** Sobre la rama `rediseno/v4` (tras E3). Portada en `src/app/v2/page.tsx` → `HomeClient.tsx` (la ruta catch-all ya cubre `/v2/{T}`; la portada es `/v2` sin símbolo). Las tarjetas de tendencias muestran la calidad y el precio del motor usando la **misma cola de análisis en segundo plano de los rivales** (E2b, `peers.queue`), generalizada como `analysis_queue` con dos prioridades (rivales pedidos por un usuario > precalentado de tendencias). El backend gana la ruta de servido de `/v2` (SPA, como `/stock`). Nada de la web actual cambia.

**Tech Stack:** Next.js 16 (export estático), React 19, Playwright con proyectos Chromium, **WebKit (iPhone)** y Firefox, Lighthouse; FastAPI.

## Global Constraints

- Todas las reglas de diseño de E1/E3 (simetría con huecos internos, 12 px mínimo, lectura 16/17 px, zoom permitido y página usable al 200 %, sin neón, AA en claro y oscuro).
- **Conductual (spec §3.5):** las listas se titulan por lo que miden ("Más negociadas hoy", "Mayores subidas", "Mayores caídas"), nunca "las mejores"; cada tarjeta con la calidad y el precio del motor para distinguir negocio de ruido; fecha, hora y universo visibles.
- **Render gratuito:** el precalentado de tendencias analiza como mucho `prewarm_max` símbolos al día, de uno en uno, solo cuando no hay análisis de usuarios esperando.
- La web actual (`/`, `/stock`) y `frontend/out` de `main` no cambian. El `frontend/out` que compiles en esta etapa vive solo en la rama y se regenera en E6.
- Sin push, sin merge, sin deploy. Aprobaciones del PM por delegación del usuario.

---

### Task 1: Cola de análisis compartida y tarjetas de tendencias con el motor

- [ ] Generaliza `backend/lib/peers.py` → `backend/lib/analysis_queue.py` (cola única, dos prioridades `user` > `prewarm`, resúmenes compactos `summary()` en la misma LRU); `peers` la usa con prioridad `user`. Tests de prioridad: un rival pedido adelanta a todo el precalentado pendiente; nunca hay dos análisis del mismo símbolo a la vez.
- [ ] `trending.get()` añade a cada item `engine: {status, quality: {score, level}, price_score: {score, level}} | null` desde la LRU; tras calcular las listas, encola en `prewarm` los símbolos de las tres listas que no estén en caché (máx. `[trending] prewarm_max = 30`).
- [ ] `GET /api/v2/trending` devuelve el estado de cada tarjeta (`listo`/`analizando`/`en_cola`); test con el replay.

### Task 2: Portada

- [ ] `src/app/v2/page.tsx` + `HomeClient.tsx` (maqueta 5): titular "Entiende una empresa antes de invertir", buscador grande funcional (`searchStocks` con debounce, navegación con teclado ↑ ↓ Enter, resultados con nombre, ticker y bolsa; Enter con un ticker exacto va a `/v2/{T}`), tendencias en tres pestañas accesibles (`role="tablist"`), tarjetas en rejilla simétrica (5 × 2 en escritorio, 2 por fila en móvil) con nombre, ticker, precio, variación y la calidad y el precio del motor con su escala mini (o esqueleto del mismo alto mientras se analiza), pie con "Actualizado el {fecha} a las {hora} (Nueva York) · universo: S&P 500 y ADR principales ({fecha del universo})"; tres tarjetas de confianza (datos oficiales de la SEC, método por tipo de empresa, honestidad con la incertidumbre) con textos tomados de la metodología del motor (no inventados).
- [ ] Estados: tendencias `calculando` (esqueletos + "Calculando las tendencias del día…" y reintento cada 5 s), `sin_dato` (motivo y última lista buena si existe).
- [ ] Barra general en todas las páginas: el buscador de E1 pasa a funcional (mismo componente).
- [ ] Playwright: búsqueda "apple" → AAPL → `/v2/AAPL`; pestañas; tarjetas de igual alto; axe.

### Task 3: Móvil al mismo nivel

- [ ] Proyectos de Playwright: `mobile-chromium` (Pixel 7), **`mobile-webkit` (iPhone 15, WebKit)** y `tablet` (iPad, 768 px). Todas las pruebas de diseño de `/v2` en los tres.
- [ ] Repaso página a página en 375 px y 768 px: cabecera compacta (precio 32 px y variación al lado, tres puntuaciones en una fila con escala mini y desglose en hoja inferior al tocar), barra de capítulos deslizable con el activo visible (se desplaza sola al capítulo activo), píldoras deslizables, tablas técnicas que no desbordan (en < 480 px pasan a tarjetas por métrica con las mismas columnas como pares etiqueta-valor), gráficas táctiles (arrastre para el cursor, sin bloquear el desplazamiento vertical de la página: `handleScroll.vertTouchDrag = false`), escenarios usables con el pulgar (controles ≥ 44 px de alto), tooltips como hoja inferior.
- [ ] **Zoom en iPhone (petición del usuario: "no se le puede hacer zoom en la versión de app del iphone"):** en WebKit, comprueba que la meta viewport no limita la escala, que ningún `touch-action` ni `gesturestart` lo impide y que la página sigue usable con el zoom de texto al 200 %. Documenta en el registro el diagnóstico del caso del usuario: la web actual no limita el zoom en su código; si el bloqueo aparece al abrirla como icono de la pantalla de inicio, anota la causa probable (modo `standalone`) y que `/v2` no declara `apple-mobile-web-app-capable` (se abre como página normal con zoom). La prueba en su teléfono queda para cuando el usuario pruebe la v4.

### Task 4: Modo oscuro completo

- [ ] Todas las páginas (portada, historia, 9 de profundidad, tooltips, hojas, gráficas con los colores de los tokens oscuros, esqueletos, tablas, escenarios) en oscuro. Contraste AA con axe en oscuro en todas. Preferencia guardada (E1) y, la primera vez, la del sistema (`prefers-color-scheme`). Sin parpadeo al cargar (script mínimo en el layout de `/v2` que pone `data-theme` antes de pintar).

### Task 5: Build de producción y servido por el backend

- [ ] `backend/main.py`: ruta SPA `GET /v2/{path:path}` como la de `/stock` (archivos reales bajo `out/v2/` si existen, si no `out/v2/index.html`), protegida contra recorrido de rutas igual que `serve_static`; y `/v2` → `out/v2/index.html`. Test con un `out/` sintético.
- [ ] `npm run build` en la rama (Turbopack, `node_modules` real sin enlaces): el export genera `out/v2/index.html` y sus recursos; el `prebuild` (guardián de literales) pasa con `/v2` incluido.
- [ ] Sirve `out/` con el backend real en local (`uvicorn main:app` con `frontend/out` de la rama) y ejecuta **todo** `e2e:v2` contra ese servidor (`baseURL` = el backend, sin `next dev`), en los 4 proyectos.
- [ ] Lighthouse sobre el build servido: `/v2`, `/v2/AAPL`, `/v2/AAPL/valor` en escritorio y móvil. Objetivo: rendimiento ≥ 90 y accesibilidad ≥ 95 en escritorio; ≥ 80 / ≥ 95 en móvil. Si no se alcanza: optimiza (división de código de Lightweight Charts con `dynamic import`, imágenes de noticias con `loading="lazy"` y tamaño fijo, fuentes) y anota.
- [ ] Verifica que `/` y `/stock/AAPL` del build siguen siendo la web actual sin cambios (capturas antes/después idénticas).

### Task 6: Registro

- [ ] `docs/rediseno/E4_REGISTRO.md`, capturas en `docs/rediseno/capturas-e4/` (portada en los 3 tamaños × claro/oscuro; 3 páginas en WebKit iPhone), Lighthouse en JSON; informe al PM.

> **Evidencia fuera de `main` (E6, 31-oct):** las capturas (`docs/rediseno/capturas-*`), `docs/fiabilidad/f8_evidencia/` y los volcados JSON de escaneo y medida de `docs/` no están en `main`. Siguen en las ramas locales del rediseño y de la fiabilidad (`rediseno/v4-f8`) y en el archivo `v4_evidencia_8e4f3952.tar.gz` de `/Users/joseestebanroa/Downloads/finanzer_next-archivo`, fuera del repositorio.
