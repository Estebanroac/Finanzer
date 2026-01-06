"""
Financial Data Fetcher Module
=============================
Módulo para obtener datos financieros de empresas desde múltiples fuentes.
Soporta Yahoo Finance (gratuito) y Financial Modeling Prep (freemium).

Autor: Esteban
Versión: 2.2 - Rate limiting y retry con backoff exponencial
"""

import os
import time
import random
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json

# Configurar logging
logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    # Intentar importar la excepción de rate limit
    try:
        from yfinance.exceptions import YFRateLimitError
        YF_RATE_LIMIT_AVAILABLE = True
    except ImportError:
        YF_RATE_LIMIT_AVAILABLE = False
        YFRateLimitError = Exception  # Fallback
except ImportError:
    YFINANCE_AVAILABLE = False
    YF_RATE_LIMIT_AVAILABLE = False
    YFRateLimitError = Exception

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# =========================
# CONSTANTES DE RETRY
# =========================
MAX_RETRIES = 3
BASE_DELAY = 2  # segundos
MAX_DELAY = 30  # segundos máximo de espera


def retry_with_backoff(func):
    """
    Decorador que implementa retry con backoff exponencial.
    Especialmente útil para manejar rate limiting de Yahoo Finance.
    """
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Detectar rate limiting (varias formas)
                is_rate_limit = (
                    'rate' in error_str and 'limit' in error_str or
                    'too many requests' in error_str or
                    '429' in error_str or
                    (YF_RATE_LIMIT_AVAILABLE and isinstance(e, YFRateLimitError))
                )
                
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    # Backoff exponencial con jitter
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Rate limited. Reintentando en {delay:.1f}s (intento {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                elif attempt < MAX_RETRIES - 1:
                    # Para otros errores, esperar menos
                    time.sleep(1)
                else:
                    logger.error(f"Falló después de {MAX_RETRIES} intentos: {e}")
                    raise
        
        raise last_exception
    return wrapper


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
_data_cache = SimpleCache(default_ttl_minutes=10)


# =========================
# EXCEPCIONES PERSONALIZADAS
# =========================

class InvalidSymbolError(Exception):
    """Excepción para símbolos inválidos o no encontrados."""
    def __init__(self, symbol: str, message: str = None):
        self.symbol = symbol
        self.message = message or f"Símbolo '{symbol}' no encontrado o inválido"
        super().__init__(self.message)


class RateLimitError(Exception):
    """Excepción para cuando se alcanza el límite de solicitudes."""
    def __init__(self, message: str = "Rate limit alcanzado. Intente más tarde."):
        self.message = message
        super().__init__(self.message)


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
    
    def _calculate_debt_trend(self, recent_de: Optional[float], old_de: Optional[float]) -> str:
        """
        Calcula la tendencia de deuda comparando D/E reciente vs antiguo.
        
        CORREGIDO según feedback profesional:
        - Amazon mostró D/E: 0.96 → 0.67 → 0.46 (bajando) pero modelo decía "Aumentando"
        - La lógica anterior tenía defaults incorrectos que invertían el resultado
        
        Returns:
            "improving" si la deuda bajó (D/E reciente < D/E antiguo)
            "increasing" si la deuda subió
            "stable" si no hay cambio significativo o faltan datos
        """
        # Si no tenemos ambos datos, no podemos determinar tendencia
        if recent_de is None or old_de is None:
            return "unknown"
        
        # Calcular cambio porcentual
        if old_de == 0:
            # Si antes era 0 y ahora hay deuda, está aumentando
            return "increasing" if recent_de > 0.05 else "stable"
        
        change_pct = (recent_de - old_de) / old_de
        
        # Umbral de 10% para considerar cambio significativo
        if change_pct < -0.10:  # Bajó más del 10%
            return "improving"
        elif change_pct > 0.10:  # Subió más del 10%
            return "increasing"
        else:
            return "stable"
    
    def get_company_profile(self, symbol: str) -> Optional[CompanyProfile]:
        """Obtiene el perfil de la empresa (con caché y retry)."""
        cache_key = _data_cache._make_key("profile", symbol.upper())
        
        # Verificar caché
        cached = _data_cache.get(cache_key)
        if cached:
            return cached
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
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
                return profile
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Detectar rate limiting
                is_rate_limit = (
                    'rate' in error_str and 'limit' in error_str or
                    'too many requests' in error_str or
                    '429' in error_str or
                    (YF_RATE_LIMIT_AVAILABLE and isinstance(e, YFRateLimitError))
                )
                
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Rate limited obteniendo perfil de {symbol}. Reintentando en {delay:.1f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"Error inesperado obteniendo perfil de {symbol}: {e}")
                    if attempt == MAX_RETRIES - 1:
                        return None
        
        return None
    
    def get_financial_data(self, symbol: str) -> Optional[FinancialStatements]:
        """Obtiene todos los datos financieros de una empresa (con caché y retry)."""
        cache_key = _data_cache._make_key("financials", symbol.upper())
        
        # Verificar caché
        cached = _data_cache.get(cache_key)
        if cached:
            return cached
        
        # Helper function fuera del loop
        def get_latest(df, key):
            try:
                if df is not None and not df.empty and key in df.index:
                    val = df.loc[key].iloc[0]
                    return float(val) if val is not None and str(val) != 'nan' else None
            except:
                pass
            return None
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Obtener estados financieros
                income_stmt = ticker.financials
                balance_sheet = ticker.balance_sheet
                cash_flow = ticker.cashflow
                
                # Income Statement
                revenue = get_latest(income_stmt, "Total Revenue")
                gross_profit = get_latest(income_stmt, "Gross Profit")
                operating_income = get_latest(income_stmt, "Operating Income")
                net_income = get_latest(income_stmt, "Net Income")
                ebitda_val = get_latest(income_stmt, "EBITDA")
                interest_expense = get_latest(income_stmt, "Interest Expense")
                
                # Balance Sheet
                total_assets = get_latest(balance_sheet, "Total Assets")
                current_assets = get_latest(balance_sheet, "Current Assets")
                cash = get_latest(balance_sheet, "Cash And Cash Equivalents")
                if cash is None:
                    cash = get_latest(balance_sheet, "Cash Cash Equivalents And Short Term Investments")
                inventories = get_latest(balance_sheet, "Inventory")
                total_liabilities = get_latest(balance_sheet, "Total Liabilities Net Minority Interest")
                current_liabilities = get_latest(balance_sheet, "Current Liabilities")
                total_debt = get_latest(balance_sheet, "Total Debt")
                long_term_debt = get_latest(balance_sheet, "Long Term Debt")
                total_equity = get_latest(balance_sheet, "Stockholders Equity")
                if total_equity is None:
                    total_equity = get_latest(balance_sheet, "Total Equity Gross Minority Interest")
                retained_earnings = get_latest(balance_sheet, "Retained Earnings")
                
                # Cash Flow
                operating_cf = get_latest(cash_flow, "Operating Cash Flow")
                capex = get_latest(cash_flow, "Capital Expenditure")
                if capex is not None:
                    capex = abs(capex)  # CapEx suele venir negativo
                fcf = get_latest(cash_flow, "Free Cash Flow")
                dividends = get_latest(cash_flow, "Cash Dividends Paid")
                
                # Depreciation
                depreciation = get_latest(cash_flow, "Depreciation And Amortization")
                
                # Datos de info
                shares = info.get("sharesOutstanding")
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                
                # Calcular FCF si no está disponible
                if fcf is None and operating_cf is not None and capex is not None:
                    fcf = operating_cf - capex
                
                # Growth rates
                try:
                    if income_stmt is not None and len(income_stmt.columns) >= 2:
                        rev_current = income_stmt.loc["Total Revenue"].iloc[0]
                        rev_previous = income_stmt.loc["Total Revenue"].iloc[1]
                        if rev_previous and rev_previous != 0:
                            revenue_growth = (rev_current - rev_previous) / abs(rev_previous)
                        else:
                            revenue_growth = None
                    else:
                        revenue_growth = None
                except:
                    revenue_growth = None
                
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
                
                # Guardar en caché (10 min para datos financieros)
                _data_cache.set(cache_key, result, ttl_minutes=10)
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Detectar rate limiting
                is_rate_limit = (
                    'rate' in error_str and 'limit' in error_str or
                    'too many requests' in error_str or
                    '429' in error_str or
                    (YF_RATE_LIMIT_AVAILABLE and isinstance(e, YFRateLimitError))
                )
                
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Rate limited obteniendo datos de {symbol}. Reintentando en {delay:.1f}s (intento {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    logger.error(f"Error obteniendo datos financieros de {symbol}: {e}")
                    import traceback
                    traceback.print_exc()
                    if attempt == MAX_RETRIES - 1:
                        return None
        
        return None
    
    def get_historical_metrics(self, symbol: str, years: int = 5) -> Dict[str, List[float]]:
        """Obtiene métricas históricas para análisis de tendencias (con caché y retry)."""
        cache_key = _data_cache._make_key("historical", symbol.upper(), years)
        
        cached = _data_cache.get(cache_key)
        if cached:
            return cached
        
        def extract_series(df, key):
            try:
                if df is not None and key in df.index:
                    series = df.loc[key].dropna().tolist()
                    return [float(x) for x in series[:years]]
            except:
                pass
            return []
        
        for attempt in range(MAX_RETRIES):
            try:
                ticker = yf.Ticker(symbol)
                income_stmt = ticker.financials
                balance_sheet = ticker.balance_sheet
                cash_flow = ticker.cashflow
                
                result = {
                    "revenue": extract_series(income_stmt, "Total Revenue"),
                    "net_income": extract_series(income_stmt, "Net Income"),
                    "operating_income": extract_series(income_stmt, "Operating Income"),
                    "total_equity": extract_series(balance_sheet, "Stockholders Equity"),
                    "total_debt": extract_series(balance_sheet, "Total Debt"),
                    "fcf": extract_series(cash_flow, "Free Cash Flow"),
                }
                
                # Guardar en caché (30 min para históricos)
                _data_cache.set(cache_key, result, ttl_minutes=30)
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = 'rate' in error_str and 'limit' in error_str or 'too many requests' in error_str
                
                if is_rate_limit and attempt < MAX_RETRIES - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Rate limited obteniendo históricos de {symbol}. Reintentando en {delay:.1f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"Error obteniendo históricos de {symbol}: {e}")
                    return {}
        
        return {}
    
    def get_detailed_historical_data(self, symbol: str, years: int = 5) -> Dict[str, Any]:
        """
        Obtiene datos históricos detallados año por año.
        Retorna un diccionario con años como keys y métricas como valores.
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Obtener estados financieros
            income_stmt = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
            
            # Obtener las fechas (columnas) disponibles
            if income_stmt is None or income_stmt.empty:
                return {"years": [], "data": {}, "error": "No hay datos históricos disponibles"}
            
            # Las columnas son las fechas de los reportes
            dates = income_stmt.columns[:years]
            
            historical_data = {
                "years": [],
                "data": {},
                "summary": {}
            }
            
            def safe_get(df, key, col):
                """Obtiene un valor de forma segura del DataFrame."""
                try:
                    if df is not None and key in df.index and col in df.columns:
                        val = df.loc[key, col]
                        if pd.notna(val):
                            return float(val)
                except:
                    pass
                return None
            
            def calculate_margin(numerator, denominator):
                """Calcula un margen de forma segura."""
                if numerator is not None and denominator is not None and denominator != 0:
                    return (numerator / denominator) * 100
                return None
            
            def calculate_growth(current, previous):
                """Calcula crecimiento YoY."""
                if current is not None and previous is not None and previous != 0:
                    return ((current - previous) / abs(previous)) * 100
                return None
            
            prev_revenue = None
            prev_net_income = None
            
            for i, date in enumerate(dates):
                year = date.year if hasattr(date, 'year') else str(date)[:4]
                historical_data["years"].append(year)
                
                # Extraer métricas del Income Statement
                revenue = safe_get(income_stmt, "Total Revenue", date)
                gross_profit = safe_get(income_stmt, "Gross Profit", date)
                operating_income = safe_get(income_stmt, "Operating Income", date)
                net_income = safe_get(income_stmt, "Net Income", date)
                ebitda = safe_get(income_stmt, "EBITDA", date)
                
                # Si no hay EBITDA directo, intentar calcularlo
                if ebitda is None:
                    depreciation = safe_get(cash_flow, "Depreciation And Amortization", date)
                    if operating_income is not None and depreciation is not None:
                        ebitda = operating_income + depreciation
                
                # Extraer métricas del Balance Sheet
                total_assets = safe_get(balance_sheet, "Total Assets", date)
                total_equity = safe_get(balance_sheet, "Stockholders Equity", date)
                total_debt = safe_get(balance_sheet, "Total Debt", date)
                long_term_debt = safe_get(balance_sheet, "Long Term Debt", date)
                cash = safe_get(balance_sheet, "Cash And Cash Equivalents", date)
                current_assets = safe_get(balance_sheet, "Current Assets", date)
                current_liabilities = safe_get(balance_sheet, "Current Liabilities", date)
                
                # Shares Outstanding (para F-Score criterio de dilución)
                shares_outstanding = safe_get(balance_sheet, "Ordinary Shares Number", date)
                if shares_outstanding is None:
                    shares_outstanding = safe_get(balance_sheet, "Share Issued", date)
                if shares_outstanding is None:
                    shares_outstanding = safe_get(balance_sheet, "Common Stock Shares Outstanding", date)
                
                # Extraer métricas del Cash Flow
                operating_cash_flow = safe_get(cash_flow, "Operating Cash Flow", date)
                capex = safe_get(cash_flow, "Capital Expenditure", date)
                fcf = safe_get(cash_flow, "Free Cash Flow", date)
                
                # Si no hay FCF directo, calcularlo
                if fcf is None and operating_cash_flow is not None and capex is not None:
                    fcf = operating_cash_flow + capex  # capex es negativo
                
                # Calcular márgenes
                gross_margin = calculate_margin(gross_profit, revenue)
                operating_margin = calculate_margin(operating_income, revenue)
                net_margin = calculate_margin(net_income, revenue)
                ebitda_margin = calculate_margin(ebitda, revenue)
                
                # Calcular ratios
                roe = calculate_margin(net_income, total_equity) if total_equity and total_equity > 0 else None
                roa = calculate_margin(net_income, total_assets) if total_assets and total_assets > 0 else None
                
                debt_to_equity = None
                if total_debt is not None and total_equity is not None and total_equity > 0:
                    debt_to_equity = total_debt / total_equity
                
                current_ratio = None
                if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
                    current_ratio = current_assets / current_liabilities
                
                net_debt = None
                if total_debt is not None and cash is not None:
                    net_debt = total_debt - cash
                
                net_debt_to_ebitda = None
                if net_debt is not None and ebitda is not None and ebitda > 0:
                    net_debt_to_ebitda = net_debt / ebitda
                
                # Calcular crecimiento
                revenue_growth = calculate_growth(revenue, prev_revenue)
                net_income_growth = calculate_growth(net_income, prev_net_income)
                
                prev_revenue = revenue
                prev_net_income = net_income
                
                # Guardar datos del año
                historical_data["data"][year] = {
                    # Ingresos y utilidades (en millones)
                    "revenue": revenue,
                    "revenue_mm": revenue / 1e6 if revenue else None,
                    "gross_profit": gross_profit,
                    "gross_profit_mm": gross_profit / 1e6 if gross_profit else None,
                    "operating_income": operating_income,
                    "operating_income_mm": operating_income / 1e6 if operating_income else None,
                    "net_income": net_income,
                    "net_income_mm": net_income / 1e6 if net_income else None,
                    "ebitda": ebitda,
                    "ebitda_mm": ebitda / 1e6 if ebitda else None,
                    
                    # Márgenes (en porcentaje)
                    "gross_margin": gross_margin,
                    "operating_margin": operating_margin,
                    "net_margin": net_margin,
                    "ebitda_margin": ebitda_margin,
                    
                    # Balance
                    "total_assets": total_assets,
                    "total_assets_mm": total_assets / 1e6 if total_assets else None,
                    "total_equity": total_equity,
                    "total_equity_mm": total_equity / 1e6 if total_equity else None,
                    "total_debt": total_debt,
                    "total_debt_mm": total_debt / 1e6 if total_debt else None,
                    "long_term_debt": long_term_debt,
                    "long_term_debt_mm": long_term_debt / 1e6 if long_term_debt else None,
                    "shares_outstanding": shares_outstanding,
                    "cash": cash,
                    "cash_mm": cash / 1e6 if cash else None,
                    "net_debt": net_debt,
                    "net_debt_mm": net_debt / 1e6 if net_debt else None,
                    
                    # Ratios
                    "roe": roe,
                    "roa": roa,
                    "debt_to_equity": debt_to_equity,
                    "current_ratio": current_ratio,
                    "net_debt_to_ebitda": net_debt_to_ebitda,
                    
                    # Cash Flow
                    "operating_cash_flow": operating_cash_flow,
                    "operating_cash_flow_mm": operating_cash_flow / 1e6 if operating_cash_flow else None,
                    "fcf": fcf,
                    "fcf_mm": fcf / 1e6 if fcf else None,
                    "capex": capex,
                    "capex_mm": capex / 1e6 if capex else None,
                    
                    # Crecimiento
                    "revenue_growth": revenue_growth,
                    "net_income_growth": net_income_growth,
                }
            
            # Calcular resumen de tendencias
            if len(historical_data["years"]) >= 2:
                years_list = historical_data["years"]
                first_year = years_list[-1]  # Año más antiguo
                last_year = years_list[0]    # Año más reciente
                
                first_data = historical_data["data"].get(first_year, {})
                last_data = historical_data["data"].get(last_year, {})
                
                def calc_cagr(end_val, start_val, periods):
                    if end_val and start_val and start_val > 0 and periods > 0:
                        return ((end_val / start_val) ** (1 / periods) - 1) * 100
                    return None
                
                num_years = len(years_list) - 1
                
                historical_data["summary"] = {
                    "revenue_cagr": calc_cagr(
                        last_data.get("revenue"), 
                        first_data.get("revenue"), 
                        num_years
                    ),
                    "net_income_cagr": calc_cagr(
                        last_data.get("net_income"), 
                        first_data.get("net_income"), 
                        num_years
                    ),
                    "margin_trend": "improving" if (last_data.get("net_margin") or 0) > (first_data.get("net_margin") or 0) else "declining",
                    # CORREGIDO: Manejar None apropiadamente y comparar D/E correctamente
                    # Si D/E reciente < D/E antiguo → mejorando (empresa se desapalancó)
                    "debt_trend": self._calculate_debt_trend(
                        last_data.get("debt_to_equity"),
                        first_data.get("debt_to_equity")
                    ),
                }
            
            return historical_data
            
        except Exception as e:
            print(f"Error obteniendo históricos detallados de {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return {"years": [], "data": {}, "error": str(e)}
    
    def get_market_comparison_data(self, sector: str) -> Dict[str, Any]:
        """
        Obtiene datos del mercado (SPY) y del sector (ETF) para comparación.
        Calcula YTD real (desde 1 de enero) y retorno de 1 año.
        """
        from datetime import datetime, timedelta
        
        result = {
            "market": {},
            "sector": {},
        }
        
        # Fecha de inicio del año para YTD real
        current_year = datetime.now().year
        ytd_start = f"{current_year}-01-01"
        
        def calculate_returns(ticker_symbol: str) -> Dict[str, float]:
            """Calcula YTD real y retorno de 1 año."""
            try:
                ticker = yf.Ticker(ticker_symbol)
                
                # YTD real (desde 1 de enero)
                ytd_hist = ticker.history(start=ytd_start)
                ytd_return = None
                if not ytd_hist.empty and len(ytd_hist) > 1:
                    ytd_return = ((ytd_hist['Close'].iloc[-1] / ytd_hist['Close'].iloc[0]) - 1) * 100
                
                # Retorno de 1 año
                year_hist = ticker.history(period="1y")
                year_return = None
                if not year_hist.empty and len(year_hist) > 1:
                    year_return = ((year_hist['Close'].iloc[-1] / year_hist['Close'].iloc[0]) - 1) * 100
                
                return {
                    "ytd_return": round(ytd_return, 2) if ytd_return else None,
                    "year_return": round(year_return, 2) if year_return else None,
                }
            except Exception as e:
                print(f"Error calculando retornos para {ticker_symbol}: {e}")
                return {"ytd_return": None, "year_return": None}
        
        try:
            # Datos del mercado (SPY)
            spy = yf.Ticker("SPY")
            spy_info = spy.info
            spy_returns = calculate_returns("SPY")
            
            result["market"] = {
                "name": "S&P 500",
                "symbol": "SPY",
                "pe": spy_info.get("trailingPE"),
                "price": spy_info.get("regularMarketPrice"),
                "ytd_return": spy_returns["ytd_return"],
                "year_return": spy_returns["year_return"],
                "dividend_yield": spy_info.get("trailingAnnualDividendYield", 0) * 100 if spy_info.get("trailingAnnualDividendYield") else None,
                "52w_high": spy_info.get("fiftyTwoWeekHigh"),
                "52w_low": spy_info.get("fiftyTwoWeekLow"),
            }
            
        except Exception as e:
            print(f"Error obteniendo datos de SPY: {e}")
            result["market"] = {"name": "S&P 500", "symbol": "SPY", "error": str(e)}
        
        try:
            # Datos del sector (ETF) - usando mapeo dinámico
            etf_symbol = self._get_sector_etf_symbol(sector)
            etf = yf.Ticker(etf_symbol)
            etf_info = etf.info
            etf_returns = calculate_returns(etf_symbol)
            
            result["sector"] = {
                "name": etf_info.get("shortName", sector),
                "symbol": etf_symbol,
                "pe": etf_info.get("trailingPE"),
                "price": etf_info.get("regularMarketPrice"),
                "ytd_return": etf_returns["ytd_return"],
                "year_return": etf_returns["year_return"],
                "dividend_yield": etf_info.get("trailingAnnualDividendYield", 0) * 100 if etf_info.get("trailingAnnualDividendYield") else None,
                "52w_high": etf_info.get("fiftyTwoWeekHigh"),
                "52w_low": etf_info.get("fiftyTwoWeekLow"),
                "beta": etf_info.get("beta3Year"),
            }
            
        except Exception as e:
            print(f"Error obteniendo datos del sector {sector}: {e}")
            result["sector"] = {"name": sector, "symbol": self._get_sector_etf_symbol(sector), "error": str(e)}
        
        return result
    
    def get_sector_averages(self, sector: str) -> Dict[str, Optional[float]]:
        """Obtiene promedios del sector (simplificado - usa ETFs sectoriales)."""
        # Usar el mismo mapeo dinámico
        etf_symbol = self._get_sector_etf_symbol(sector)
        
        try:
            ticker = yf.Ticker(etf_symbol)
            info = ticker.info
            
            return {
                "sector_pe": info.get("trailingPE", 20.0),
                "sector_ev_ebitda": 12.0,  # Difícil de obtener para ETFs
            }
        except:
            return {"sector_pe": 20.0, "sector_ev_ebitda": 12.0}
    
    def _get_sector_etf_symbol(self, sector_name: str) -> str:
        """Mapeo robusto de sector a ETF (reutilizable)."""
        if not sector_name:
            return "SPY"
        
        sector_etf_mapping = {
            # Tecnología
            "technology": "XLK",
            "tech": "XLK",
            "information technology": "XLK",
            "software": "XLK",
            "semiconductors": "XLK",
            # Financiero
            "financial services": "XLF",
            "financial": "XLF",
            "financials": "XLF",
            "banks": "XLF",
            "banking": "XLF",
            "insurance": "XLF",
            "capital markets": "XLF",
            "credit services": "XLF",
            # Healthcare
            "healthcare": "XLV",
            "health care": "XLV",
            "biotechnology": "XLV",
            "pharmaceuticals": "XLV",
            "medical devices": "XLV",
            # Consumo Cíclico
            "consumer cyclical": "XLY",
            "consumer discretionary": "XLY",
            "retail": "XLY",
            "automobiles": "XLY",
            "auto manufacturers": "XLY",
            "restaurants": "XLY",
            "travel & leisure": "XLY",
            "apparel": "XLY",
            # Consumo Defensivo
            "consumer defensive": "XLP",
            "consumer staples": "XLP",
            "food & beverage": "XLP",
            "household products": "XLP",
            "tobacco": "XLP",
            # Industriales
            "industrials": "XLI",
            "industrial": "XLI",
            "aerospace & defense": "XLI",
            "machinery": "XLI",
            "construction": "XLI",
            "transportation": "XLI",
            "airlines": "XLI",
            # Energía
            "energy": "XLE",
            "oil & gas": "XLE",
            "oil": "XLE",
            "gas": "XLE",
            "petroleum": "XLE",
            # Utilities
            "utilities": "XLU",
            "utility": "XLU",
            "electric utilities": "XLU",
            "gas utilities": "XLU",
            "water utilities": "XLU",
            # Real Estate
            "real estate": "XLRE",
            "reits": "XLRE",
            "reit": "XLRE",
            "real estate services": "XLRE",
            # Materiales
            "materials": "XLB",
            "basic materials": "XLB",
            "chemicals": "XLB",
            "metals & mining": "XLB",
            "steel": "XLB",
            "gold": "XLB",
            # Comunicaciones
            "communication services": "XLC",
            "communications": "XLC",
            "telecommunication": "XLC",
            "telecom": "XLC",
            "media": "XLC",
            "entertainment": "XLC",
            "interactive media": "XLC",
        }
        
        sector_lower = sector_name.lower().strip()
        
        # Búsqueda exacta
        if sector_lower in sector_etf_mapping:
            return sector_etf_mapping[sector_lower]
        
        # Búsqueda parcial
        for key, etf in sector_etf_mapping.items():
            if key in sector_lower or sector_lower in key:
                return etf
        
        return "SPY"
    
    def get_sector_comparison_data(self, sector: str) -> Dict[str, Any]:
        """
        Obtiene datos completos del sector para comparación.
        Incluye promedios típicos por sector y datos del ETF sectorial.
        """
        # Datos típicos por sector (basados en promedios históricos)
        sector_benchmarks = {
            "Technology": {
                "name": "Tecnología",
                "etf": "XLK",
                "typical_pe": 28.0,
                "typical_ps": 6.5,
                "typical_pb": 8.0,
                "typical_ev_ebitda": 18.0,
                "typical_roe": 0.22,
                "typical_roa": 0.12,
                "typical_gross_margin": 0.50,
                "typical_operating_margin": 0.22,
                "typical_net_margin": 0.18,
                "typical_debt_equity": 0.45,
                "typical_current_ratio": 2.0,
                "growth_outlook": "Alto",
                "volatility": "Alta",
                "dividend_typical": "Bajo",
            },
            "Healthcare": {
                "name": "Salud",
                "etf": "XLV",
                "typical_pe": 22.0,
                "typical_ps": 2.5,
                "typical_pb": 4.5,
                "typical_ev_ebitda": 14.0,
                "typical_roe": 0.18,
                "typical_roa": 0.08,
                "typical_gross_margin": 0.55,
                "typical_operating_margin": 0.18,
                "typical_net_margin": 0.12,
                "typical_debt_equity": 0.60,
                "typical_current_ratio": 1.8,
                "growth_outlook": "Moderado-Alto",
                "volatility": "Media",
                "dividend_typical": "Moderado",
            },
            "Financial Services": {
                "name": "Servicios Financieros",
                "etf": "XLF",
                "typical_pe": 14.0,
                "typical_ps": 3.0,
                "typical_pb": 1.3,
                "typical_ev_ebitda": 10.0,
                "typical_roe": 0.12,
                "typical_roa": 0.01,
                "typical_gross_margin": 0.60,
                "typical_operating_margin": 0.30,
                "typical_net_margin": 0.22,
                "typical_debt_equity": 1.50,
                "typical_current_ratio": 1.2,
                "growth_outlook": "Moderado",
                "volatility": "Media-Alta",
                "dividend_typical": "Alto",
            },
            "Consumer Cyclical": {
                "name": "Consumo Discrecional",
                "etf": "XLY",
                "typical_pe": 22.0,
                "typical_ps": 1.8,
                "typical_pb": 6.0,
                "typical_ev_ebitda": 14.0,
                "typical_roe": 0.25,
                "typical_roa": 0.08,
                "typical_gross_margin": 0.35,
                "typical_operating_margin": 0.10,
                "typical_net_margin": 0.06,
                "typical_debt_equity": 1.00,
                "typical_current_ratio": 1.3,
                "growth_outlook": "Cíclico",
                "volatility": "Alta",
                "dividend_typical": "Bajo",
            },
            "Consumer Defensive": {
                "name": "Consumo Básico",
                "etf": "XLP",
                "typical_pe": 20.0,
                "typical_ps": 1.5,
                "typical_pb": 5.0,
                "typical_ev_ebitda": 14.0,
                "typical_roe": 0.22,
                "typical_roa": 0.08,
                "typical_gross_margin": 0.35,
                "typical_operating_margin": 0.12,
                "typical_net_margin": 0.08,
                "typical_debt_equity": 1.20,
                "typical_current_ratio": 1.0,
                "growth_outlook": "Estable",
                "volatility": "Baja",
                "dividend_typical": "Alto",
            },
            "Industrials": {
                "name": "Industriales",
                "etf": "XLI",
                "typical_pe": 20.0,
                "typical_ps": 2.0,
                "typical_pb": 4.5,
                "typical_ev_ebitda": 12.0,
                "typical_roe": 0.18,
                "typical_roa": 0.06,
                "typical_gross_margin": 0.28,
                "typical_operating_margin": 0.12,
                "typical_net_margin": 0.08,
                "typical_debt_equity": 0.90,
                "typical_current_ratio": 1.4,
                "growth_outlook": "Cíclico",
                "volatility": "Media",
                "dividend_typical": "Moderado",
            },
            "Energy": {
                "name": "Energía",
                "etf": "XLE",
                "typical_pe": 12.0,
                "typical_ps": 1.2,
                "typical_pb": 2.0,
                "typical_ev_ebitda": 6.0,
                "typical_roe": 0.15,
                "typical_roa": 0.07,
                "typical_gross_margin": 0.45,
                "typical_operating_margin": 0.15,
                "typical_net_margin": 0.10,
                "typical_debt_equity": 0.40,
                "typical_current_ratio": 1.2,
                "growth_outlook": "Volátil",
                "volatility": "Muy Alta",
                "dividend_typical": "Alto",
            },
            "Utilities": {
                "name": "Servicios Públicos",
                "etf": "XLU",
                "typical_pe": 18.0,
                "typical_ps": 2.5,
                "typical_pb": 2.0,
                "typical_ev_ebitda": 12.0,
                "typical_roe": 0.10,
                "typical_roa": 0.03,
                "typical_gross_margin": 0.40,
                "typical_operating_margin": 0.22,
                "typical_net_margin": 0.12,
                "typical_debt_equity": 1.40,
                "typical_current_ratio": 0.8,
                "growth_outlook": "Estable",
                "volatility": "Baja",
                "dividend_typical": "Muy Alto",
            },
            "Real Estate": {
                "name": "Bienes Raíces",
                "etf": "XLRE",
                "typical_pe": 35.0,
                "typical_ps": 6.0,
                "typical_pb": 2.5,
                "typical_ev_ebitda": 18.0,
                "typical_roe": 0.08,
                "typical_roa": 0.04,
                "typical_gross_margin": 0.55,
                "typical_operating_margin": 0.30,
                "typical_net_margin": 0.20,
                "typical_debt_equity": 0.90,
                "typical_current_ratio": 1.0,
                "growth_outlook": "Moderado",
                "volatility": "Media",
                "dividend_typical": "Muy Alto",
            },
            "Materials": {
                "name": "Materiales",
                "etf": "XLB",
                "typical_pe": 16.0,
                "typical_ps": 1.8,
                "typical_pb": 3.0,
                "typical_ev_ebitda": 9.0,
                "typical_roe": 0.15,
                "typical_roa": 0.06,
                "typical_gross_margin": 0.30,
                "typical_operating_margin": 0.14,
                "typical_net_margin": 0.08,
                "typical_debt_equity": 0.60,
                "typical_current_ratio": 1.8,
                "growth_outlook": "Cíclico",
                "volatility": "Alta",
                "dividend_typical": "Moderado",
            },
            "Communication Services": {
                "name": "Comunicaciones",
                "etf": "XLC",
                "typical_pe": 18.0,
                "typical_ps": 2.5,
                "typical_pb": 3.5,
                "typical_ev_ebitda": 10.0,
                "typical_roe": 0.12,
                "typical_roa": 0.05,
                "typical_gross_margin": 0.55,
                "typical_operating_margin": 0.18,
                "typical_net_margin": 0.12,
                "typical_debt_equity": 0.80,
                "typical_current_ratio": 1.3,
                "growth_outlook": "Moderado",
                "volatility": "Media-Alta",
                "dividend_typical": "Bajo-Moderado",
            },
        }
        
        # Default si no encontramos el sector
        default_data = {
            "name": sector or "General",
            "etf": "SPY",
            "typical_pe": 20.0,
            "typical_ps": 2.5,
            "typical_pb": 4.0,
            "typical_ev_ebitda": 12.0,
            "typical_roe": 0.15,
            "typical_roa": 0.06,
            "typical_gross_margin": 0.40,
            "typical_operating_margin": 0.15,
            "typical_net_margin": 0.10,
            "typical_debt_equity": 0.80,
            "typical_current_ratio": 1.5,
            "growth_outlook": "Moderado",
            "volatility": "Media",
            "dividend_typical": "Moderado",
        }
        
        # Búsqueda flexible del sector
        benchmark = None
        if sector:
            sector_lower = sector.lower().strip()
            
            # Primero búsqueda exacta
            benchmark = sector_benchmarks.get(sector)
            
            # Si no, búsqueda case-insensitive
            if not benchmark:
                for key, data in sector_benchmarks.items():
                    if key.lower() == sector_lower:
                        benchmark = data
                        break
            
            # Si no, búsqueda parcial
            if not benchmark:
                for key, data in sector_benchmarks.items():
                    if sector_lower in key.lower() or key.lower() in sector_lower:
                        benchmark = data
                        break
        
        # Usar default si no encontramos
        if not benchmark:
            benchmark = default_data
            # Pero usar el ETF correcto basado en el mapeo
            etf_from_mapping = self._get_sector_etf_symbol(sector)
            benchmark["etf"] = etf_from_mapping
        
        # Intentar obtener datos en tiempo real del ETF
        try:
            etf_symbol = benchmark.get("etf", "SPY")
            ticker = yf.Ticker(etf_symbol)
            info = ticker.info
            hist = ticker.history(period="1y")
            
            # Calcular rendimiento del sector (YTD aproximado)
            if not hist.empty:
                ytd_return = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
                benchmark["ytd_return"] = round(ytd_return, 2)
            
            # P/E actual del ETF si está disponible
            if info.get("trailingPE"):
                benchmark["current_sector_pe"] = info.get("trailingPE")
            
            benchmark["etf_price"] = info.get("regularMarketPrice")
            benchmark["etf_name"] = info.get("shortName", etf_symbol)
            
        except Exception as e:
            benchmark["ytd_return"] = None
            benchmark["current_sector_pe"] = benchmark["typical_pe"]
        
        return benchmark


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
    
    def get_complete_analysis_data(self, symbol: str) -> Dict[str, Any]:
        """Obtiene todos los datos necesarios para el análisis completo."""
        result = {
            "symbol": symbol.upper(),
            "profile": None,
            "financials": None,
            "historical": None,
            "sector_averages": None,
            "contextual": {},
            "errors": [],
        }
        
        if not self.yahoo_available:
            result["errors"].append("Yahoo Finance no disponible")
            return result
        
        # Perfil
        profile = self.yahoo.get_company_profile(symbol)
        if profile:
            result["profile"] = profile
        else:
            result["errors"].append("No se pudo obtener el perfil")
        
        # Datos financieros
        financials = self.yahoo.get_financial_data(symbol)
        if financials:
            result["financials"] = financials
            
            # ===== DATOS PARA ALTMAN Z-SCORE =====
            # Working Capital = Current Assets - Current Liabilities
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
            
            # ===== DATOS PARA PIOTROSKI F-SCORE =====
            result["contextual"]["net_income"] = financials.net_income
            result["contextual"]["operating_cash_flow"] = financials.operating_cash_flow
            result["contextual"]["long_term_debt"] = financials.long_term_debt
            result["contextual"]["shares_outstanding"] = financials.shares_outstanding
            result["contextual"]["total_debt"] = financials.total_debt
            result["contextual"]["interest_expense"] = financials.interest_expense
            
        else:
            result["errors"].append("No se pudieron obtener datos financieros")
        
        # Históricos para CAGR y FCF trend (formato de listas)
        historical = self.yahoo.get_historical_metrics(symbol)
        if historical:
            result["historical"] = historical
            
            # Calcular métricas contextuales desde históricos
            if historical.get("revenue") and len(historical["revenue"]) >= 3:
                revenues = historical["revenue"]
                try:
                    from financial_ratios import cagr
                    result["contextual"]["revenue_cagr_3y"] = cagr(
                        revenues[-1], revenues[0], min(3, len(revenues)-1)
                    )
                    if len(revenues) >= 5:
                        result["contextual"]["revenue_cagr_5y"] = cagr(
                            revenues[-1], revenues[0], min(5, len(revenues)-1)
                        )
                except:
                    pass
            
            # FCF trend
            if historical.get("fcf"):
                fcf_list = historical["fcf"]
                negative_years = sum(1 for x in fcf_list if x and x < 0)
                result["contextual"]["fcf_trend_negative_years"] = negative_years
        
        # ===== DATOS HISTÓRICOS DETALLADOS PARA PIOTROSKI F-SCORE =====
        # Usar get_detailed_historical_data que devuelve estructura {years: [], data: {}}
        detailed_historical = self.yahoo.get_detailed_historical_data(symbol, years=4)
        
        if detailed_historical and detailed_historical.get("years"):
            years_list = detailed_historical.get("years", [])
            hist_data = detailed_historical.get("data", {})
            
            if len(years_list) >= 2:
                current_year = years_list[0]  # Año más reciente
                prior_year = years_list[1]    # Año anterior
                
                current_data = hist_data.get(current_year, {})
                prior_data = hist_data.get(prior_year, {})
                
                # Debug: guardar para verificar qué datos tenemos
                result["contextual"]["_debug_years"] = years_list[:2]
                result["contextual"]["_debug_current_keys"] = list(current_data.keys())[:10]
                
                # ROA del año anterior (viene como porcentaje 0-100)
                if prior_data.get("roa") is not None:
                    roa_prior = prior_data.get("roa")
                    # Convertir de porcentaje a decimal si es > 1
                    result["contextual"]["roa_prior"] = roa_prior / 100 if abs(roa_prior) > 1 else roa_prior
                
                # ROA actual también (para debug)
                if current_data.get("roa") is not None:
                    roa_current = current_data.get("roa")
                    result["contextual"]["roa_current_hist"] = roa_current / 100 if abs(roa_current) > 1 else roa_current
                
                # Current ratio del año anterior
                if prior_data.get("current_ratio") is not None:
                    result["contextual"]["current_ratio_prior"] = prior_data.get("current_ratio")
                
                # Gross margin del año anterior (viene como porcentaje 0-100)
                if prior_data.get("gross_margin") is not None:
                    gm_prior = prior_data.get("gross_margin")
                    result["contextual"]["gross_margin_prior"] = gm_prior / 100 if abs(gm_prior) > 1 else gm_prior
                
                # Gross margin actual
                if current_data.get("gross_margin") is not None:
                    gm_current = current_data.get("gross_margin")
                    result["contextual"]["gross_margin_current"] = gm_current / 100 if abs(gm_current) > 1 else gm_current
                
                # Asset turnover del año anterior
                if prior_data.get("revenue") is not None and prior_data.get("total_assets") is not None:
                    if prior_data.get("total_assets") > 0:
                        result["contextual"]["asset_turnover_prior"] = prior_data.get("revenue") / prior_data.get("total_assets")
                
                # Asset turnover actual
                if current_data.get("revenue") is not None and current_data.get("total_assets") is not None:
                    if current_data.get("total_assets") > 0:
                        result["contextual"]["asset_turnover_current"] = current_data.get("revenue") / current_data.get("total_assets")
                
                # Long term debt del año anterior
                if prior_data.get("long_term_debt") is not None:
                    result["contextual"]["long_term_debt_prior"] = prior_data.get("long_term_debt")
                elif prior_data.get("total_debt") is not None:
                    # Fallback a total_debt si no hay long_term_debt específico
                    result["contextual"]["long_term_debt_prior"] = prior_data.get("total_debt")
                
                # Long term debt actual
                if current_data.get("long_term_debt") is not None:
                    result["contextual"]["long_term_debt"] = current_data.get("long_term_debt")
                elif current_data.get("total_debt") is not None:
                    result["contextual"]["long_term_debt"] = current_data.get("total_debt")
                
                # Shares del año anterior (para detectar dilución)
                if prior_data.get("shares_outstanding") is not None:
                    result["contextual"]["shares_prior"] = prior_data.get("shares_outstanding")
                
                # Shares actuales
                if current_data.get("shares_outstanding") is not None:
                    result["contextual"]["shares_outstanding"] = current_data.get("shares_outstanding")
        
        # Promedios del sector
        if profile:
            sector_avg = self.yahoo.get_sector_averages(profile.sector)
            result["sector_averages"] = sector_avg
            result["contextual"].update(sector_avg)
        
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
            "earnings_growth_rate": (financials.earnings_growth_rate or 0) * 100 if financials.earnings_growth_rate else None,
            "beta": financials.beta,
            "cogs": None,  # No siempre disponible en yfinance
        }


def test_fetcher(symbol: str = "AAPL"):
    """Función de prueba para verificar que el fetcher funciona."""
    print(f"\n{'='*60}")
    print(f"Testing Financial Data Fetcher for {symbol}")
    print(f"{'='*60}\n")
    
    service = FinancialDataService()
    
    # Test perfil
    print("1. Obteniendo perfil...")
    profile = service.yahoo.get_company_profile(symbol)
    if profile:
        print(f"   ✓ {profile.name} ({profile.sector})")
        print(f"   Market Cap: ${profile.market_cap:,.0f}" if profile.market_cap else "   Market Cap: N/A")
    else:
        print("   ✗ Error obteniendo perfil")
    
    # Test financials
    print("\n2. Obteniendo datos financieros...")
    financials = service.yahoo.get_financial_data(symbol)
    if financials:
        print(f"   ✓ Revenue: ${financials.revenue:,.0f}" if financials.revenue else "   Revenue: N/A")
        print(f"   ✓ Net Income: ${financials.net_income:,.0f}" if financials.net_income else "   Net Income: N/A")
        print(f"   ✓ Price: ${financials.price:.2f}" if financials.price else "   Price: N/A")
        print(f"   ✓ EPS: ${financials.eps:.2f}" if financials.eps else "   EPS: N/A")
        print(f"   ✓ Beta: {financials.beta:.2f}" if financials.beta else "   Beta: N/A")
    else:
        print("   ✗ Error obteniendo financials")
    
    # Test históricos
    print("\n3. Obteniendo históricos...")
    historical = service.yahoo.get_historical_metrics(symbol)
    if historical:
        for key, values in historical.items():
            if values:
                print(f"   ✓ {key}: {len(values)} años de datos")
    else:
        print("   ✗ Error obteniendo históricos")
    
    print(f"\n{'='*60}\n")
    
    return service, profile, financials, historical


if __name__ == "__main__":
    test_fetcher("AAPL")
