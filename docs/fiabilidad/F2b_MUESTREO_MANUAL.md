# Muestreo manual de la fase 2b: 5 tickers frente al informe anual publicado

Para el chat de revisión (PLAN §4). Cifras del pipeline (replay de los fixtures del panel, en la moneda de los estados, con la conversión del motor deshecha) frente al informe anual (XBRL de SEC EDGAR, que es el mismo documento). Importes en millones; BPA en la moneda por acción ordinaria. Cada fila trae el concepto y el filing para abrir el documento y comprobarlo a mano. Estado y causa: los de `tests/edgar_verify.py` (tolerancias del PLAN §3, sin cambios).

## AAPL: Apple Inc. (EE. UU., 10-K, tecnología)

| Cifra | Ejercicio | Pipeline | Informe anual | Dif. | Estado | Concepto | Filing |
|---|---|---|---|---|---|---|---|
| Ingresos | 2025 | 416,161 | 416,161 | +0.0% | ok | `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Resultado operativo | 2025 | 133,050 | 133,050 | +0.0% | ok | `us-gaap:OperatingIncomeLoss` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Beneficio neto | 2025 | 112,010 | 112,010 | +0.0% | ok | `us-gaap:NetIncomeLoss` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| BPA diluido | 2025 | 7.46 | 7.46 | +0.0% | ok | `us-gaap:EarningsPerShareDiluted` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Flujo de operaciones | 2025 | 111,482 | 111,482 | +0.0% | ok | `us-gaap:NetCashProvidedByUsedInOperatingActivities` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Capex | 2025 | 12,715 | 12,715 | +0.0% | ok | `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Activo total | 2025 | 359,241 | 359,241 | +0.0% | ok | `us-gaap:Assets` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Pasivo total | 2025 | 285,508 | 285,508 | +0.0% | ok | `us-gaap:Liabilities` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Patrimonio | 2025 | 73,733 | 73,733 | +0.0% | ok | `us-gaap:StockholdersEquity` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Utilidades retenidas | 2025 | -14,264 | -14,264 | +0.0% | ok | `us-gaap:RetainedEarningsAccumulatedDeficit` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |
| Acciones en circulación | 2025 | 14,773 | 14,773 | +0.0% | ok | `us-gaap:CommonStockSharesOutstanding` | [10-K 0000320193-25-000079](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/) |

Moneda de los estados: USD.

## JPM: JPMORGAN CHASE & CO (banco de EE. UU., 10-K, preferentes)

| Cifra | Ejercicio | Pipeline | Informe anual | Dif. | Estado | Concepto | Filing |
|---|---|---|---|---|---|---|---|
| Ingresos | 2025 | 181,847 | 182,447 | -0.3% | ok | `us-gaap:Revenues` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Resultado operativo | 2025 | — | — |  | ninguno | `` |  |
| Beneficio neto | 2025 | 57,048 | 57,048 | +0.0% | ok | `us-gaap:NetIncomeLoss` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| BPA diluido | 2025 | 20.02 | 20.02 | +0.0% | ok | `us-gaap:EarningsPerShareDiluted` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Flujo de operaciones | 2025 | -147,782 | -147,782 | +0.0% | ok | `us-gaap:NetCashProvidedByUsedInOperatingActivities` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Capex | 2025 | — | — |  | ninguno | `` |  |
| Activo total | 2025 | 4,424,900 | 4,424,900 | +0.0% | ok | `us-gaap:Assets` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Pasivo total | 2025 | 4,062,462 | 4,062,462 | +0.0% | ok | `us-gaap:Liabilities` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Patrimonio | 2025 | 362,438 | 362,438 | +0.0% | ok | `us-gaap:StockholdersEquity` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Utilidades retenidas | 2025 | 416,055 | 416,055 | +0.0% | ok | `us-gaap:RetainedEarningsAccumulatedDeficit` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |
| Acciones en circulación | 2025 | 2,696 | 2,696 | +0.0% | ok | `us-gaap:CommonStockSharesOutstanding` | [10-K 0001628280-26-008131](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/) |

Moneda de los estados: USD.

## DUK: Duke Energy CORP (utility, 10-K, arrendamientos)

