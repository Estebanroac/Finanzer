# Prompt del operador — Rediseño E1: sistema visual y página-historia en /v2

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.

---

Eres el **operador de la etapa E1 del rediseño de Finanzer**. El motor de análisis ya es fiable (fases 0–7 del plan de
fiabilidad, en producción). El usuario aprobó un rediseño completo de la experiencia (web y PDF) a partir de maquetas
revisadas parte por parte. Tu trabajo en E1: construir en la ruta nueva `/v2`, **solo en local**, el sistema visual
aprobado y la página-historia de 9 capítulos de una empresa, con los datos que ya calcula el motor.

## 1. Regla que manda sobre todo lo demás

El usuario: *"me gustaría un prototipo aprobado antes de que implementes los cambios. Para proteger lo que existe."*

- **La web actual no cambia de comportamiento.** Los únicos archivos compartidos que puedes tocar, y solo de forma
  aditiva, están listados en "Global Constraints" del plan. Ningún golden cambia. No se commitea `frontend/out`.
- Worktree propio: `../finanzer_next-e1`, rama `rediseno/e1-sistema-historia` desde `main` (el plan, Task 0, trae los
  comandos).
- **Sin push, sin merge, sin deploy.** Nada se sube sin un "ok, pushea" explícito del usuario.
- No toques los worktrees `../finanzer_next-f67prep` (lo usa la tarea programada semanal de vigilancia), `-f3`, `-f2b`,
  `-f3prep`, `-f5prep` ni `-r1`.
- Secretos: la clave de Finnhub (`finanzer-finnhub`) y el User-Agent de la SEC (`finanzer-sec-ua`) viven en el
  Llavero; no los imprimas ni los escribas en archivos, fixtures, logs o el chat. E1 no los necesita: trabajas con el
  servidor de replay (`backend/tests/replay_server.py --env panel`), sin red.

## 2. Qué leer antes de empezar (por ruta absoluta)

Los documentos del rediseño están en la carpeta principal; si no aparecen en tu worktree, léelos por su ruta absoluta
en `/Users/joseestebanroa/Downloads/finanzer_next/`:

1. **El plan que vas a ejecutar, entero:**
   `docs/superpowers/plans/2026-10-17-rediseno-e1-sistema-e-historia.md`. Tareas 0–8 con código, tests y comandos.
2. **La especificación aprobada:** `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` (decisiones del
   usuario §2, arquitectura §3, sistema visual §5, verificación §7).
3. **Las maquetas aprobadas** en `docs/rediseno/maquetas/` (ábrelas en el navegador): `1-pagina-historia.html`,
   `2c-cabecera-con-escala.html`, `3-sistema-visual.html` y `4-parte-tecnica-y-tooltips.html`. Son la referencia
   visual: tu `/v2` debe parecerse a ellas.

## 3. Cómo trabajar

- Ejecuta el plan **tarea por tarea y en orden**, con la skill `superpowers:subagent-driven-development` (o
  `superpowers:executing-plans`). TDD: el test falla primero, luego pasa; un commit por tarea con el mensaje del plan,
  terminado en la línea de coautoría habitual.
- **El contrato manda.** Si un nombre de campo del plan no coincide con `frontend/src/lib/api.ts` (lo detecta `tsc` o
  un test), ajusta tu código al contrato, nunca el contrato.
- **Ninguna cifra ni lectura inventada.** Todo texto de la página sale del `display` del motor. Si un capítulo se queda
  sin dato para un ticker, se muestra "Sin dato" (regla del plan, Task 5), nunca texto escrito por ti.
- **Sin literales de análisis** en `/v2`: el guardián `check-analysis-literals.mjs` se amplía a `/v2` en Task 2. Las
  bandas de las puntuaciones salen de `thresholds.toml` vía `SCORE_BANDS` (Task 1).
- **Simetría** (preferencia firme del usuario): sin huecos muertos, filas de igual alto, espaciado solo de la escala
  4·8·12·16·24·32·48. Si el test de simetría (Task 7) falla, se corrige el CSS, **nunca el test**.
- **Sin neón:** ninguna sombra ni brillo de color de marca; solo los tokens de la spec §5.
- Si algo del plan es imposible tal cual (p. ej. el replay no sirve la serie de precios, o la API de Lightweight Charts
  difiere de la versión instalada), aplica la alternativa que indica el propio plan en ese paso y anótala como
  desviación con su motivo.
- Toda afirmación de "hecho" va con la evidencia: la salida del comando o una captura.

## 4. Puntos de parada

- **Parada intermedia (al cerrar Task 4):** enseña al usuario la cabecera de `/v2/AAPL` en claro y en oscuro (captura)
  y pregunta si va bien antes de construir los capítulos. Si pide cambios, hazlos y vuelve a enseñarla.
- **Parada final (Task 8):** presenta el enlace local (`http://localhost:3000/v2/AAPL` con el replay levantado), las 32
  capturas de `docs/rediseno/capturas-e1/`, el resultado de simetría, accesibilidad y Lighthouse, y la comprobación de
  que la web actual no cambió (`git diff main --stat` vacío en los archivos de la web actual). **Detente.** Itera con
  sus comentarios hasta un "aprobado" explícito y registra la aprobación literal.

## 5. Cierre

Deja `docs/rediseno/E1_REGISTRO.md` en tu rama (el plan, Task 8, Step 3, dice qué incluir), aunque quede a medias. El
planificador lo llevará a la bitácora y escribirá el plan y el prompt de E2. Rama sin push ni merge.

## 6. Definición de terminado

- [ ] Tareas 0–8 del plan hechas, con un commit por tarea.
- [ ] `npm run test:v2`, `npm run e2e:v2` (escritorio y móvil), `npm run check` y la suite del backend, todos en verde.
- [ ] 8 tickers × claro/oscuro × escritorio/móvil: capturas generadas, simetría PASS, sin desbordamiento horizontal.
- [ ] Accesibilidad sin infracciones graves en claro y oscuro.
- [ ] Web actual intacta, demostrado con el `git diff --stat` de Task 8.
- [ ] Aprobación explícita del usuario registrada; rama sin push ni merge.
