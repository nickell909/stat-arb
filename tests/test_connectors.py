"""
Тесты для модуля connectors.
"""

import pytest
import asyncio
from src.connectors.base_connector import WebSocketConfig, BaseWebSocketConnector
from src.models.data_models import TickData


class TestWebSocketConfig:
    """Тесты для конфигурации WebSocket."""
    
    def test_default_values(self):
        """Тест значений по умолчанию."""
        config = WebSocketConfig(url="wss://test.com")
        
        assert config.url == "wss://test.com"
        assert config.ping_interval == 30
        assert config.ping_timeout == 10
        assert config.reconnect_delay_base == 1.0
        assert config.reconnect_delay_max == 60.0
        assert config.message_queue_size == 10000
    
    def test_custom_values(self):
        """Тест кастомных значений."""
        config = WebSocketConfig(
            url="wss://custom.com",
            ping_interval=60,
            ping_timeout=20,
            reconnect_delay_base=2.0,
            reconnect_delay_max=120.0,
            message_queue_size=5000
        )
        
        assert config.url == "wss://custom.com"
        assert config.ping_interval == 60
        assert config.ping_timeout == 20


class TestTickData:
    """Тесты для модели TickData."""
    
    def test_tick_data_creation(self):
        """Тест создания TickData."""
        tick = TickData(
            exchange='binance',
            symbol='BTC/USDT',
            timestamp_ms=1234567890000,
            bid=50000.0,
            ask=50001.0,
            last=50000.5,
            volume=1.5
        )
        
        assert tick.exchange == 'binance'
        assert tick.symbol == 'BTC/USDT'
        assert tick.timestamp_ms == 1234567890000
        assert tick.bid == 50000.0
        assert tick.ask == 50001.0
        assert tick.last == 50000.5
        assert tick.volume == 1.5
        assert tick.is_interpolated == False
    
    def test_timestamp_property(self):
        """Тест конвертации timestamp в datetime."""
        tick = TickData(
            exchange='binance',
            symbol='BTC/USDT',
            timestamp_ms=1609459200000,  # 2021-01-01 00:00:00 UTC
            bid=50000.0,
            ask=50001.0,
            last=50000.5,
            volume=1.5
        )
        
        dt = tick.timestamp
        assert dt.year == 2021
        assert dt.month == 1
        assert dt.day == 1


class TestSymbolNormalization:
    """Тесты для нормализации символов."""
    
    def test_binance_symbol_normalization(self):
        """Тест нормализации символов Binance."""
        from src.connectors.binance_connector import BinanceConnector
        
        connector = BinanceConnector()
        
        assert connector._normalize_symbol('BTCUSDT') == 'BTC/USDT'
        assert connector._normalize_symbol('ETHUSDT') == 'ETH/USDT'
        assert connector._normalize_symbol('BTCBUSD') == 'BTC/BUSD'
        assert connector._normalize_symbol('ETHBTC') == 'ETH/BTC'
    
    def test_bybit_symbol_normalization(self):
        """Тест нормализации символов Bybit."""
        from src.connectors.bybit_connector import BybitConnector
        
        connector = BybitConnector()
        
        assert connector._normalize_symbol('BTCUSDT') == 'BTC/USDT'
        assert connector._normalize_symbol('ETHUSDT') == 'ETH/USDT'
    
    def test_okx_symbol_normalization(self):
        """Тест нормализации символов OKX."""
        from src.connectors.okx_connector import OKXConnector
        
        connector = OKXConnector()
        
        assert connector._normalize_symbol('BTC-USDT') == 'BTC/USDT'
        assert connector._normalize_symbol('ETH-USDT') == 'ETH/USDT'
    
    def test_okx_symbol_denormalization(self):
        """Тест обратной конвертации символов OKX."""
        from src.connectors.okx_connector import OKXConnector
        
        connector = OKXConnector()
        
        assert connector._denormalize_symbol('BTC/USDT') == 'BTC-USDT'
        assert connector._denormalize_symbol('ETH/USDT') == 'ETH-USDT'
