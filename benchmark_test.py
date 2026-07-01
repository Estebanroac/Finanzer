#!/usr/bin/env python3
"""
Benchmark Test - Stock Analyzer v2.4
=====================================
Script para medir la mejora de rendimiento con paralelización.

Uso:
    python benchmark_test.py          # Test con AAPL
    python benchmark_test.py NVDA     # Test con otro símbolo
    python benchmark_test.py --multi  # Test con múltiples símbolos
"""

import time
import sys

def run_benchmark():
    from data_fetcher import FinancialDataService, _data_cache
    
    symbols = ["AAPL", "NVDA", "MSFT"] if "--multi" in sys.argv else [sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "AAPL"]
    
    print("\n" + "="*60)
    print("🚀 BENCHMARK - Stock Analyzer v2.4 (Paralelizado)")
    print("="*60)
    
    service = FinancialDataService()
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}...")
        print("-" * 40)
        
        # Limpiar caché
        _data_cache.clear()
        
        # Medir tiempo
        start = time.time()
        
        def progress(msg, pct):
            bar = "█" * int(pct/5) + "░" * (20 - int(pct/5))
            print(f"\r   [{bar}] {pct:5.1f}% {msg:<30}", end="", flush=True)
        
        data = service.get_complete_analysis_data(symbol, progress_callback=progress)
        
        elapsed = time.time() - start
        print()  # Nueva línea después del progress bar
        
        # Mostrar resultados
        if data.get("profile"):
            print(f"   ✅ {data['profile'].name}")
        
        if data.get("financials") and data["financials"].price:
            print(f"   💰 Precio: ${data['financials'].price:.2f}")
        
        print(f"\n   ⏱️  Tiempo total: {elapsed:.2f}s")
        
        if "_timing" in data:
            print(f"   ├─ Fetch paralelo: {data['_timing'].get('parallel_fetch', 0):.2f}s")
            print(f"   └─ Procesamiento: {data['_timing'].get('total', 0) - data['_timing'].get('parallel_fetch', 0):.2f}s")
        
        # Test con caché caliente
        start2 = time.time()
        data2 = service.get_complete_analysis_data(symbol)
        cached_time = time.time() - start2
        print(f"\n   ⚡ Con caché: {cached_time:.2f}s ({elapsed/cached_time:.1f}x más rápido)")
    
    print("\n" + "="*60)
    print("✅ Benchmark completado")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_benchmark()
