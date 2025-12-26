"""
Finanzer - Callbacks de Dash.

Para usar estos callbacks, importarlos en app.py:
    from finanzer.callbacks import comparison, search, chart

Los callbacks se registran automáticamente al importar los módulos.
"""

# Importar módulos para registrar callbacks
# Nota: Los callbacks usan @callback de Dash, que se auto-registra

__all__ = ['comparison', 'search', 'chart']