| Cifra | Ejercicio | Pipeline | Informe anual | Dif. | Estado | Concepto | Filing |
|---|---|---|---|---|---|---|---|
| Ingresos | 2025 | 32,237 | 31,741 | +1.6% | fuera (definición) | `us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Resultado operativo | 2025 | 8,577 | 8,626 | -0.6% | ok | `us-gaap:OperatingIncomeLoss` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Beneficio neto | 2025 | 4,968 | 4,968 | +0.0% | ok | `us-gaap:NetIncomeLoss` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| BPA diluido | 2025 | 6.31 | 6.31 | +0.0% | ok | `us-gaap:EarningsPerShareDiluted` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Flujo de operaciones | 2025 | 12,330 | 12,330 | +0.0% | ok | `us-gaap:NetCashProvidedByUsedInOperatingActivities` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Capex | 2025 | 14,024 | 14,024 | +0.0% | ok | `us-gaap:PaymentsToAcquirePropertyPlantAndEquipment` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Activo total | 2025 | 195,736 | 195,736 | +0.0% | ok | `us-gaap:Assets` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Pasivo total | 2025 | 142,717 | — |  | edgar_falta (EDGAR falta) | `` |  |
| Patrimonio | 2025 | 51,842 | 51,842 | +0.0% | ok | `us-gaap:StockholdersEquity` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Utilidades retenidas | 2025 | 5,056 | 5,056 | +0.0% | ok | `us-gaap:RetainedEarningsAccumulatedDeficit` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |
| Acciones en circulación | 2025 | 778 | 778 | -0.0% | ok | `us-gaap:CommonStockSharesOutstanding` | [10-K 0001326160-26-000014](https://www.sec.gov/Archives/edgar/data/1326160/000132616026000014/) |

Moneda de los estados: USD.

## TSM: Taiwan Semiconductor Manufacturing Company Limited (ADR (5 ordinarias), 20-F en TWD)

| Cifra | Ejercicio | Pipeline | Informe anual | Dif. | Estado | Concepto | Filing |
|---|---|---|---|---|---|---|---|
| Ingresos | 2025 | 3,809,054 | 3,809,054 | +0.0% | ok | `ifrs-full:RevenueFromContractsWithCustomers` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Resultado operativo | 2025 | 1,936,096 | 1,936,092 | +0.0% | ok | `ifrs-full:ProfitLossFromOperatingActivities` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Beneficio neto | 2025 | 1,697,604 | 1,697,604 | +0.0% | ok | `ifrs-full:ProfitLossAttributableToOwnersOfParent` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| BPA diluido | 2025 | 331.25 | 327.35 | +1.2% | ok | `ifrs-full:DilutedEarningsLossPerShare` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Flujo de operaciones | 2025 | 2,274,976 | 2,274,976 | +0.0% | ok | `ifrs-full:CashFlowsFromUsedInOperatingActivities` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Capex | 2025 | 1,282,597 | 1,272,410 | +0.8% | ok | `ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Activo total | 2025 | 7,932,842 | 7,932,842 | +0.0% | ok | `ifrs-full:Assets` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Pasivo total | 2025 | 2,536,623 | 2,536,623 | +0.0% | ok | `ifrs-full:Liabilities` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Patrimonio | 2025 | 5,355,039 | 5,355,039 | +0.0% | ok | `ifrs-full:EquityAttributableToOwnersOfParent` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Utilidades retenidas | 2025 | 4,640,513 | 5,038,944 | -7.9% | fuera (definición) | `ifrs-full:RetainedEarnings` | [20-F 0001628280-26-025362](https://www.sec.gov/Archives/edgar/data/1046179/000162828026025362/) |
| Acciones en circulación | 2025 | 5,187 | 5,187 | +0.0% | ok | `dei:EntityCommonStockSharesOutstanding` |  |

Moneda de los estados: TWD.

## UL: UNILEVER PLC (ADR (1), 20-F en EUR, cambio de perímetro)

| Cifra | Ejercicio | Pipeline | Informe anual | Dif. | Estado | Concepto | Filing |
|---|---|---|---|---|---|---|---|
| Ingresos | 2025 | 50,503 | 50,503 | +0.0% | ok | `ifrs-full:Revenue` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Resultado operativo | 2025 | 10,127 | 9,037 | +12.1% | fuera (fuente errónea) | `ifrs-full:ProfitLossFromOperatingActivities` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Beneficio neto | 2025 | 9,469 | 9,469 | +0.0% | ok | `ifrs-full:ProfitLossAttributableToOwnersOfParent` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| BPA diluido | 2025 | 4.32 | 4.32 | +0.0% | ok | `ifrs-full:DilutedEarningsLossPerShare` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Flujo de operaciones | 2025 | 8,350 | 8,350 | +0.0% | ok | `ifrs-full:CashFlowsFromUsedInOperatingActivities` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Capex | 2025 | 1,591 | 1,417 | +12.3% | fuera (definición) | `ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Activo total | 2025 | 70,471 | 70,471 | +0.0% | ok | `ifrs-full:Assets` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Pasivo total | 2025 | 52,884 | 52,884 | +0.0% | ok | `ifrs-full:Liabilities` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Patrimonio | 2025 | 15,530 | 15,530 | -0.0% | ok | `ifrs-full:EquityAttributableToOwnersOfParent` | [20-F 0000217410-26-000007](https://www.sec.gov/Archives/edgar/data/217410/000021741026000007/) |
| Utilidades retenidas | 2025 | 44,229 | — |  | edgar_falta (EDGAR falta) | `` |  |
| Acciones en circulación | 2025 | 2,179 | 2,180 | -0.0% | ok | `ifrs-full:NumberOfSharesOutstanding` |  |

Moneda de los estados: EUR.

