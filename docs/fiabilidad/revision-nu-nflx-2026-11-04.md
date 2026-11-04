# Revisión externa de los informes de NU y NFLX (4-nov-2026): verificación contra el código

Insumo: `informes-pdf/Diagnostico_Finanzer_NU_NFLX_2026-11-04.pdf` (19 hallazgos: T1–T7, N1–N5, F1–F5). Informes
leídos por el revisor: PDF v2 (`/api/v2/pdf`) de prod. Verificado contra `main` 43080175 (= prod, `/api/health`) y el
JSON de `/api/analysis/{NU,NFLX}` de prod del mismo día. Solo lectura: nada corregido todavía.

## 1. Veredicto por hallazgo

| ID | Revisor | Verificado | Causa raíz real (archivo:línea, `backend/`) | ¿Causa del revisor? |
|---|---|---|---|---|
| T1 NU | P0 | **Parcial** | `lib/self_exclusion.py:284` filtra pares por industria e **ignora la región** (19 pares: 8 EE. UU., 5 Europa, 2 Japón, 2 Canadá, 2 emergentes); `lib/industry_bench.py:180,207` cae a la mediana de pares cuando faltan las cifras de la empresa, sin estimar su peso por capitalización (NU pesa ~1,6 % del agregado emergente) | No: el sesgo va al revés (con la referencia emergente NU sale **más** cara, P/B 0,89x). «Pares de LatAm» inviable: 0 en el universo |
| T1 NFLX | P0 | **Confirmado** en ROE/margen; **refutado** en P/E | Sin Netflix (91 % del beneficio de la industria) la referencia queda en ROE 0,63 %; `lib/vs_reference.py:20` solo descarta una referencia igual a 0. El P/E 30x **no** está inflado (Damodaran solo usa empresas con beneficio); el «descuento» sale de comparar el precio de hoy (−46 %) con una industria a 5-ene-2026 | Parcial. Afecta a lecturas y alertas, no a la nota (P1) |
| T2 | P0 | **Confirmado** + causa extra | `lib/valuation_confidence.py:208-258` no mira insumos compartidos; además `main.py:2462-2473` compara el P/B **en bruto** con el sector, sin ajustar por ROE: todo banco más rentable que sus pares sale «caro» y «confirma» al justificado. Corregir T1 no lo arregla | Sí, incompleta |
| T3 NU | P0 | **Parcial** | El riesgo de crédito ya se declara «no medido» (F9·R6), pero `main.py:1099` lo marca «no puntúa» y `valuation_confidence.py:261-291` solo cuenta componentes del score → cobertura «Alta» | Sí |
| T3 NFLX | P0 | **Confirmado**, otra causa | **Regla muerta para todas las empresas**: `lib/alert_interpretations.py:819` lee `max_drawdown_1y`, que nada escribe (se perdió en 7ed6b36e); y las alertas se generan (`main.py:2393`) antes del contexto de mercado (`:2560`). NFLX −46 % y NU −38 % la dispararían | No |
| T4 NU | P1 | **Confirmado** | `lib/historical_metrics.py:150-153` declara la cota (48,8 %) y `:215-231` no la aplica; el detector de base anómala (`:141-143`, `thresholds.toml:518`) salta con cualquier crecimiento > 41 %/año aunque no haya valle; etiqueta «3 años» con ventana FY2020–FY2025 | Sí |
| T4 NFLX | P1 | **Parcial** | 2022 queda fuera de «anómala» por 0,25 pp; el PEG histórico es decisión explícita (revisión COST) | Parcial |
| T5 | P1 | **Parcial** | Rf: par Damodaran por diseño, desvío 35 pb < aviso de 50 pb (`config/valuation.toml:32`). Beta: la bottom-up nunca se contrasta (`lib/beta.py:162-174`): NU 0,60 frente a propia 1,32 ± 0,56; NFLX 0,79 frente a 1,65 de la fuente. Limitador: `lib/ke_sensitivity.py:45-50` solo mira el **nivel final**, no si un método cambia de voto | Piso por volatilidad: rechazado (la beta mide riesgo sistemático) |
| T6 NU | P1 | **Parcial** | `lib/market_context.py:426-435`: un solo ETF (sector, EE. UU.) y una sola ventana (1A). A 1 año NU cae ~31 pp más que EWZ (la conclusión aguanta); el último mes es del país (EWZ −25 %, NU −21 %), que es lo que cuentan los titulares | Parcial |
| T6 NFLX | P1 | **Confirmado** | `lib/market_context.py:497-513`: «sobrerreacción» con criterios solo retrospectivos; ignora la reacción PEAD (−7,8 %) que el motor ya tiene | Sí |
| T7 | P2 | **Confirmado** (5/5) | Fila «Precio de mercado» con la ayuda del atractivo en **todas** las empresas (`lib/display.py:2382`, clave `price`); título «DCF» sin condición (`lib/pdf_v2/chapters.py:480`); metodología escrita a mano (`lib/pdf_v2/methodology.py:62,120`); persistencia con margen neto «No aplica» (`lib/persistence.py:96,131-147`); Damodaran «referencia» y «excluido» (`methodology.py:64,76-91`) | Sí |
| N1 | P0 | **Confirmado** + 2.ª incoherencia | `lib/archetype_metrics.py:283` (implícito, una etapa) y `:299` (sensibilidad, una etapa); `apply_two_stage` (`:124-131`) no los actualiza. El mismo JSON da dos P/TBV justificados (3,05x y 2,54x). Con dos etapas, ROTE terminal implícito ≈ 22,1–22,3 %. La nota ya usa el de dos etapas: falla la narrativa, la banda y la sensibilidad | Sí |
| N2 | P0 | **Confirmado: mezcla de definiciones**, no error de cálculo | FY de EDGAR `ifrs-full:Revenue` (bruto, 15,78B) y TTM de Yahoo (neto, 13,17B). `lib/edgar_primary.py:76-82` solo sustituye el TTM en aseguradoras y bancos us-gaap; la discrepancia (−33 %) se anota en `reconciliation` y nadie actúa | Sí |
| N3 | P1 | **Confirmado** | `lib/cost_of_capital.py:174-193`: Ke en USD sin término de inflación; ROE/ROTE conservan la inflación BRL | Sí |
| N4 | P1 | **Confirmado** | `lib/financial_ratios.py:323-405` (salud = ROA + ROE + patrimonio/activos) y `:3721-3749` (ROE y ROA otra vez en Rentabilidad). ~86 FINANCIAL del universo | Sí (= S1 de la espec. del modelo general) |
| N5 | P2 | **Parcial** | «30 %» y «42 %» son **dos series distintas** (margen de intereses e ingresos): falla que la nota no nombra la serie. ROE sobre patrimonio final en **todas** las empresas (`financial_ratios.py:1549,1594`, contra su propia docstring). Media de ROTE con años de pérdidas (`archetype_metrics.py:200-207`; la regla F9·R7 existe en `_roe_stability` pero no aquí) | Parcial |
| F1 | P0 | **Parcial (P1)** | El DCF da +1 «barata» (+17,8 %) aunque con WACC +1 pp vale 65,86 < precio. Crecimiento = CAGR de ingresos (E7, Fase B); banda fija ±10 %; el limitador no salta porque el nivel final no cambia. El g del propio DCF solo lo sostuvo el 19 % de las comparables | Sí |
| F2 | P0 | **Confirmado** en la lógica; hoy solo texto | `lib/reverse_dcf.py:198-204`: con tasa base 25–75 % decide la historia propia, medida en otra métrica (ingresos por acción a 10 años). Hoy no vota (el directo no es «baja»); **arreglar F1 sin F2 lo haría votar +2 «barata»** | Sí |
| F3 | P1 | **Parcial**, otra causa | La normalización es correcta (pico no operativo de 2,73B en mar-2026, z 61,7; confirmar en el 10-Q). Falla el tope de credibilidad (`financial_ratios.py:2810-2812`): usa el CAGR histórico del BPA (expansión de margen). El PEG usa el P/E reportado, no el normalizado (`main.py:1365` frente a `:1867`). Forward de Finnhub, base desconocida | No |
| F4 | P1 | **Confirmado** | Saturación por dos pruebas binarias redundantes (`financial_ratios.py:3290-3335`, `thresholds.toml:171-175`): toda rentable con F ≥ 7 llega a 20. 3/31 de la vigilancia con 20/20 y acumulaciones fallidas (AAPL, KO, NFLX) | Sí; la métrica de caja de contenido no (va contra el modelo general; Q1 la cubre) |
| F5 | P2 | **Confirmado** | P/E normalizado sobre acciones diluidas medias (4,268B); la capitalización usa las actuales (4,164B) | Sí |

