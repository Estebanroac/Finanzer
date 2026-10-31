# Beneficio sin nombre por encima del techo de N1b (29-oct-2026)

Escaneo de comprobación de `fiabilidad/f10-margen-op` (030b30ad).

**Contexto:**

- **Regla de N1/N1b:** solo se recorta lo nombrable: ganancias de inversiones de EDGAR, participadas netas y beneficio
  fiscal frente al tipo normalizado. El resto queda en la cifra y se declara en `earnings_normalization.unexplained`.
- **El techo** es el de `after_tax`: `explained` + `tolerance`.
- **`margen_neto_techo` (rama `fiabilidad/f10-margen-techo-n1b`):** lee ese techo y lo declarado, y marca solo lo
  que no está ni nombrado ni declarado. Sobre la salida de 030b30ad pasa de 22 a 0; sobre la de la puerta da lo mismo
  que antes.

## Las cuatro grandes: causa probable

El TTM es el del análisis. Las etiquetas de EDGAR van en los mismos 4 trimestres; donde el emisor no las presenta por
trimestre, el ejercicio.

| Empresa | Sin nombre (antes de imp. / después) | Causa probable | Evidencia en EDGAR |
|---|---|---|---|
| **F** | 0 / 1.088 M$ | **El beneficio fiscal de unas pérdidas, no la financiera cautiva.** Las piezas dan pérdida (operativo −7,0 B$ + participadas −5,6 B$ = −12,7 B$), y el techo de N1b solo aplica el tipo a un resultado positivo. Con pérdidas, el escudo fiscal sale como «sin nombre». Ford Credit consolida dentro del operativo | `IncomeTaxExpenseBenefit` TTM −4.736 M$ (un beneficio fiscal); `IncomeLossFromEquityMethodInvestments` −5.600 M$ |
| **NOC** | 395 / 191 M$ | **Ingreso de pensiones no operativo** (el crédito FAS: el coste neto de pensiones es negativo) | `DefinedBenefitPlanNetPeriodicBenefitCost` TTM −451 M$ |
| **SO** | 189 / 60 M$ | **AFUDC de capital propio** (utility); en parte se compensa con otros no operativos | `PublicUtilitiesAllowanceForFundsUsedDuringConstructionCapitalizedCostOfEquity` FY2025 340 M$ |
| **FE** | 116 / 10 M$ | **AFUDC de capital propio** | la misma etiqueta, FY2025 108 M$ |

Las otras 18 con exceso declarado no están clasificadas una a una. Las mayores: ECHO 10.788 M$ (según E2a, un deterioro
sin etiqueta dentro del operativo), SKYD 4.659 M$ (estados de la antecesora), KKR 2.847 M$ (gestora: ingresos de
inversión de sus fondos) y RIO 1.558 M$ (20-F).

## ¿Nombrarlos post-v4?

- **Pensiones (NOC) y AFUDC (utilities): sí, nombrarlos sin recortarlos.**
  - Son recurrentes y tienen etiqueta estándar: `DefinedBenefitPlanNetPeriodicBenefitCost`, su parte sin el coste de
    servicio y `PublicUtilitiesAllowanceForFundsUsedDuringConstruction…CostOfEquity`.
  - Nombrados, saldrían del «sin nombre» con su partida y se diría qué parte del beneficio no es operativa, sin cambiar
    la cifra que puntúa.
  - En las utilities, el AFUDC de capital es parte del retorno regulado: no se debe recortar.
- **El escudo fiscal de las pérdidas (F): arreglarlo en el techo, no nombrarlo.**
  - Es una asimetría de N1b: con un resultado antes de impuestos negativo, el techo debería llevar también (1 − t), o
    el beneficio fiscal frente al tipo normalizado, que N1b ya nombra.
  - Hoy cualquier empresa con pérdidas y beneficio fiscal sale con «sin nombre».
  - Conviene medir cuántas antes de decidirlo.
