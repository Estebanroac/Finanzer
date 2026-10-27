# Rediseño (v4) · Estado en la pausa del 18-oct-2026 (≈23:10 UTC)

El usuario pidió pausar («deten a todos los agentes. mantén el mapa y la ruta clara de lo que falta y de lo que hemos
hecho»). Todo está en local: **nada pusheado, `main` remoto sin tocar, la web en producción sin cambios**.

## Dónde está cada cosa

| Qué | Rama | Punta | Notas |
|---|---|---|---|
| **Integración de la v4** | `rediseno/v4` | `f6f108f` | Worktree `../finanzer_next-v4` (sesión «Rediseño E2b» = operador E3). Todo lo aprobado hasta V6b. |
| **WIP del análisis seccionado** | `rediseno/v4b-secciones-wip` | `6192a6a` | Copia de seguridad del trabajo **a medias y sin probar** de E3 (39 archivos). El mismo trabajo sigue sin commitear en el worktree v4, tal cual lo dejó: al retomar, E3 continúa desde su worktree (o desde esta rama si el worktree se hubiera perdido). |
| **Datos y cintillo (V4b)** | `rediseno/v4b-datos` | `fcb87a6` | Worktree `../finanzer_next-e4` (sesión «Rediseño E2a» = operador E4). Hecho: cintillo arranca a 0 ms. La auditoría de datos faltantes estaba empezando (sin resultados guardados). |
| Portada P8b (ya fusionada en v4) | `rediseno/p8b-portada` | `b85ad96` | Congelada. |
| E4 portada (ya fusionada en v4) | `rediseno/e4-portada` | `912e606` | Congelada. |
| Planes, registro de aprobaciones, este documento | `main` local | — | Sin push. |

Sesiones: «Rediseño E2b» (`local_9eb0b5ce…`) y «Rediseño E2a» (`local_45849846…`) detenidas, abiertas y con su contexto.
Servidores de prueba parados. Regla: **ninguna sesión usa `git stash`** (la pila es común a todos los worktrees).

## Hecho (todo aprobado por el PM, ver `APROBACIONES_PM.md`)

- E1–E5 completas; V1–V7 de la primera verificación; fusión de E4 en la v4.
- V7 lector nuevo: motor M1–M7, M5 bis (una sola verdad del DCF), puntuación (P), industrias en español (N); presentación
  P1–P6 (glosario, concentración, rivales en el capítulo 6, segmentos, «?», línea de confianza en web y PDF p. 2).
- Portada P8/P8b: cintillo rotativo con mini-gráficas (1D/1S/1M/6M), listas por periodo con signo correcto, sectores,
  carrusel arrastrable que se reanuda solo, sin botón Pausar.
- Pantalla de carga con logo animado y 5 estaciones iguales (T_est = p95, 4,12 s en local; **recalibrar en Render en
  E6**); estado de error claro (adiós al «Analizando…» eterno).
- «?» que nunca ocupan la barra de capítulos; textos sin «motor»; «DCF directo/inverso» siempre nombrado.
- V6b (código y seguridad del delta): sin críticos; arreglos de portada y E1–E10 hechos.
- Medidas: 0 cambios de veredicto en 43 golden frente a `main`; análisis en frío 1,5–3,6 s local; memoria sin cambios
  apreciables con la descarga de 6 meses.

## Lo que falta (ruta, en orden)

Plan detallado: `docs/superpowers/plans/2026-10-18-rediseno-v4b-ajustes-usuario.md` (con la cita literal del usuario).

1. **E3 · análisis seccionado** (a medias): 9 secciones con ruta propia, `/v2/{T}` abre «La empresa», cada sección con su
   lectura + todo su detalle, cabecera fija con las tres puntuaciones, «Siguiente sección →»; sin página-historia larga.
2. **E3 · nada oculto**: desglose de puntuaciones siempre visible; sin acordeones, «Ver más» ni hojas para contenido.
3. **E3 · sin lag, medido**: CPU ×4, INP p75 ≤ 200 ms, cambio de sección ≤ 150 ms, sin tareas largas > 100 ms; test de
   rendimiento automatizado.
4. **E3 · colores**: todo valor con lectura con su tono y etiqueta (auditoría en AAPL, JPM, PLTR, O, BCS).
5. **E4 · datos faltantes**: recuento y clasificación (a/b/c) en el panel completo, arreglos en motor/datos/fixtures,
   informe `V4b_datos_faltantes.md`; lo de presentación pasa a E3 vía el PM.
6. Fusionar `rediseno/v4b-datos` en la v4.
7. **Pasada final completa** (V1 panel 3 navegadores × 3 tamaños × claro/oscuro; V2 fuentes reales; V3 fuentes caídas;
   V4 carga; V5 producción simulada; suites) y `docs/rediseno/V4_CIERRE.md`.
8. **Avisar al usuario** para que pruebe la v4.
9. **E6 (migración)** solo con su visto bueno y su «ok, pushea» (plan `2026-10-18-rediseno-e6-migracion.md`, incluye
   recalibrar la pantalla de carga en Render).

## Cómo retomar

1. Con el «arrancamos» del usuario: a la sesión «Rediseño E2b», «retoma el punto 1 desde tu worktree (tu trabajo sin
   commitear sigue ahí; copia en `rediseno/v4b-secciones-wip`)»; a «Rediseño E2a», «retoma el punto 5 en
   `rediseno/v4b-datos`».
2. Demo: los servidores de replay se levantan con `.claude/launch.json` (`v4-replay-8768` + `v4-next-3001`) o el build
   servido por `tests/replay_server.py --env panel --port 8769`.

## ALERTA ROJA (26-oct-2026): auditoría externa del motor

El usuario entregó una auditoría de 26 informes (nota 68/100; **7 de 26 veredictos de precio no utilizables**: VZ, AWK,
NEE, PLD, UNH, XOM, CB). Plan: `docs/superpowers/plans/2026-10-26-fiabilidad-auditoria-externa.md` (PDF y texto en
`docs/fiabilidad/auditoria-externa-2026-10-26.*`). **La Fase A (E1–E6, E8–E11, P3) bloquea la entrega de la v4 al
usuario**; la Fase B (DCF de tres impulsores E7, métricas por sector P2, backtest) va después como proyecto F8.

## Avance desde que se retomó (26-oct)
- V4b bloque 1 · análisis seccionado: HECHO (`rediseno/v4` 7428f8f), aprobado. Capturas enviadas al usuario.
- Pendiente menor para E4 (tras la Fase A de la auditoría): el país del emisor sale en inglés («United States»).
