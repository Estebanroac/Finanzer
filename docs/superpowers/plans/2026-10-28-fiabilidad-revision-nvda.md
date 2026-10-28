# Fiabilidad · Revisión externa del informe de NVIDIA (28-oct-2026) — Plan F10

Revisión: `docs/fiabilidad/revision-nvda-2026-10-28.md`. Base: `rediseno/v4-f8` en e20de9f8. Mismos principios que F8/F9
(verificar antes de corregir, reglas generales en config con test, presupuesto 0, sin dato antes que aproximación,
GOLDEN_DIFF_F10.md con causas, re-correr NVDA + las 26 de la auditoría + NU al cerrar). Nada de lo que la auditoría
dio por bueno en §2 («contexto que no puntúa», DCF inverso con tasas base) cambia de naturaleza: las tasas base pueden
mover la **confianza**, no el precio.

| # | Hallazgo | Qué se hace | Quién |
|---|---|---|---|
| N1 | Ganancias no operativas en el beneficio normalizado | Prueba de coherencia: beneficio neto frente a (resultado operativo + ingresos financieros netos) × (1 − t efectiva o legal); el exceso por encima de una tolerancia en config se normaliza (fuera del P/E normalizado, ROE y margen neto que puntúan) y se marca con su cifra. Verificar primero con EDGAR qué partida es (otros ingresos, ganancias de inversiones) | E2a |
| N2 | La empresa pesa mucho en el agregado de su industria | Si su peso en el agregado de Damodaran supera un umbral en config, la referencia se recalcula **sin ella** (agregado − la empresa, con sus cifras a la fecha del conjunto de datos) o, si no se puede, la mediana de pares del universo; declarado. Afecta al bloque de múltiplos y a la fortaleza «cotiza con descuento» | E2a |
| N3 | PEG con crecimiento del BPA desde un año valle | El crecimiento del BPA usa el mismo método robusto que los ingresos (regresión log-lineal o mitades, el que se use) y, si el año base está marcado como anómalo y no hay alternativa robusta, PEG n.s. | E2a |
| N4 | Votos correlacionados en el bloque de múltiplos; tasas base sin efecto | Los múltiplos que dependen del mismo BPA (P/E, forward P/E, PEG) cuentan como una familia con tope conjunto (no tres votos); y si el DCF inverso exige un crecimiento que según las tasas base sostuvo < 5 % de las comparables, la confianza baja un escalón (el precio no se toca) | E2a |
| N5 | Rivales «aún no estaban listos» en el PDF | Diagnosticar por qué el PDF sale antes que los rivales de esa empresa (prioridad en la cola, espera acotada al generar el PDF o rivales del caché); el PDF los incluye cuando existen o lo dice con su motivo | Independientes |
| N6 | Menores | ROE «amplificado por recompras» solo si el apalancamiento DuPont lo respalda; PEAD con el trimestre **fiscal** real de la empresa; nota de persistencia que nombre su umbral (80) distinto del de «excelente» (85); motivo de confianza «techo en baja» redactado para el lector | Independientes |
| — | E7 (DCF de tres impulsores) y M5 (EDGAR como fuente principal de todo) | Siguen en Fase B/C, después de la v4; se dice así en V4_CIERRE | — |

Ramas desde e20de9f8: `fiabilidad/f10-motor` (E2a) y `fiabilidad/f10-presentacion` (independientes). La portada rápida de
E2b va en `rediseno/v4f8-portada-rapida`. Se fusionan las tres en `rediseno/v4-f8` y se repite la pasada mínima (suites,
V2 real con NVDA + 7, coherencia, carga corta).
