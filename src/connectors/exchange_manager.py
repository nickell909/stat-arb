"""
Менеджер подключений к биржам.
Управление множественными WebSocket коннекторами.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from src.connectors.base_connector import BaseWebSocketConnector, WebSocketConfig
from src.connectors.binance_connector import BinanceConnector
from src.connectors.bybit_connector import BybitConnector
from src.connectors.okx_connector import OKXConnector
from src.models.data_models import TickData, ConnectionStats


logger = logging.getLogger(__name__)


@dataclass
class ExchangeConfig:
    """Конфигурация биржи."""
    enabled: bool = True
    testnet: bool = False


class ExchangeManager:
    """
    Менеджер для управления подключениями к нескольким биржам.
    
    Позволяет:
    - Подключаться к нескольким биржам одновременно
    - Рассылать подписки на все активные биржи
    - Получать унифицированные тиковые данные от всех бирж
    - Мониторить статус подключений
    """
    
    def __init__(self):
        self._connectors: Dict[str, BaseWebSocketConnector] = {}
        self._callbacks: List[Callable[[TickData], Any]] = []
        self._running = False
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=100000)
        
        # Инициализация коннекторов
        self._init_connectors()
    
    def _init_connectors(self) -> None:
        """Инициализация всех коннекторов."""
        self._connectors['binance'] = BinanceConnector()
        self._connectors['bybit'] = BybitConnector(testnet=False)
        self._connectors['okx'] = OKXConnector(testnet=False)
        
        # Добавляем общий колбэк для пересылки в очередь
        for connector in self._connectors.values():
            connector.add_callback(self._on_tick)
    
    def _on_tick(self, tick_data: TickData) -> None:
        """Обработчик тиковых данных от всех коннекторов."""
        try:
            self._message_queue.put_nowait(tick_data)
        except asyncio.QueueFull:
            logger.warning("Message queue is full, dropping tick")
    
    def add_callback(self, callback: Callable[[TickData], Any]) -> None:
        """Добавление глобального колбэка для обработки тиков."""
        self._callbacks.append(callback)
    
    async def connect_all(self) -> None:
        """Подключение ко всем биржам."""
        self._running = True
        
        tasks = []
        for name, connector in self._connectors.items():
            logger.info(f"Connecting to {name}...")
            tasks.append(self._connect_exchange(name, connector))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def connect_exchange(self, exchange: str) -> None:
        """Подключение к конкретной бирже."""
        if exchange not in self._connectors:
            raise ValueError(f"Unknown exchange: {exchange}")
        
        await self._connect_exchange(exchange, self._connectors[exchange])
    
    async def _connect_exchange(self, name: str, connector: BaseWebSocketConnector) -> None:
        """Внутренний метод подключения."""
        try:
            await connector.connect()
            logger.info(f"[{name}] Connected successfully")
        except Exception as e:
            logger.error(f"[{name}] Connection failed: {e}")
    
    async def disconnect_all(self) -> None:
        """Отключение от всех бирж."""
        self._running = False
        
        tasks = []
        for name, connector in self._connectors.items():
            tasks.append(self._disconnect_exchange(name, connector))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def disconnect_exchange(self, exchange: str) -> None:
        """Отключение от конкретной биржи."""
        if exchange not in self._connectors:
            return
        
        await self._disconnect_exchange(exchange, self._connectors[exchange])
    
    async def _disconnect_exchange(self, name: str, connector: BaseWebSocketConnector) -> None:
        """Внутренний метод отключения."""
        try:
            await connector.disconnect()
            logger.info(f"[{name}] Disconnected")
        except Exception as e:
            logger.error(f"[{name}] Disconnect error: {e}")
    
    async def subscribe_all(self, symbols: List[str]) -> None:
        """
        Подписка на символы на всех биржах.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE
        """
        tasks = []
        for name, connector in self._connectors.items():
            if connector.is_connected:
                tasks.append(self._subscribe_exchange(name, connector, symbols))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def subscribe_exchange(self, exchange: str, symbols: List[str]) -> None:
        """Подписка на символы на конкретной бирже."""
        if exchange not in self._connectors:
            raise ValueError(f"Unknown exchange: {exchange}")
        
        connector = self._connectors[exchange]
        if connector.is_connected:
            await connector.subscribe(symbols)
    
    async def _subscribe_exchange(
        self, name: str, connector: BaseWebSocketConnector, symbols: List[str]
    ) -> None:
        """Внутренний метод подписки."""
        try:
            await connector.subscribe(symbols)
            logger.info(f"[{name}] Subscribed to {len(symbols)} symbols")
        except Exception as e:
            logger.error(f"[{name}] Subscribe error: {e}")
    
    async def unsubscribe_all(self, symbols: List[str]) -> None:
        """Отписка от символов на всех биржах."""
        tasks = []
        for name, connector in self._connectors.items():
            if connector.is_connected:
                tasks.append(self._unsubscribe_exchange(name, connector, symbols))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def unsubscribe_exchange(self, exchange: str, symbols: List[str]) -> None:
        """Отписка от символов на конкретной бирже."""
        if exchange not in self._connectors:
            return
        
        connector = self._connectors[exchange]
        if connector.is_connected:
            await connector.unsubscribe(symbols)
    
    async def _unsubscribe_exchange(
        self, name: str, connector: BaseWebSocketConnector, symbols: List[str]
    ) -> None:
        """Внутренний метод отписки."""
        try:
            await connector.unsubscribe(symbols)
            logger.info(f"[{name}] Unsubscribed from {len(symbols)} symbols")
        except Exception as e:
            logger.error(f"[{name}] Unsubscribe error: {e}")
    
    def get_stats(self) -> Dict[str, ConnectionStats]:
        """Получение статистики по всем биржам."""
        return {
            name: connector.stats
            for name, connector in self._connectors.items()
        }
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Получение статуса подключений."""
        return {
            name: connector.is_connected
            for name, connector in self._connectors.items()
        }
    
    async def get_next_tick(self) -> TickData:
        """Получение следующего тика из очереди."""
        return await self._message_queue.get()
    
    def get_queued_ticks(self, max_count: int = 1000) -> List[TickData]:
        """Получение накопленных тиков из очереди."""
        ticks = []
        while len(ticks) < max_count and not self._message_queue.empty():
            ticks.append(self._message_queue.get_nowait())
        return ticks
    
    def get_connector(self, exchange: str) -> Optional[BaseWebSocketConnector]:
        """Получение коннектора для конкретной биржи."""
        return self._connectors.get(exchange)
    
    @property
    def exchanges(self) -> List[str]:
        """Список доступных бирж."""
        return list(self._connectors.keys())
