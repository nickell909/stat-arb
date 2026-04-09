"""
__init__.py для модуля connectors.
Экспорт всех коннекторов и менеджера.
"""

from src.connectors.base_connector import BaseWebSocketConnector, WebSocketConfig
from src.connectors.binance_connector import BinanceConnector
from src.connectors.bybit_connector import BybitConnector
from src.connectors.okx_connector import OKXConnector
from src.connectors.exchange_manager import ExchangeManager, ExchangeConfig

__all__ = [
    'BaseWebSocketConnector',
    'WebSocketConfig',
    'BinanceConnector',
    'BybitConnector',
    'OKXConnector',
    'ExchangeManager',
    'ExchangeConfig',
]
