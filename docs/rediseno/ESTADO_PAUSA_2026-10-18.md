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

## PAUSA 2 (27-oct-2026 ~03:45 UTC) — dónde queda cada cosa

| Rama | Punta | Estado |
|---|---|---|
| `rediseno/v4` | `feb7de5b` | **V4b completo**: secciones (7428f8f), nada oculto (e959f76), cabecera corta en móvil (daaa98a), lag medido (6d29c93), datos faltantes + rivales del replay (fusiones 0ab9d56, feb7de5), colores y ausencias (0e79b282). e2e:v2 ×4: 792/793 (1 fallo de tiempo en tableta, pasa solo). Falta: pasada final V1–V5 y `V4_CIERRE.md`. |
| `fiabilidad/f8-auditoria` | `23b479cc` (WIP de E4; E1 cerrado en 5d219d84) | Auditoría Fase A, cadena de valoración (sesión «Rediseño E2a»): **E1 hecho**; E4 empezado en WIP sin pruebas (Ke y beta; 15/43 golden cambian, 1 nivel de precio, NFLX). Falta: E4+E5 → E2 → E8 → E9 → E11 (+ peso de Altman) → P3. Luego, en `rediseno/v4b-datos`: referencias extra de Damodaran (solo lectura) y rivales de V. |
| `fiabilidad/f8-independientes` | `2e6a9031` | Sesión «Auditoría F8: correcciones independientes»: **E3 hecho** (FFO Nareit; PLD → exigente, O → atractivo). BRK-B sin cambios. Falta: repetir la suite completa; REIT con participadas materiales → «sin dato» (decisión del PM, SPG); E6, E10 (variante/exclusiones) e historia 10 años EDGAR (diseño ya escrito en `F8_INDEPENDIENTES_REGISTRO.md`). |

Después: fusionar las dos ramas F8 en la v4 (golden juntos, cada GOLDEN_DIFF con su causa) → pasada final completa →
`V4_CIERRE.md` → avisar al usuario (prueba con datos reales en local) → E6 con su «ok, pushea». Pendiente menor: país
del emisor en inglés.

## Reanudación (27-oct-2026)
El usuario dijo «comanda que todo arranque de nuevo». E2a retoma F8 desde 23b479cc; F8 independientes, desde 2e6a9031
(regla SPG → E6 → E10 → historia 10 años); E2b adelanta en `rediseno/v4` el país en español y una pre-pasada final
(`docs/rediseno/V4_PREPASADA.md`) que se repite tras fusionar F8.

## PAUSA 3 (27-oct-2026, noche)
Todo el desarrollo está hecho y fusionado en `rediseno/v4-f8` (punta ≥ 2c39b9cd): V4b, F8 Fase A completa (E1–E11, P3),
F9 (revisión de NU: R1–R7, R1b, R1c continuo, R2b, R3, R6) y el arreglo del test del carrusel. Faltaba solo la pasada
final oficial de E2b: hechas suites, carga, V3, V5 y V2 con fuentes reales; pendientes la prueba de carga larga, V1 y
Firefox (lo corre el PM fuera del sandbox), y cerrar `docs/rediseno/V4_CIERRE.md` (borrador escrito). Después: avisar
al usuario y E6 con su «ok, pushea». Copia de prueba con datos reales: worktree `../finanzer_next-prueba` (ba47b009),
servidor `v4-prueba-real` en el puerto 8790, web nueva en `/v2`.
- Estado exacto de E2b al pausar: WIP e16e786b en `rediseno/v4-f8`. Hecho: backend 6.028/0, vitest 142, e2e:v2 871/0,
  perf 3/3, V3 (2 fallos arreglados en 3160c4c5), carga 72/72, V5, Lighthouse escritorio 100 (CLS 6c26eab4), V2 real 7/7
  con coherencia 0/0. **Ojo:** la carga de 5 min dio memoria +42,6 MB (falla el criterio) y pico de 409 MB; Render tiene
  512 MB. Al retomar, lo primero es la carga de 12 min para distinguir fuga de excursión, y si es fuga, diagnosticarla
  antes de E6. Falta también V1 y Firefox.

## V4 TERMINADA (28-oct-2026)
`rediseno/v4-f8` en e20de9f8: v4 + F8 + F9 + rendimiento + pasada final oficial (V4_CIERRE.md). Memoria definitiva en la
carga de 12 min: pico 388 MB (margen 124 MB frente a Render). Copia del usuario en `../finanzer_next-prueba` (e20de9f8),
servidor `v4-prueba-real`, http://localhost:8790/v2. Siguiente: el usuario prueba; E6 (migración) solo con su «ok, pushea»
(plan `2026-10-18-rediseno-e6-migracion.md`: recalibrar la pantalla de carga en Render, probar MALLOC_ARENA_MAX=2).

## PAUSA 4 (28-oct-2026, tarde-noche)
Integración `rediseno/v4-f8` en ccacd828: v4 completa + F8 + F9 + rendimiento + portada rápida (bfb17aa0) + F10
presentación (N5 rivales en el PDF, N6 menores). Pendiente, en este orden:
1. **E2a · `fiabilidad/f10-motor`** (worktree ../finanzer_next-f10): N1 (no operativo), N3 (PEG), N4 (familia BPA + tasas
   base solo en la confianza visible) hechos; N2 (referencia sin la propia empresa, continua) en commit al pausar.
   Falta: **N2b** — región de la industria por dónde opera (como F9·R1) y ROE estable del P/B en dos etapas hacia la
   industria global sin la empresa (caso CB: «atractivo» por comparar con aseguradoras europeas); **B3** — alertas con
   la misma referencia que fila y puntuación; fusionar en v4-f8.
