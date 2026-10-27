# Fiabilidad · Auditoría externa del 26-oct-2026 (ALERTA ROJA) — Plan

> El usuario entregó `Auditoria_Finanzer.pdf` (11 p., copia en `docs/fiabilidad/auditoria-externa-2026-10-26.pdf`) y dijo:
> *"esto es alerta roja. hay que tenerla en el mapa. cuidado con esto"*.
> Muestra: 26 informes (MSFT, NVDA, LLY, UNH, JPM, CB, AMZN, MCD, GOOGL, VZ, CAT, UNP, KO, WMT, XOM, KMI, NEE, AWK,
> PLD, O, LIN, FCX, ASML, SAP, MRNA, BA), 11 sectores. Nota global 68/100. **7 de 26 veredictos de precio no son
> utilizables** (VZ, AWK, NEE, PLD, UNH, XOM, CB); el único «atractivo» de la muestra (VZ) es uno de ellos.

## Principios

- **Verificar antes de corregir.** Cada hallazgo se reproduce con datos reales en su ticker y se anota la evidencia
  propia (la auditoría pide confirmar varios: FFO de PLD contra el suplemento, 10-Q de AMZN/BA en EDGAR). Si un
  hallazgo no se reproduce, se documenta por qué y no se toca.
- **Estas correcciones SÍ cambian veredictos, a propósito.** Cada cambio de veredicto va en `GOLDEN_DIFF_F8.md` con su
  causa (E1…E11) y su justificación financiera; ningún cambio sin causa.
- **Sin parches:** reglas en el motor y umbrales en config, con test; nada de excepciones por ticker.
- **No tocar lo que la auditoría da por bueno** (§2: método por tipo de empresa, monedas, acciones, normalización,
  arrendamientos, financiera cautiva, FCF−SBC, g terminal, contracción hacia 50, avisos de frontera, falsación, DCF
  inverso con tasas base, contexto que no puntúa, bloque de múltiplos). Test de no regresión para cada uno.
- **Conjunto de referencia:** los 26 tickers, con las afirmaciones automáticas de la auditoría §6 como tests:
  AWK Ke ≥ Kd; VZ crecimiento del titular = 0,33 %; NEE bandera de pico activa; PLD FFO a ±10 % del reportado;
  GOOGL P/E de portada = normalizado (31,4x); MCD ROE = n.s.; AMZN y BA con estados al 30-jun-2026 (si EDGAR los
  tiene). Controles de pipeline: Ke ≥ Kd; β ∈ [0,4; 2,5] o sectorial; g ≤ Rf; mcap = precio × acciones ±2 %; ROE n.s.
  si patrimonio ≤ 0; PEG n.s. si crecimiento ≤ 0; estados < 100 días o bandera.

## Fase A — antes de entregar la v4 al usuario (bloqueante)

Orden de la auditoría (§5), impacto alto y esfuerzo bajo/medio:

1. **E1 · Ke y beta con controles de cordura.** Beta por defecto bottom-up (desapalancada de la industria Damodaran,
   reapalancada con la D/E propia); beta propia solo si R² ≥ 0,20, error estándar bajo y β ∈ [0,4; 2,5]; pisos
   Ke ≥ Kd + 1 pp y Ke ≥ Rf + 0,5 × ERP; Rf y ERP de la misma fecha; regla única y visible de fuente de beta; prueba
   de sensibilidad ±1 pp de Ke → «dependiente de Ke» y confianza −1 escalón.
2. **E4 + E5 · Titulares y anclaje.** VZ: el titular de crecimiento sale de la variable correcta; PEG = n.s. si el
   crecimiento del BPA ≤ 0 o no cuadra con el del informe; convergencia exige misma dirección y ningún múltiplo
   individual en lectura extrema contraria; FCF de telecom − media 5 años de espectro. Regla: si el motor marca una
   métrica «no fiable», portada y resumen usan la normalizada (GOOGL, AMZN).
3. **E2 · Bandera de pico de beneficio** (TTM > mediana 3 años + 40 % y consenso/forward lo desmiente → P/E del score
   con mediana/consenso y texto «beneficio TTM atípico»).
