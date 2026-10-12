"""
Financial Data Fetcher Module
=============================
Módulo para obtener datos financieros de empresas desde múltiples fuentes.
Soporta Yahoo Finance (gratuito) y Financial Modeling Prep (freemium).

Autor: Esteban
Versión: 2.10 - Rate limiting con retry y backoff exponencial
"""

import os
import re
import time
import random
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
import hashlib

# =========================
# CONSTANTES DE RETRY
# =========================
MAX_RETRIES = 4       # Reintentos para rate limiting
BASE_DELAY = 3        # segundos base entre reintentos
MAX_DELAY = 45        # segundos máximo de espera

# Configurar logging específico para este módulo
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler para consola si no hay handlers configurados
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# yf_adapter (curl_cffi direct API) is the primary fetcher
try:
    from yf_adapter import get_ticker_info
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# yfinance package is optional (used as fallback in yf_adapter)
try:
    import yfinance as yf
    try:
        from yfinance.exceptions import YFRateLimitError
        YF_RATE_LIMIT_AVAILABLE = True
    except ImportError:
        YF_RATE_LIMIT_AVAILABLE = False
        YFRateLimitError = Exception
except ImportError:
    YF_RATE_LIMIT_AVAILABLE = False
    YFRateLimitError = Exception


# =========================
# CONSTANTES DE CONFIGURACIÓN
# =========================

# Timeouts para operaciones de red (en segundos)
API_TIMEOUT_SECONDS = 15          # Timeout para llamadas API individuales
PARALLEL_TASK_TIMEOUT = 30        # Timeout para tareas paralelas

# Configuración del ThreadPoolExecutor
THREAD_POOL_WORKERS = 4           # Número de workers paralelos


# =========================
# EXCEPCIONES PERSONALIZADAS
# =========================

class DataFetchError(Exception):
    """Error base para problemas de obtención de datos."""
    pass

class APITimeoutError(DataFetchError):
    """Timeout al llamar a una API externa."""
    pass

class InvalidSymbolError(DataFetchError):
    """Símbolo de ticker inválido o no encontrado."""
    pass

class RateLimitError(DataFetchError):
    """Se excedió el límite de llamadas a la API."""
    pass

class DataValidationError(DataFetchError):
    """Los datos obtenidos no pasan validación."""
    pass


# =========================
# SISTEMA DE CACHÉ SIMPLE
# =========================

