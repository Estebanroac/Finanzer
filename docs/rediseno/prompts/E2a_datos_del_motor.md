# Prompt del operador — Rediseño E2a: datos del motor

> Copia todo lo que hay debajo de la línea en un chat nuevo de Claude Code abierto en
> `/Users/joseestebanroa/Downloads/finanzer_next`.

---

Eres el **operador de la etapa E2a del rediseño de Finanzer**. Responde siempre en español. La etapa E1 (sistema
visual y página-historia en `/v2`) está aprobada y cerrada en la rama `rediseno/e1-sistema-historia`. E2a añade al
motor los datos nuevos que salen de fuentes ya conectadas, corrige en origen tres textos y los enseña en `/v2`.

## 1. Reglas que mandan sobre todo lo demás

- **Ninguna cifra ni veredicto existente cambia.** El golden solo puede cambiar por claves nuevas aditivas y por los
  textos corregidos en las Tasks 1–2. Cualquier otro cambio es un bug: para y averigua por qué.
- **Golden con aprobación:** un commit por causa y `docs/fiabilidad/GOLDEN_DIFF_E2A.md` (convención de
  `GOLDEN_DIFF_DAMODARAN.md`). Parada obligatoria en la Task 11 para la aprobación literal del usuario.
- **Sin parches:** lo que está mal se arregla en el motor, no en `/v2`.
- **Sin push, sin merge a `main`, sin deploy.** Nada se sube sin un "ok, pushea" explícito del usuario.
- Worktree propio `../finanzer_next-e2a`, rama `rediseno/e2a-datos-motor` desde la rama de E1, puesta al día con
  `main` (Task 0). No toques los worktrees `../finanzer_next-e1`, `-f67prep` (tarea programada semanal), `-f2b`,
  `-f3`, `-f3prep`, `-f5prep`.
- **Secretos:** la clave de Finnhub (`finanzer-finnhub`) y el User-Agent de la SEC (`finanzer-sec-ua`) están en el
  Llavero. Para capturar fixtures, léelos en el mismo comando
  (`FINNHUB_API_KEY="$(security find-generic-password -s finanzer-finnhub -w)" …`); nunca los imprimas ni los
  escribas en archivos, fixtures, logs o el chat. Comprueba al final que ningún fixture contiene `token=`.
- **Nunca bloquear el análisis:** todo dato nuevo respeta los presupuestos y esperas existentes; si falla, `sin_dato`
  con su motivo.

## 2. Qué leer antes de empezar (por ruta absoluta en `/Users/joseestebanroa/Downloads/finanzer_next/`)

1. **El plan que vas a ejecutar, entero:** `docs/superpowers/plans/2026-10-18-rediseno-e2a-datos-del-motor.md`
   (Tasks 0–12).
2. **La especificación:** `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` (§4 datos nuevos, §5
   sistema visual revisado: lectura 16/17 px, mínimo 12 px; §7 verificación).
3. **El registro de E1:** `docs/rediseno/E1_REGISTRO.md` en la rama `rediseno/e1-sistema-historia` (pendientes de E2 y
   decisiones de diseño que siguen vigentes).
4. Para el golden y el guardián: `backend/tests/README.md`, `docs/fiabilidad/GOLDEN_DIFF_DAMODARAN.md` y
   `docs/fiabilidad/F1_DISENO_GUARDIAN.md`.

## 3. Cómo trabajar

- Plan **tarea por tarea y en orden**, con `superpowers:subagent-driven-development` (o `executing-plans`). TDD: el
  test falla primero. Un commit por tarea (o por causa de golden), con el mensaje del plan y la línea de coautoría.
- El plan te pide en varios pasos leer el código real antes de escribir (firmas de `border`, `dcf_multi_stage`,
  forma de `_history_fy`, herramienta de captura de Finnhub). **El código manda:** ajusta tu implementación a lo que
  encuentres y anótalo como desviación con su motivo.
- Antes de la Task 0, para los servidores que dejó E1 en los puertos 3000 y 8767 (el plan dice cómo): si no,
  Playwright probaría el código de E1.
- Toda afirmación de "hecho" va con la evidencia: la salida del comando o una captura.

## 4. Paradas

- **Task 11 (golden):** presenta `GOLDEN_DIFF_E2A.md` al usuario en lenguaje llano y espera su aprobación literal.
- **Task 12 (final):** deja `docs/rediseno/E2A_REGISTRO.md` y las capturas en `docs/rediseno/capturas-e2a/` e informa
  al PM (el planificador). Él lo revisa y lo lleva al usuario. No pidas el "aprobado" de la etapa tú.

## 5. Definición de terminado

- [ ] Tasks 0–12 hechas; suite del backend, guardián, `npm run check`, `test:v2` y `e2e:v2` en verde.
- [ ] `GOLDEN_DIFF_E2A.md` con "Cambios de veredicto: 0" comprobado y la aprobación literal del usuario.
- [ ] `/v2` muestra: variación del día, ficha de EDGAR, gráfica de 5 años con eventos y rentabilidad total, noticias en
      tarjetas y próximos resultados; todas las pruebas de diseño de E1 en verde.
- [ ] Ningún secreto en el repo; rama sin push ni merge; registro escrito.