4. **E3 · FFO según Nareit** (− ganancias por venta de inmuebles, + deterioros, AFFO con fórmula visible, FFO del emisor
   como referencia si existe y alerta si difiere > 10 %).
5. **E8 · Fiabilidad del DCF sin mirar el precio** (peso del terminal, dispersión de la sensibilidad, estabilidad del
   margen FCF, banderas de datos); la distancia al precio afecta solo a la convergencia.
6. **E9 · Rentabilidad condicionada a ROIC − WACC** (tope 10/20 si < 0, 6/20 si < −3 pp; márgenes por percentil de
   industria; ROA/ROIC en lugar de ROE con apalancamiento alto).
7. **E6 · Frescura de estados** (cruce con el último 10-Q de EDGAR; usar EDGAR o marcar «desfasado»; > 100 días con
   10-Q posterior → cobertura «media»).
8. **E10 + E11 · Altman por SIC y regla de confianza** (Z original SIC 2000–3999, Z'' el resto; excluir utilities,
   midstream 4612/4922–4924, REITs y financieras con sustituto; bajar su peso; «la más baja manda» aplicada de
   verdad; contracción de la calidad ×0,85 con confianza baja; tratamiento de la saturación de calidad).
9. **P3 · Presentación:** ROE n.s. con patrimonio negativo (MCD); margen de seguridad oculto si el DCF es de
   fiabilidad baja, valor justo redondeado y rango p10–p90; una sola ventana de fuerza relativa; texto de Piotroski
   condicionado al dato de la empresa; etiquetas coherentes (CB β, MRNA crecimiento).

## Fase B — después de la v4, proyecto propio (F8)

- **E7 · DCF de tres impulsores** (ingresos, margen, reinversión; terminal con reinversión = g ÷ RONIC; traslado de
  costes desde el beneficio operativo; DCF inverso en FCF por acción desde FCF de mantenimiento). Es la corrección
  que más cambia el sistema; va después de E8.
- **P2 · Métricas por sector y pares:** bancos (CET1, NIM, calidad crediticia vía FDIC), aseguradoras (ratio
  combinado), REITs (AFFO, NAV, vencimientos), biotech (arquetipo pérdidas + meses de caja), pares por SIC de 4
  dígitos + industria + capitalización 0,2–5x; FCF histórico EDGAR con cascada de etiquetas de capex; vencimientos de
  deuda.
- **Validación de las puntuaciones:** backtest point-in-time (fecha `filed` de EDGAR), correlación de rangos con la
  rentabilidad a 12 meses por sector frente a un factor simple (FCF yield); prueba de sesgo sectorial.

## Reparto

- Operador del motor (sesión «Rediseño E2a», E4): Fase A en una rama propia desde la punta de la v4 de su línea
  (`rediseno/v4b-datos` o nueva `fiabilidad/f8-auditoria`), un commit por error, `GOLDEN_DIFF_F8.md`, informe
  `docs/fiabilidad/F8_AUDITORIA_REGISTRO.md` con evidencia propia por hallazgo.
- E3 (sesión «Rediseño E2b») solo para lo que sea de pintar en la web nueva (p. ej. rango p10–p90).
- El PM revisa cada error con los 26 tickers antes de aprobar.

## Fase C — de 86 a 96 (hoja de ruta del usuario, 26-oct-2026)

Segundo documento del usuario: `docs/fiabilidad/hoja-de-ruta-86-a-96-2026-10-26.{pdf,txt}`. Parte de **86/100** (la
nota esperada tras E1–E11 y los huecos sectoriales, es decir, Fases A y B) y propone 12 medidas para llegar a **96**
(techo realista 93–95). Ninguna bloquea la v4; es el proyecto de después.