## 2. Por qué «pasará con muchas más»: cinco familias de causa

Ninguna causa es de NU o de NFLX. Todas son de una de estas cinco familias, y cada una tiene ya víctimas fuera de la muestra.

| Familia | Hallazgos | A quién afecta |
|---|---|---|
| **A. Cables sueltos**: algo se calcula bien pero no llega a donde se usa | Alerta de caída muerta (T3); dos etapas no propagadas al implícito (N1); cota del crecimiento declarada y no aplicada (T4); persistencia ignora «No aplica» (T7); media de ROTE sin la regla de F9·R7 (N5); ayuda de «precio» en la fila equivocada (T7); riesgo de crédito fuera de la cobertura (T3) | Todas las empresas (alerta, ayuda), todos los FINANCIAL con libros > 20 %, todos los bancos |
| **B. Dos definiciones de la misma cifra** | TTM de Yahoo frente a FY de EDGAR (N2); acciones diluidas frente a actuales (F5); ROE sobre patrimonio final (N5) | Todo emisor con `reconciliation` > 2 % en el último FY y TTM de Yahoo (bancos IFRS y ADR sobre todo); ROE de todas |
| **C. Referencias sin prueba de representatividad** | Pares sin región (T1); referencia de ROE/margen < 2 % tras excluir a la empresa (T1); P/B relativo sin ajustar por ROE (T2) | 13 industrias EE. UU., 16 Europa, 6 Japón, 14 emergentes y 6 globales ya están < 2 % **antes** de excluir; más tras excluir a empresas dominantes |
| **D. Lecturas que ignoran su propia incertidumbre** | DCF que cambia de signo con ±1 pp (F1); «barata» con tasa base 28 % (F2); tope de credibilidad con crecimiento histórico (F3); convergencia con insumos compartidos (T2); beta bottom-up sin contraste (T5); limitador que solo mira el nivel final (T5) | Toda empresa cerca de un borde de banda; compresión del forward con crecimiento implícito > 25 %: 4/31 (NFLX, NVDA, JNJ, TSM) |
| **E. Prosa y plantilla no condicionadas** | «Propio de la empresa» con un solo ETF (T6); De Bondt sin evidencia (T6); títulos y metodología escritos a mano en `pdf_v2` (T7); nota de base anómala sin serie (N5) | Todos los emisores no EE. UU.; toda caída > 40 % con calidad sólida; todos los arquetipos sin DCF |

