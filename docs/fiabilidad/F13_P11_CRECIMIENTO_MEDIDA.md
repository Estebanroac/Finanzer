# F13 · Paso 11: el crecimiento del DCF, medido antes de aplicar (5-nov-2026)

Plan: E7 (crecimiento con ventas, BPA y tasa base) si, tras los pasos 1–9, el sesgo hacia «caro» persiste en las 110
congeladas.

## ¿Persiste el sesgo?

Sí. En el paso 10, 62 de las 106 con veredicto de precio son «exigente» o «muy exigente» (al empezar F13: 64 de 108).
La mediana del DCF directo es −36 %.

## ¿Lo explica la fuente del crecimiento?

No. Se recalcula el DCF de las 76 con DCF (`scenario_inputs`, reproducido exacto en las 76) con cuatro crecimientos:

| Opción | Crecimiento de la fase 1 | Mediana del DCF | ≤ −60 % | ≥ +60 % |
|---|---|---|---|---|
| A · hoy | CAGR de ingresos a 3 años (con sus reglas: por acción, perímetro, mezcla con el interanual) | −36 % | 20 | 9 |
| B | media de ventas y BPA a 3 años | −29 % | 18 | 13 |
| C | mitad (ventas + BPA) / 2, mitad tasa base | −36 % | 17 | 9 |
| D | mitad ventas, mitad tasa base | −40 % | 19 | 8 |

Tasa base: mediana del CAGR de ventas a 5 años de las comparables de su tamaño e industria (Mauboussin y Callahan,
`config/base_rates.toml`, la que ya usa el DCF inverso).

Ninguna opción mueve la mediana más de 7 puntos. El sesgo viene del nivel, no del crecimiento:
- con un WACC de ~8,5 % y un terminal del 2,5 %, el DCF vale unas 17 veces el FCF − SBC;
- las grandes empresas cotizan a 25–40 veces.

Eso no es un error del modelo, es lo que espera el mercado, y el DCF inverso ya lo dice: cuánto crecimiento exige el
precio y qué parte de las comparables lo logró.

## Lo que sí está mal, empresa por empresa

1. **El BPA no sirve como impulsor.** Con bases deprimidas se dispara: NVDA crece un 102 % al año, DIS un 59 %, LLY un
   52 % y CRM un 35 %. Con la opción B, NVDA llega a +188 %, CRM a +189 % y DIS a +144 %. Se descarta.
2. **Crecimientos que casi nadie sostiene.** El DCF mantiene 5 años crecimientos que, a ese tamaño, mantuvo menos del
   10 % de las comparables:

   | Empresa | Crecimiento | Comparables que lo sostuvieron |
   |---|---|---|
   | MSFT | 16 % | 5 % |
   | META | 20 % | 2 % |
   | LLY | 30 % | 1 % |
   | NVDA | 30 % | 0 % |
   | AMZN | 12 % | 7 % |

   NVO, en el panel, usa un 13,4 %: la media del interanual (6,4 %, se frena) y del CAGR de 3 años (20,4 %). Así llega
   al +83 % y a «atractivo».
3. **Ventas y BPA divergen más de 10 pp** en 22 de los 76 DCF:
   - márgenes en expansión o traslado de costes: LIN, ECL, WMT, JNJ;
   - márgenes en compresión: UNH, GM, ABBV, TXN.

   El crecimiento de las ventas no representa el del flujo, y hoy nada lo dice.

## Opciones

| Opción | Qué hace | Efecto medido |
|---|---|---|
| **(a)** Convergencia a la tasa base | Fase 1 = media de su crecimiento y la mediana a 5 años de sus comparables; equivale a converger en línea recta en 5 años de su crecimiento al de las comparables (Mauboussin: el crecimiento revierte a la media, en los dos sentidos). No en cíclicas, que ya usan el ciclo medio | Simétrica: la mediana pasa de −36 % a −40 %. Bajan las de crecimiento alto: NVO de +83 % a +46 %, MSFT de −39 % a −53 %, NVDA de −5 % a −51 %, TSM de −15 % a −47 %, META de −12 % a −34 %. Suben las que encogen: KHC de +63 % a +109 %, UL de −46 % a −35 % |
| **(b)** Fiabilidad del DCF | Sin tocar el crecimiento, el DCF pierde un escalón de fiabilidad si ventas y BPA divergen más de 10 pp, o si su crecimiento lo sostuvo menos del 10 % de las comparables | 25 de los 76 DCF; no cambia ningún valor, solo su peso |
| **(c) (recomendada)** (a) + la divergencia de (b) | El crecimiento converge a la tasa base y la divergencia ventas/BPA baja la fiabilidad (la tasa base ya está dentro del valor) | La de (a) en los valores; 22 DCF con un escalón menos |
| (d) Tres impulsores completos | Ingresos, margen y reinversión por separado (E7 de la auditoría) | Varias horas; es de la Fase B. Con lo medido, no cambia el sesgo |

Evidencias: `archivo-historico/evidencias-de-pruebas/f13_crecimiento_2026-11-05` (script y filas por empresa).
