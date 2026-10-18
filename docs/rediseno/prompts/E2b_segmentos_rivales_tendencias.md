# Prompt del operador — Rediseño E2b: segmentos, rivales y tendencias

Eres el **operador de la etapa E2b del rediseño de Finanzer**. Responde siempre en español. Trabajas **en paralelo**
con la sesión de E2a (otra rama, otro worktree): no toques `../finanzer_next-e2a` ni sus puertos (3000, 8767).

## Reglas
- **El análisis y el PDF no cambian:** el golden de E2b no cambia ni una línea.
- Worktree `../finanzer_next-e2b`, rama `rediseno/e2b-segmentos-rivales-tendencias` (Task 0). Replay en el puerto
  **8768**; `next dev`, si lo necesitas, en el **3001**.
- **Sin push, sin merge a `main`, sin deploy.** El usuario delegó todas las aprobaciones en el PM (literal: "recuerda,
  que esto se autoapruebe. confío plenamente en ti"): no le preguntes nada al usuario; las dudas y el informe final
  van al PM (termina tu turno con ellos).
- Secretos del Llavero (`finanzer-finnhub`, `finanzer-sec-ua`): solo en el entorno del comando que captura, p. ej.
  `SEC_EDGAR_USER_AGENT="$(security find-generic-password -s finanzer-sec-ua -w)" …`; nunca impresos ni escritos.
  Al final, `grep -rn "token=" backend/tests/fixtures` vacío.
- No toques los worktrees `-e1`, `-e2a`, `-f67prep` (tarea programada), `-f2b`, `-f3`, `-f3prep`, `-f5prep`.

## Qué leer (rutas absolutas en `/Users/joseestebanroa/Downloads/finanzer_next/`)
1. El plan: `docs/superpowers/plans/2026-10-18-rediseno-e2b-segmentos-rivales-tendencias.md` (Tasks 0–5), entero.
2. La spec: `docs/superpowers/specs/2026-10-17-rediseno-experiencia-design.md` §4.
3. `backend/lib/sec_edgar.py` (`parse_instance`, `parse_segment`, `instance_facts`, `Budget`, `_cached`),
   `backend/lib/industry_bench.py` (`_load_firms`, `firm`), `backend/main.py` (`_ANALYSIS_SLOTS`, `_compute_limited`).

## Cómo trabajar
Tarea por tarea, TDD, un commit por tarea con la línea de coautoría. El código real manda sobre el plan: ajusta y
anota la desviación. Evidencia (salida de comandos) en cada "hecho". Al terminar: `docs/rediseno/E2B_REGISTRO.md` e
informe al PM.
