# F10 · Bloqueantes del modelo general (B1 y B2): registro

Rama `fiabilidad/f10-bloqueantes` desde `rediseno/v4-f8` en ccacd828. Encargo del PM tras el escaneo del modelo
general (`docs/modelo/ESCANEO_2026-10-28.md`, rama `modelo/general-inventario` en 06b7d51a). Cambios de golden con su
causa: `GOLDEN_DIFF_F10.md` (secciones B1 y B2).

## B2 · Cifras dobles (11 empresas, todas de la historia de 10 años frente al gráfico)

| Caso | Causa | Arreglo (en origen) |
|---|---|---|
| EIX, IVZ, APA | EDGAR etiqueta el beneficio de los propietarios (`NetIncomeLoss`) y el disponible para el común; la serie de la ventana mezclaba los dos y el gráfico caía a Yahoo | El del accionista común primero en `sec_edgar.CONCEPTS` (decisión del PM) y en la serie FY de Yahoo; un concepto completa años de otro solo si coinciden en el último común |
| TKO | Constituida en 2023: EDGAR no tiene 2022 y mandaba la fuente entera (la predecesora) | Los ejercicios anteriores al primer informe anual del emisor: sin dato, con su motivo |
| BE | EDGAR sin el beneficio de 2024 y 2025; en los comunes coincide con Yahoo (0,1 %) | Misma definición (± 2 %): EDGAR los suyos, la fuente los que faltan, y se dice |
| NTAP | `Revenues` es una parte (5,907 frente a 6,572 millones en FY2025) y ganaba por orden | Ingresos: el total entre los conceptos que llegan al último ejercicio |
| LHX, KDP | El cambio de ejercicio deja dos periodos anuales solapados (dos «FY2019») | Manda el más reciente |
| IDXX | La puntuación usaba el ROE escalado por una normalización por debajo de su umbral (70.6 % frente a 70.67 %) | Sin la etiqueta «normalizado», el reportado; y la columna del desglose con la precisión de la tabla |
| CBOE, SO | Los mismos conceptos mezclados | Ídem |

`tests/coherence.py <carpeta>` y `FINANZER_SCAN_CACHE` (test_coherencia_f9) corren el detector sobre los análisis
guardados del escaneo: los 11 del escaneo del 28-oct salen con el código anterior; reanalizados con este, 0.

## B1 · Vacíos sin motivo (289 en 97 empresas; el 59 % en 10 campos)

Casi todos son denominadores ≤ 0 registrados como «sin dato» sin motivo: ROE y D/E con patrimonio negativo (ABBV, AZO,
BKNG, CAH, DELL), P/FCF con FCF negativo (AMZN, BA), P/E con beneficio negativo, EV/EBITDA con EBITDA negativo; el resto,
FFO de REIT sin Nareit y empresas nuevas (FERG, HONA). Regla única en `lib/empty_reasons.py` (puntuación y display,
web y PDF). En vivo, 12 de las de más vacíos del escaneo (ABBV, AZO, BKNG, AMZN, BXP, FERG, HONA, ANET, MRNA, BA,
FISV, NTRS): 0 vacíos sin motivo.

## Veredictos

| Empresa | Cambio | Causa |
|---|---|---|
| BAC | Precio 50 → 48 | B2: beneficio del común (sin preferentes): P/B justificado 0.99x → 0.93x |
| BCS | Calidad 71 → 68, precio 58 → 52, confianza media → baja | B2: beneficio del ordinario (sin cupones AT1): P/B justificado 0.79x → 0.64x, convergencia baja |
| HSBC | Calidad 69 → 72 | B2: la serie FY del ordinario (antes `ProfitLoss`, con minoritarios): BPA TTM coherente y Calidad de ganancias 10 → 13 |
| TM | Precio 31 → 25, confianza media → alta | B1: P/FCF con FCF negativo pasa a «n. s.»: la cobertura sube y el precio deja de contraerse |

## Fusión en la v4 (sobre f10-motor, b00993f3)

Golden, fixtures y contrato regenerados una vez sobre todo el motor (N1–N4, N2, N2b, B3 más B1/B2). Frente a
b00993f3 cambian los veredictos de las tres empresas de B2 y ninguno más:

| Empresa | Motor (b00993f3) | Fusión | Causa |
|---|---|---|---|
| BAC | calidad 67, precio 48 «razonable», baja | 67, 42 «exigente», baja | B2: beneficio del común (28,095 frente a 29,487 millones): P/B justificado 0.99x → 0.93x (bloque P/B −2 → −3). **Solo de la fusión:** N2 resta a la industria las cifras de la empresa con el mismo beneficio del común, así que la referencia del P/E sin BAC pasa de 14.25x a 14.08x y su P/E de 12.72x queda «en línea» (90.4 % de la referencia; «atractivo» exige ≤ 90 %, `pe_value_mults`) en lugar de «atractivo» (bloque BPA +1 → 0). Valoración 9 → 7 |
| BCS | 71, 54 «razonable», media | 68, 50 «razonable», baja | B2: beneficio del ordinario (sin cupones AT1): P/B justificado 0.79x → 0.64x; P/B frente al sector dice barata y el justificado cara: convergencia baja, confianza baja y la calidad se contrae |
| HSBC | 66, 45, baja | 69, 45, baja | B2: serie FY del ordinario (antes `ProfitLoss`): P/E 13.78x → 13.05x y Calidad de ganancias 10 → 13 |

- **TM** ya no cambia de veredicto (en la rama B1 subía a confianza alta): con N2 su convergencia es media y pone el
  techo en media. B1 sigue actuando: P/FCF «n. s.» (flujo de caja libre negativo), cobertura alta en lugar de media, y
  el resumen dice «por sus dimensiones sería alta; la limita: la convergencia es media».
- **`confidence_limits`:** las dos ramas adaptaron el escalón de N4; queda la de f10-motor (techos → tasas base → Ke,
  el orden en que se aplican, con su redacción «las tasas base —solo el x % … no contrae el precio—»). De la de B1 queda
  el test de que un escalón que no baja la confianza («ya estaba en baja») no es un límite.
- **El beneficio del común en la exclusión de la empresa (N2):** el P/E de Damodaran es capitalización / beneficio, y
  la capitalización es la del común; restar el del común (el de B2) es la definición coherente. Su página de
  definiciones no aclara si su total es antes o después de preferentes: si fuera antes, BAC volvería a una referencia
  de 14.25x. Se señala al PM.
- Tests: vitest, el caso de confianza media que solo contrae el precio pasa de JPM (alta con N2) a O; e2e, TM vuelve a
  ser el caso de la frontera («confianza media; en la frontera con «exigente»»), como en el motor.