class SimpleCache:
    """
    Caché en memoria con TTL (Time To Live) y límite de entradas.
    Implementa LRU (Least Recently Used) eviction para prevenir memory leaks.
    """
    
    def __init__(self, default_ttl_minutes: int = 15, max_entries: int = 500):
        self._cache: Dict[str, Dict] = {}
        self._default_ttl = timedelta(minutes=default_ttl_minutes)
        self._max_entries = max_entries
        self._access_order: List[str] = []  # Para LRU tracking
    
    def _make_key(self, prefix: str, *args) -> str:
        """Genera una clave única para el caché."""
        key_data = f"{prefix}:{':'.join(str(a) for a in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _evict_expired(self):
        """Elimina entradas expiradas."""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry["expires"]
        ]
        for key in expired_keys:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
    
    def _evict_lru(self, count: int = 1):
        """Elimina las entradas menos recientemente usadas."""
        for _ in range(min(count, len(self._access_order))):
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene un valor del caché si existe y no ha expirado."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if datetime.now() > entry["expires"]:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None
        
        # Actualizar orden de acceso (mover al final = más reciente)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl_minutes: Optional[int] = None):
        """Guarda un valor en el caché."""
        # Limpiar expirados primero
        self._evict_expired()
        
        # Si alcanzamos el límite, eliminar los más viejos
        while len(self._cache) >= self._max_entries:
            self._evict_lru(count=max(1, self._max_entries // 10))  # Eliminar 10%
        
        ttl = timedelta(minutes=ttl_minutes) if ttl_minutes else self._default_ttl
        self._cache[key] = {
            "value": value,
            "expires": datetime.now() + ttl,
            "created": datetime.now()
        }
        
        # Registrar en orden de acceso
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def clear(self):
        """Limpia todo el caché."""
        self._cache.clear()
        self._access_order.clear()
    
    def stats(self) -> Dict:
        """Retorna estadísticas del caché."""
        self._evict_expired()  # Limpiar antes de reportar
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "utilization": f"{len(self._cache) / self._max_entries * 100:.1f}%"
        }


# Instancia global del caché
_data_cache = SimpleCache(default_ttl_minutes=30)


@dataclass
class CompanyProfile:
    """Perfil básico de una empresa."""
    symbol: str
    name: str
    sector: str
    industry: str
    country: str
    currency: str
    exchange: str
    market_cap: Optional[float]
    description: str


@dataclass 
class FinancialStatements:
    """Estados financieros consolidados."""
    # Income Statement
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None  # EBIT
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    interest_expense: Optional[float] = None
    depreciation: Optional[float] = None
    
    # Balance Sheet
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    cash: Optional[float] = None
    inventories: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_debt: Optional[float] = None
    long_term_debt: Optional[float] = None  # NUEVO: Para F-Score
    total_equity: Optional[float] = None
    retained_earnings: Optional[float] = None  # NUEVO: Para Z-Score
    
    # Cash Flow Statement
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    free_cash_flow: Optional[float] = None
    dividends_paid: Optional[float] = None
    
    # Per Share Data
    shares_outstanding: Optional[float] = None
    eps: Optional[float] = None
    forward_eps: Optional[float] = None
    dividend_per_share: Optional[float] = None
    book_value_per_share: Optional[float] = None
    
    # Market Data
    price: Optional[float] = None
    price_52w_high: Optional[float] = None
    price_52w_low: Optional[float] = None
    beta: Optional[float] = None
    
    # Growth & Historical
    revenue_growth_yoy: Optional[float] = None
    earnings_growth_rate: Optional[float] = None
    
    # Metadata
    fiscal_year_end: Optional[str] = None
    last_updated: Optional[str] = None


class YahooFinanceFetcher:
    """Fetcher usando Yahoo Finance (yfinance)."""
    
    def __init__(self):
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance no está instalado. Ejecuta: pip install yfinance")
    
    def get_company_profile(self, symbol: str) -> Optional[CompanyProfile]:
        """Obtiene el perfil de la empresa (con caché y retry para rate limiting)."""
        cache_key = _data_cache._make_key("profile", symbol.upper())
        
        # Verificar caché
        cached = _data_cache.get(cache_key)
        if cached:
            return cached
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                info = get_ticker_info(symbol)

                # Validar que obtuvimos datos válidos
                if not info or info.get("regularMarketPrice") is None:
                    logger.warning(f"Símbolo '{symbol}' no encontrado o sin datos de mercado")
                    return None
                
                profile = CompanyProfile(
                    symbol=symbol.upper(),
                    name=info.get("longName", info.get("shortName", symbol)),
                    sector=info.get("sector", "Unknown"),
                    industry=info.get("industry", "Unknown"),
                    country=info.get("country", "Unknown"),
                    currency=info.get("currency", "USD"),
                    exchange=info.get("exchange", "Unknown"),
                    market_cap=info.get("marketCap"),
                    description=info.get("longBusinessSummary", "")[:500],
                )
                
                # Guardar en caché (30 min para perfiles, cambian poco)
                _data_cache.set(cache_key, profile, ttl_minutes=30)
                logger.debug(f"Perfil de {symbol} obtenido correctamente")
                return profile
            
            except KeyError as e:
                logger.warning(f"Campo faltante en datos de {symbol}: {e}")
                return None
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Error de conexión obteniendo perfil de {symbol}: {e}")
                raise APITimeoutError(f"Timeout obteniendo perfil de {symbol}") from e
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                error_type = type(e).__name__
                
                # Detectar rate limiting (múltiples formas)
                is_rate_limit = (
                    'YFRateLimitError' in error_type or
                    'ratelimit' in error_type.lower() or
                    'rate' in error_str and 'limit' in error_str or
                    'too many requests' in error_str or
                    '429' in error_str
                )
                
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"⏳ Rate limited ({error_type}). Reintentando perfil {symbol} en {delay:.1f}s (intento {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue  # Importante: continuar al siguiente intento
                else:
                    logger.error(f"Error obteniendo perfil de {symbol}: {error_type}: {e}")
                    if attempt == MAX_RETRIES - 1:
                        return None
        
        return None
    
    def get_financial_data(self, symbol: str) -> Optional[FinancialStatements]:
        """Obtiene todos los datos financieros de una empresa (con caché y retry para rate limiting)."""
        cache_key = _data_cache._make_key("financials", symbol.upper())
        
        # Verificar caché
        cached = _data_cache.get(cache_key)
        if cached:
            return cached
        
        # Helper function
        def get_latest(df, key):
            try:
                if df is not None and not df.empty and key in df.index:
                    val = df.loc[key].iloc[0]
                    return float(val) if val is not None and str(val) != 'nan' else None
            except (KeyError, IndexError, TypeError, ValueError):
                pass
            return None
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # get_ticker_info already fetches fast_info + 3 statements IN PARALLEL
                # DO NOT re-fetch statements — use the data from info directly
                info = get_ticker_info(symbol)

                # All financial data comes pre-extracted from yf_adapter
                revenue = info.get("totalRevenue")
                gross_profit = info.get("grossProfits")
                operating_income = info.get("operatingIncome")
                net_income = info.get("netIncome")
                ebitda_val = info.get("ebitda")
                interest_expense = info.get("interestExpense")

                total_assets = info.get("totalAssets")
                current_assets = info.get("totalCurrentAssets")
                cash = info.get("cash")
                inventories = info.get("inventory")
                total_liabilities = info.get("totalLiab")
                current_liabilities = info.get("totalCurrentLiabilities")
                total_debt = info.get("totalDebt")
                long_term_debt = info.get("longTermDebt")
                total_equity = info.get("totalStockholderEquity")
                retained_earnings = info.get("retainedEarnings")

                operating_cf = info.get("operatingCashflow")
                capex_raw = info.get("capitalExpenditures")
                capex = abs(capex_raw) if capex_raw is not None else None
                fcf = info.get("freeCashflow")
                dividends = info.get("dividendsPaid")
                depreciation = info.get("depreciation")

                shares = info.get("sharesOutstanding")
                price = info.get("currentPrice") or info.get("regularMarketPrice")

                # Calcular FCF si no está disponible
                if fcf is None and operating_cf is not None and capex is not None:
                    fcf = operating_cf - capex

                # Growth rates (already calculated in adapter)
                revenue_growth = info.get("revenueGrowth")
                
                result = FinancialStatements(
                    # Income Statement
                    revenue=revenue,
                    gross_profit=gross_profit,
                    operating_income=operating_income,
                    net_income=net_income,
                    ebitda=ebitda_val,
                    interest_expense=abs(interest_expense) if interest_expense else None,
                    depreciation=depreciation,
                    
                    # Balance Sheet
                    total_assets=total_assets,
                    current_assets=current_assets,
                    cash=cash,
                    inventories=inventories,
                    total_liabilities=total_liabilities,
                    current_liabilities=current_liabilities,
                    total_debt=total_debt,
                    long_term_debt=long_term_debt,
                    total_equity=total_equity,
                    retained_earnings=retained_earnings,
                    
                    # Cash Flow
                    operating_cash_flow=operating_cf,
                    capex=capex,
                    free_cash_flow=fcf,
                    dividends_paid=abs(dividends) if dividends else None,
                    
                    # Per Share & Market
                    shares_outstanding=shares,
                    eps=info.get("trailingEps"),
                    forward_eps=info.get("forwardEps"),
                    dividend_per_share=info.get("dividendRate"),
                    book_value_per_share=info.get("bookValue"),
                    price=price,
                    price_52w_high=info.get("fiftyTwoWeekHigh"),
                    price_52w_low=info.get("fiftyTwoWeekLow"),
                    beta=info.get("beta"),
                    
                    # Growth
                    revenue_growth_yoy=revenue_growth,
                    earnings_growth_rate=info.get("earningsGrowth"),
                    
                    # Metadata
                    fiscal_year_end=info.get("lastFiscalYearEnd"),
                    last_updated=datetime.now().isoformat(),
                )
                
                # Guardar en caché (60 min para datos financieros - reduce rate limiting)
                _data_cache.set(cache_key, result, ttl_minutes=60)
                logger.debug(f"Datos financieros de {symbol} cacheados correctamente")
                return result
            
            except KeyError as e:
                logger.warning(f"Campo faltante en datos financieros de {symbol}: {e}")
                return None
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Error de conexión obteniendo datos financieros de {symbol}: {e}")
                raise APITimeoutError(f"Timeout obteniendo datos financieros de {symbol}") from e
            except ValueError as e:
                logger.warning(f"Error de conversión en datos de {symbol}: {e}")
                return None
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                error_type = type(e).__name__
                
                # Detectar rate limiting (múltiples formas)
                is_rate_limit = (
                    'YFRateLimitError' in error_type or
                    'ratelimit' in error_type.lower() or
                    'rate' in error_str and 'limit' in error_str or
                    'too many requests' in error_str or
                    '429' in error_str
                )
                
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"⏳ Rate limited ({error_type}). Reintentando {symbol} en {delay:.1f}s (intento {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue  # Importante: continuar al siguiente intento
                else:
                    logger.error(f"Error obteniendo datos financieros de {symbol}: {error_type}: {e}")
                    if attempt == MAX_RETRIES - 1:
                        return None
        
        return None


class FinancialDataService:
    """Servicio unificado para obtener datos financieros."""
    
    def __init__(self, fmp_api_key: Optional[str] = None):
        """
        Args:
            fmp_api_key: API key de Financial Modeling Prep (opcional)
        """
        self.fmp_api_key = fmp_api_key or os.environ.get("FMP_API_KEY")
        
        # Intentar inicializar Yahoo Finance
        try:
            self.yahoo = YahooFinanceFetcher()
            self.yahoo_available = True
        except ImportError:
            self.yahoo = None
            self.yahoo_available = False
    
    def get_complete_analysis_data(self, symbol: str, progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """
        Obtiene todos los datos necesarios para el análisis completo.
        
        VERSIÓN 2.9: Paralelizada con timeouts explícitos y logging mejorado
        
        Args:
            symbol: Símbolo del ticker (ej: AAPL, MSFT)
            progress_callback: Función opcional para reportar progreso (mensaje, porcentaje 0-100)
        
        Returns:
            Dict con profile, financials, historical, sector_averages, contextual, errors
        
        Raises:
            InvalidSymbolError: Si el símbolo es inválido
        """
        start_time = time.time()
        
        # ========================================
        # VALIDACIÓN DE ENTRADA
        # ========================================
        
        # Validar que symbol no esté vacío
        if not symbol or not isinstance(symbol, str):
            logger.error("Símbolo vacío o inválido proporcionado")
            raise InvalidSymbolError("El símbolo no puede estar vacío")
        
        # Limpiar y validar formato del símbolo
        symbol = symbol.strip().upper()
        
        # Validar longitud razonable (tickers son típicamente 1-5 caracteres, máx ~10 para algunos mercados)
        if len(symbol) > 15:
            logger.warning(f"Símbolo sospechosamente largo: {symbol[:20]}...")
            raise InvalidSymbolError(f"Símbolo demasiado largo: {len(symbol)} caracteres")
        
        # Validar caracteres permitidos (letras, números, puntos, guiones)
        if not re.match(r'^[A-Z0-9\.\-]+$', symbol):
            logger.warning(f"Símbolo con caracteres inválidos: {symbol}")
            raise InvalidSymbolError(f"Símbolo contiene caracteres inválidos: {symbol}")
        
        logger.info(f"Iniciando análisis completo para {symbol}")
        
        result = {
            "symbol": symbol,
            "profile": None,
            "financials": None,
            "historical": None,
            "sector_averages": None,
            "contextual": {},
            "errors": [],
            "_timing": {}  # Para debug de performance
        }
        
        if not self.yahoo_available:
            result["errors"].append("Yahoo Finance no disponible")
            logger.error("Yahoo Finance no está disponible")
            return result
        
        def report_progress(msg: str, pct: float):
            if progress_callback:
                try:
                    progress_callback(msg, pct)
                except Exception:
                    pass  # No interrumpir análisis por errores en callback
        
        report_progress("Iniciando análisis...", 5)
        
        # ========================================
        # FASE 1: Llamadas paralelas principales
        # ========================================
        
        profile = None
        financials = None
        historical = None
        
        # Definir tareas a ejecutar en paralelo
        # NOTE: historical and detailed removed from critical path
        # They trigger extra yfinance calls and aren't needed for main analysis
        tasks = {
            "profile": lambda: self.yahoo.get_company_profile(symbol),
            "financials": lambda: self.yahoo.get_financial_data(symbol),
        }
        
        results_parallel = {}
        
        # Ejecutar en paralelo con ThreadPoolExecutor
        logger.info(f"Iniciando fetch paralelo para {symbol} con {THREAD_POOL_WORKERS} workers")
        
        with ThreadPoolExecutor(max_workers=THREAD_POOL_WORKERS) as executor:
            future_to_task = {
                executor.submit(task_fn): task_name 
                for task_name, task_fn in tasks.items()
            }
            
            completed = 0
            total = len(future_to_task)
            
            try:
                for future in as_completed(future_to_task, timeout=PARALLEL_TASK_TIMEOUT * total):
                    task_name = future_to_task[future]
                    completed += 1
                    progress_pct = 10 + (completed / total * 50)  # 10% a 60%

                    try:
                        # Timeout explícito por tarea individual
                        results_parallel[task_name] = future.result(timeout=PARALLEL_TASK_TIMEOUT)
                        report_progress(f"Obteniendo {task_name}...", progress_pct)
                        logger.debug(f"✓ Tarea '{task_name}' completada para {symbol}")

                    except FuturesTimeoutError:
                        results_parallel[task_name] = None
                        error_msg = f"Timeout ({PARALLEL_TASK_TIMEOUT}s) en {task_name}"
                        result["errors"].append(error_msg)
                        logger.warning(f"⏱ {error_msg} para {symbol}")

                    except ConnectionError as e:
                        results_parallel[task_name] = None
                        error_msg = f"Error de conexión en {task_name}: {str(e)[:100]}"
                        result["errors"].append(error_msg)
                        logger.error(f"🔌 {error_msg} para {symbol}")

                    except ValueError as e:
                        results_parallel[task_name] = None
                        error_msg = f"Datos inválidos en {task_name}: {str(e)[:100]}"
                        result["errors"].append(error_msg)
                        logger.warning(f"⚠ {error_msg} para {symbol}")

                    except Exception as e:
                        results_parallel[task_name] = None
                        error_msg = f"Error inesperado en {task_name}: {type(e).__name__}: {str(e)[:100]}"
                        result["errors"].append(error_msg)
                        logger.error(f"❌ {error_msg} para {symbol}", exc_info=True)
            except FuturesTimeoutError:
                # The overall as_completed deadline elapsed while one or more
                # fetches were still hanging (slow/unreachable provider). This
                # raises from the iteration itself — outside the per-task handler
                # above — so without this guard it propagated to the API layer as
                # a 500. Mark any task that never completed as None and record the
                # timeout, so the analysis degrades to a clean "no data" (404).
                for pending_future, pending_name in future_to_task.items():
                    if pending_name not in results_parallel:
                        results_parallel[pending_name] = None
                        result["errors"].append(f"Timeout global esperando {pending_name}")
                        pending_future.cancel()
                logger.warning(f"⏱ Timeout global de fetch para {symbol}")
        
        parallel_time = time.time() - start_time
        result["_timing"]["parallel_fetch"] = parallel_time
        logger.info(f"Fetch paralelo completado para {symbol} en {parallel_time:.2f}s")
        
        # Extraer resultados
        profile = results_parallel.get("profile")
        financials = results_parallel.get("financials")
        historical = results_parallel.get("historical")
        
        report_progress("Procesando datos...", 65)
        
        # ========================================
        # FASE 2: Procesar resultados
        # ========================================
        
        # Perfil
        if profile:
            result["profile"] = profile
        else:
            result["errors"].append("No se pudo obtener el perfil")
        
        # Datos financieros
        if financials:
            result["financials"] = financials
            
            # ===== DATOS PARA ALTMAN Z-SCORE =====
            if financials.current_assets is not None and financials.current_liabilities is not None:
                result["contextual"]["working_capital"] = financials.current_assets - financials.current_liabilities
            
            result["contextual"]["total_assets"] = financials.total_assets
            result["contextual"]["retained_earnings"] = financials.retained_earnings
            result["contextual"]["ebit"] = financials.operating_income
            result["contextual"]["total_liabilities"] = financials.total_liabilities
            result["contextual"]["revenue"] = financials.revenue
            
            # Market Cap para Z-Score
            if financials.price and financials.shares_outstanding:
                result["contextual"]["market_cap"] = financials.price * financials.shares_outstanding
            
            # ===== DATOS PARA FINANCIAL HEALTH SCORE (Sector Financiero) =====
            result["contextual"]["total_equity"] = financials.total_equity
            result["contextual"]["book_value"] = financials.book_value_per_share
            
            # ===== DATOS PARA PIOTROSKI F-SCORE =====
            result["contextual"]["net_income"] = financials.net_income
            result["contextual"]["operating_cash_flow"] = financials.operating_cash_flow
            result["contextual"]["long_term_debt"] = financials.long_term_debt
            result["contextual"]["shares_outstanding"] = financials.shares_outstanding
            result["contextual"]["total_debt"] = financials.total_debt
            result["contextual"]["interest_expense"] = financials.interest_expense
            
        else:
            result["errors"].append("No se pudieron obtener datos financieros")
        
        report_progress("Calculando históricos...", 75)
        
        # Históricos para CAGR y FCF trend: movido a historical_metrics.py
        # (etapa 4). Nunca corría: la tarea "historical" ya no se lanza.
        if historical:
            result["historical"] = historical

        report_progress("Procesando F-Score...", 85)
        
        report_progress("Obteniendo datos del sector...", 90)

        # (Los promedios sectoriales estáticos que se inyectaban aquí eran
        # ficticios y nadie los consumía — ver nota en get_sector_averages.)

        # Timing final
        result["_timing"]["total"] = time.time() - start_time
        
        report_progress("Análisis completado", 100)
        
        return result
    
    def financials_to_dict(self, financials: FinancialStatements) -> Dict[str, Optional[float]]:
        """Convierte FinancialStatements a dict para calculate_all_ratios."""
        return {
            "revenue": financials.revenue,
            "gross_profit": financials.gross_profit,
            "operating_income": financials.operating_income,
            "net_income": financials.net_income,
            "total_assets": financials.total_assets,
            "current_assets": financials.current_assets,
            "cash": financials.cash,
            "inventories": financials.inventories,
            "current_liabilities": financials.current_liabilities,
            "total_debt": financials.total_debt,
            "long_term_debt": financials.long_term_debt,
            "total_equity": financials.total_equity,
            "retained_earnings": financials.retained_earnings,
            "total_liabilities": financials.total_liabilities,
            "operating_cash_flow": financials.operating_cash_flow,
            "capex": financials.capex,
            "shares_outstanding": financials.shares_outstanding,
            "price": financials.price,
            "interest_expense": financials.interest_expense,
            "depreciation": financials.depreciation,
            "amortization": 0,  # Incluido en depreciation generalmente
            "forward_eps": financials.forward_eps,
            "dividend_per_share": financials.dividend_per_share,
            "dividends_paid": financials.dividends_paid,  # Para payout_ratio
            "earnings_growth_rate": (financials.earnings_growth_rate or 0) * 100 if financials.earnings_growth_rate else None,
            "beta": financials.beta,
            "cogs": None,  # No siempre disponible en yfinance
        }


def test_fetcher(symbol: str = "AAPL"):
    """Función de prueba para verificar que el fetcher funciona."""
    print(f"\n{'='*60}")
    print(f"Testing Financial Data Fetcher v2.2 (Paralelo) for {symbol}")
    print(f"{'='*60}\n")
    
    service = FinancialDataService()
    
    # Test con timing
    print("⏱️  Iniciando fetch con paralelización...")
    start = time.time()
    
    def progress_cb(msg, pct):
        print(f"   [{pct:5.1f}%] {msg}")
    
    data = service.get_complete_analysis_data(symbol, progress_callback=progress_cb)
    
    total_time = time.time() - start
    
    print(f"\n✅ Completado en {total_time:.2f} segundos")
    
    if "_timing" in data:
        print(f"\n📊 Desglose de tiempos:")
        for key, val in data["_timing"].items():
            print(f"   {key}: {val:.2f}s")
    
    # Mostrar resultados
    profile = data.get("profile")
    financials = data.get("financials")
    
    if profile:
        print(f"\n1. Perfil: ✓ {profile.name} ({profile.sector})")
    else:
        print(f"\n1. Perfil: ✗ Error")
    
    if financials:
        print(f"2. Financials: ✓ Revenue ${financials.revenue/1e9:.1f}B" if financials.revenue else "2. Financials: ✓ (datos parciales)")
    else:
        print(f"2. Financials: ✗ Error")
    
    if data.get("historical"):
        print(f"3. Históricos: ✓ {len(data['historical'].get('revenue', []))} años de datos")
    else:
        print(f"3. Históricos: ✗ Error")
    
    if data.get("errors"):
        print(f"\n⚠️  Errores: {data['errors']}")
    
    print(f"\n{'='*60}\n")
    
    return data


def benchmark_comparison(symbol: str = "AAPL"):
    """
    Compara el rendimiento de la versión paralela.
    Ejecuta múltiples veces para obtener promedio.
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK: Paralelización para {symbol}")
    print(f"{'='*60}\n")
    
    service = FinancialDataService()
    
    # Limpiar caché para test justo
    _data_cache.clear()
    
    times = []
    for i in range(3):
        _data_cache.clear()  # Limpiar entre runs
        start = time.time()
        data = service.get_complete_analysis_data(symbol)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"   Run {i+1}: {elapsed:.2f}s")
    
    avg_time = sum(times) / len(times)
    print(f"\n📊 Promedio: {avg_time:.2f}s")
    print(f"   (Con caché frío - sin hits)")
    
    # Ahora con caché caliente
    start = time.time()
    data = service.get_complete_analysis_data(symbol)
    cached_time = time.time() - start
    print(f"\n⚡ Con caché caliente: {cached_time:.2f}s")
    
    return avg_time, cached_time


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    if "--benchmark" in sys.argv:
        benchmark_comparison(symbol)
    else:
        test_fetcher(symbol)
