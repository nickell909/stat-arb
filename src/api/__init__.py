"""
__init__.py для модуля api.
Экспорт REST API клиента.
"""

from src.api.historical_data import HistoricalDataClient, RateLimitConfig

__all__ = [
    'HistoricalDataClient',
    'RateLimitConfig',
]