| Fase | Medidas | Qué | Nota |
|---|---|---|---|
| C1 · Base de datos | M7, M5, M6, M12 | Instantáneas con fecha (Parquet + versión de parámetros); EDGAR companyfacts como fuente principal con conciliación de 8 campos ±2 %; taxonomía IFRS para 20-F (ASML, SAP, segmentos ≥ 95 %); fuente por cifra y registro de cambios de la metodología | ~89 |
| C2 · Validación | M1, M2 | Backtest point-in-time (IC frente a FCF yield, t > 2 en 2018–2026, estable en ≥ 8 de 11 sectores); pesos estimados y lectura por percentil de industria | ~92 |
| C3 · Incertidumbre | M3, M4, M9 | Valor justo p10/p50/p90 por Monte Carlo sobre los tres impulsores (requiere E7); ciclo completo en cíclicas y commodities; riesgos del 10-K ligados a impulsores con tornado | ~94 |
| C4 · Profundidad | M10, M11, M8 | Asignación de capital; métricas sectoriales fuera de XBRL (FDIC BankFind; extracción con LLM con verificación literal en la fuente); valoración del pipeline en biotech | ~96 |

**Punto de decisión tras C2 (de la propia hoja de ruta):** si la puntuación de precio no supera al FCF yield, C3
simplifica en lugar de refinar.

**Decisiones que serán del usuario (no del PM), cuando lleguemos:**
- **Datos de pago:** M1 necesita precios de empresas deslistadas (Sharadar, Norgate o similar) y M8 ventas máximas de
  consenso. Sin ellos, M1 no es válido y M8 tiene poco contenido. Coste y proveedor, a decidir por el usuario.
- **Uso de un LLM para M11** (extracción de suplementos y 8-K): coste por llamada y verificación literal obligatoria.
- **Prioridad:** la hoja de ruta advierte que, si la herramienta es para decisiones propias, M1 y M3 concentran casi todo
  el valor práctico y M10–M12 suben la nota con poco efecto en la decisión.

### Decisión del usuario sobre la Fase C (26-oct-2026): presupuesto 0

Literal: *"el presupuesto es 0. no hay plata. entonces, no inventemos data ni usemos data poco creíble. simplemente no
usemos esos datos de paga ni creemos indicadores con datos poco creíbles por no tener la versión paga. no importa
llegar a 96 entonces"*.

Regla: **solo fuentes gratuitas y fiables** (EDGAR/XBRL, Damodaran, FDIC BankFind, Finnhub gratuito, Yahoo como
respaldo conciliado, tasas base publicadas). Ningún indicador que necesite datos de pago para ser válido, y ningún
sustituto «aproximado» que lo imite.

| Medida | Decisión | Motivo |
|---|---|---|
| M7 instantáneas, M5 EDGAR principal + conciliación, M6 IFRS para 20-F, M12 fuente por cifra | **Se mantienen** | Gratuitas y oficiales |
| M4 ciclo completo en cíclicas | **Se mantiene** | Historia de EDGAR (7–10 años); precios de mitad de ciclo solo con series públicas fiables, si no, márgenes normalizados sin precio de commodity |
| M3 valor justo como rango (Monte Carlo) | **Se mantiene** (tras E7) | Supuestos de fuentes gratuitas publicadas (tasas base de Mauboussin, márgenes de Damodaran); la calibración «80 % dentro del rango» no se puede validar sin M1 y se declara así |
| M9 riesgos | **Solo la parte cuantitativa**: tornado de impulsores a partir de M3 | Asignar riesgos del 10-K a impulsores exige un LLM de pago o reglas poco fiables |
| M10 asignación de capital | **Se mantiene** | EDGAR + instantáneas propias (M7) |
| M11 métricas sectoriales | **Solo FDIC BankFind (bancos)**; ocupación de REITs y ratio combinado sin XBRL quedan «sin dato» declarado | La extracción con LLM tiene coste |
| M1 backtest | **Fuera** | Sin precios de empresas deslistadas el resultado tiene sesgo de supervivencia: no es válido |
| M2 pesos estimados | **Fuera la estimación** (depende de M1); la lectura por percentil dentro de la industria (Damodaran y nuestro universo) sí puede hacerse | — |
| M8 pipeline de biotech | **Fuera** | Sin ventas máximas de consenso no tiene contenido; se mantiene «sin valoración del pipeline» declarado |

La nota objetivo deja de ser 96: lo que importa es que cada cifra sea creíble.
