# Rediseño · Etapa E6: migración de la web actual a la v4 — Plan

> **Solo se ejecuta con el visto bueno explícito del usuario tras probar la v4** (literal, 2026-10-17: *"que el último
> paso sea solo migrar del modelo actual al nuevo si el nuevo marcha de maravilla… lo probamos y si todo está perfecto…
> entonces migramos"*). Implica push a `main` y despliegue automático en Render: requiere además su "ok, pushea".

**Goal:** Que `finanzer.app` sirva la v4 como web principal, con la web actual disponible como respaldo durante un
periodo de observación, sin pérdida de datos ni de enlaces, y con vuelta atrás en minutos.

## Principios
- **Reversible:** la web actual sigue servida en `/clasica` (y `/stock/{T}` redirige a `/v2/{T}` solo después del
  periodo de observación). Volver atrás = revertir un commit de rutas y redesplegar.
- **Historial limpio:** las ramas del rediseño llevan en su historial capturas pesadas (~280 MB antes de comprimir).
  `main` no las recibe: la v4 entra como **un commit de squash** (o pocos, por bloques) sobre `main`, con las capturas
  ya comprimidas (≤ 45 MB en total) o, mejor, sin ellas (se guardan como artefacto fuera del repositorio y el registro
  enlaza dónde están). Decisión por defecto del PM: **sin capturas en `main`**; quedan en las ramas locales del
  rediseño y en un archivo comprimido fuera del repositorio.
- **Build local, como hoy:** `build.sh` no compila el frontend en Render (tiempo de despliegue); `frontend/out` se
  compila en local con Turbopack y se commitea, y la guarda de integridad de `build.sh` valida los recursos.

## Pasos
1. **Congelar la v4:** `rediseno/v4` con E1–E5, la verificación (V1–V7) y todos los arreglos fusionados; suite
   completa, `check`, lint, `e2e:v2`, `e2e:fallos`, V1 (Chromium + WebKit) y PDF en verde en esa revisión exacta.
2. **Rutas de transición** (commit propio, con test):
   - `/` → portada v4; `/{T}` y `/v2/{T}…` → v4; `/stock/{T}` → web actual **durante la observación** (enlaces
     compartidos siguen funcionando) con un aviso discreto «Prueba la nueva versión →»;
   - `/clasica` → portada actual (respaldo);
   - `/api/pdf/{T}` (PDF actual) se mantiene; el botón de la v4 usa `/api/v2/pdf/{T}`.
3. **Squash sobre `main`:** rama `migracion/v4` desde `main`; `git merge --squash rediseno/v4`; quitar
   `docs/rediseno/capturas-*` del índice (y añadirlas a `.gitignore`); compilar `frontend/out` (`npm run build`) y
   commitear; `build.sh` en verde en local (simulación del despliegue).
4. **Comprobación final en local con el build de `main` resultante:** V5 (producción simulada) y una pasada corta de V1
   (8 tickers) contra el backend real.
5. **Push (con "ok, pushea" del usuario) y despliegue en Render.** Comprobaciones en producción, en este orden y con
   evidencia: `/api/health`, portada, `/v2/AAPL` y sus 9 páginas, PDF nuevo, `/stock/AAPL` (respaldo), tendencias,
   rivales de AAPL hasta completar; **memoria real en Render** durante 30 min con tráfico ligero (el objetivo medido en
   local era ≤ 380 MB; si en Render se acerca a 480 MB, aplicar la opción medida «EDGAR 16 emisores» y redesplegar).
6. **Observación (7 días):** errores 5xx, memoria, tiempos; el usuario usa la v4 en su teléfono y su portátil.
7. **Cierre:** `/stock/{T}` redirige a `/v2/{T}` (o se mantiene `/clasica` indefinidamente si el usuario lo prefiere);
   bitácora y memoria al día.

## Vuelta atrás
- Rutas: revertir el commit del paso 2 → la web actual vuelve a `/` en un despliegue (~3–5 min en Render).
- Total: `git revert` del squash; el backend v4 es aditivo, así que la web actual funciona con él o sin él.