Por qué el guardián de F9·R3 (`tests/coherence.py`) no lo vio: solo compara cifras de `display` con `key`; no lee la
prosa, ni los textos a mano de `pdf_v2`, ni el uso de métricas «No aplica» en otros módulos.

## 3. Plan propuesto (F11)

Mismo método que F8–F10: cada hallazgo se convierte primero en **regla de cordura** en `lib/model_invariants.py`, se
mide sobre el universo (`tools/universe_scan.py`, 543 empresas) **antes** de corregir, y se corrige en origen con
regla general. Golden y matriz de transiciones del veredicto como en cada fase.

**Reglas nuevas (medir antes de tocar nada):**
1. `regla_viva`: toda regla de alerta lee campos que alguien escribe (estático, sobre `alert_interpretations.py`).
2. `una_definicion_ttm_fy`: si `reconciliation` del último FY > 2 %, el TTM de ese campo no puede venir de otra fuente.
3. `implicito_mismo_modelo`: con `two_stage.applied`, implícito y sensibilidad usan dos etapas.
4. `cota_aplicada`: un crecimiento puntuado nunca supera su propia `bound`.
5. `referencia_representativa`: |ROE| o |margen| de la referencia ≥ 2 % y pares de una sola región.
6. `voto_estable`: ningún método puntúa una dirección que cambia con ±1 pp de Ke/WACC.
7. `convergencia_independiente`: «alta» exige métodos sin insumo compartido.
8. `metodo_citado_aplicable`: el PDF no cita ni titula un método que el arquetipo excluye; ninguna métrica «No aplica» se usa como ancla.

**Correcciones por orden** (P0 reales primero; dependencias del registro):
1. Familia A completa (cables sueltos: bajo riesgo, alto alcance).
2. N2 (una definición por campo, TTM incluido).
3. T1 (pares por región + prueba de representatividad) → T2 (insumos declarados; P/B relativo ajustado por ROE en FINANCIAL).
4. F1 + F2 juntos (voto estable al WACC; «barata» exige tasa base ≥ 50 %) y T5 (limitador por voto, contraste de la beta).
5. F3, T4-NFLX, N5, F5, T6, resto de T7.
6. Al modelo general (no a F11): N4 → S1, F4 → Q1, F3 de fondo → V1, N3 (Ke en moneda local, con fuente gratuita).

**Descartado o corregido del diagnóstico:** pares de LatAm (no hay en el universo); dirección del sesgo de T1 en NU; P/E
de Entretenimiento inflado; «30 % vs 42 %» como cifra duplicada; normalización de NFLX excesiva; caja de contenido como
métrica sectorial (va contra el modelo general); piso de beta por volatilidad realizada.