2. **Independientes · `fiabilidad/f10-bloqueantes`** (desde ccacd828): B1 vacíos sin motivo → «n.s.» con motivo; B2
   cifras dobles (EIX, IVZ, APA, TKO, LHX, KDP, NTAP, IDXX) con serie FY única; fusionar.
3. **Modelo general · `modelo/general-inventario`** (06b7d51a, 4013f9cc, f93aa3d7): fusionar en v4-f8 (tools/reglas/docs,
   sin cambiar puntuaciones) y escaneo de control de las 543; otro escaneo tras B1–B3 = puerta de la v4.
   Propuesta `docs/modelo/ESPEC_MODELO_GENERAL.md` (47 → 12 variables) para presentar al usuario tras la v4 (4 preguntas).
4. **E2b**: pasada mínima tras todo lo anterior (suites, V2 real NVDA + 7, coherencia, carga de 12 min **con** rivales
   de fondo activos desde N5; avisar si > 450 MB). Luego actualizar la copia del usuario (:8790/v2) y avisarle.
5. E6 solo con «ok, pushea».

## PAUSA 5 (29-oct-2026)
- `fiabilidad/f10-motor`: N1, N2, N3, N4 y **N2b** (solo la regla del ROE estable hacia la industria global sin la
  empresa; la regla de región por geografía de ingresos se retiró: la referencia de múltiplos es la región en la que
  Damodaran clasifica a la empresa). **B3** (alertas con la misma referencia y función que su fila) en commit o WIP al
  pausar. Falta: fusionar en `rediseno/v4-f8` (ccacd828) y avisar.
- `fiabilidad/f10-bloqueantes` (c361a26b): B1 y B2 cerrados, suites en verde; se fusiona **después** de f10-motor.
- `modelo/general-inventario` (f93aa3d7): se fusiona tras F10 y corre el escaneo de control; otro tras todo = puerta.
- Luego E2b: pasada mínima (suites, V2 real NVDA + 7, coherencia, carga 12 min con rivales de fondo).
- Copia del usuario: `../finanzer_next-prueba` (e20de9f8, aún sin F10), servidor `v4-prueba-real` :8790.

## V4 FINAL CON F10 (30-oct-2026)
- `rediseno/v4-f8` = **ad178cb9**, sin push. Dentro: F10 completo (N1–N4, N1b, N2/N2b, B1–B3), modelo general
  (invariantes + escaneo), crecimiento desde base anómala (con cota), margen operativo con una sola verdad (TTM de
  EDGAR reexpresado, cargos con etiquetas estándar, solo se recorta lo nombrable), beta con semanas completas,
  reintento de EDGAR con caché.
- Puerta: 543 empresas, todas las reglas a 0 salvo beta < 0,4 (9, post-v4). Pasada final (V4_CIERRE §2.5): suites
  verdes, V2 real 8/8 y coherencia 0, loading_expected_s 4,81, carga 12 min con pico 419 MB (Render 512).
- Copia del usuario `../finanzer_next-prueba` en ad178cb9, servidor `v4-prueba-real` :8790 (/v2/<TICKER>).
- Post-v4 (cola): M2 (ROE agregado, ROA, ROE→ROIC); excesos sin nombre (F, NOC, utilities); etiquetas propias de
  cargos (ON, MO, ALB, EL, SJM, ECHO); beta < 0,4 y filtro continuo de R²; P/E con BPA de EDGAR (WEC); SKYD;
  `retried` en la procedencia; rivales más lentos con N5 (p50 112 s); Damodaran antes/después de preferentes (BAC);
  4 preguntas de la especificación del modelo general.
- Siguiente: el usuario prueba; E6 solo con «ok, pushea» (calentar /v2, MALLOC_ARENA_MAX=2).

## V4 LISTA PARA E6 (30-oct-2026, noche)
- `rediseno/v4-f8` = **e550fe37**, sin push. Desde ad178cb9 entraron: PDF rápido (31 → ~10 s, rivales con
  capitalización en USD), revisión de COST (BPA desde EDGAR, PEG con el crecimiento mostrado, regla de contracción, una
  cifra del DCF), ayudas «?» desplazables, cola de fondo a un turno con usuarios, pase móvil (rejilla, .numtable,
  escalera con subgrid, safe-area, notas sin jerga) y EBITDA sin amortización operativa recurrente (NFLX, TTWO, KDP).
- Tanda final (V4_CIERRE §2.7): suites verdes, V2 real 9/9 con coherencia 0, picos de carga 448/444/412 MB (mediana 444).
- Copia del usuario en e550fe37 (:8790) y simulador iPhone 17 Pro Max (7B0944BA…).
- Post-v4 añadido: hallazgos 1, 3 y 5 de COST (márgenes en alta rotación, arrendamientos frente a Damodaran), ventana 0
  de la cola, BPA de TM/CSCO/HDB/MUFG/SMFG, `retried` en la procedencia.

## V4 FINAL (31-oct-2026, madrugada)
- `rediseno/v4-f8` = **79810091**, sin push: + color en las barras de posición (web y PDF; regla A–E de E1, aprobada
  por el usuario) y tarjetas del carrusel compactas en móvil (solo las tarjetas). §2.8: suites verdes, V2 real 9/9,
  coherencia 0, pico 437 MB. Copia del usuario y simulador en 79810091. Falta solo «ok, pushea» para E6.
