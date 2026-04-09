"""
Базовый класс для WebSocket коннекторов бирж.
Унифицированный интерфейс для всех адаптеров.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any, List
from collections import deque
from dataclasses import dataclass

from src.models.data_models import TickData, ConnectionStats


logger = logging.getLogger(__name__)


@dataclass
class WebSocketConfig:
    """Конфигурация WebSocket подключения."""
    url: str
    ping_interval: int = 30  # секунды
    ping_timeout: int = 10  # секунды
    reconnect_delay_base: float = 1.0  # базовая задержка для exponential backoff
    reconnect_delay_max: float = 60.0  # максимальная задержка
    message_queue_size: int = 10000  # размер буфера очереди сообщений


class BaseWebSocketConnector(ABC):
    """
    Базовый класс для WebSocket коннекторов.
    
    Реализует:
    - Автоматический реконнект с exponential backoff
    - Heartbeat-пинг
    - Логирование задержек
    - Очередь сообщений с буфером
    """
    
    def __init__(self, config: WebSocketConfig, exchange_name: str):
        self.config = config
        self.exchange_name = exchange_name
        self._ws = None
        self._connected = False
        self._running = False
        self._reconnect_count = 0
        self._message_queue: deque = deque(maxlen=config.message_queue_size)
        self._callbacks: List[Callable[[TickData], Any]] = []
        self._stats = ConnectionStats(exchange=exchange_name)
        self._last_message_time: Optional[int] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        
    @property
    def stats(self) -> ConnectionStats:
        """Получение статистики подключения."""
        self._stats.connected = self._connected
        self._stats.reconnect_count = self._reconnect_count
        self._stats.last_message_time = self._last_message_time
        self._stats.messages_received = len(self._message_queue)
        return self._stats
    
    @property
    def is_connected(self) -> bool:
        """Проверка статуса подключения."""
        return self._connected
    
    def add_callback(self, callback: Callable[[TickData], Any]) -> None:
        """Добавление колбэка для обработки тиковых данных."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[TickData], Any]) -> None:
        """Удаление колбэка."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def connect(self) -> None:
        """Подключение к WebSocket."""
        self._running = True
        await self._connect_with_retry()
    
    async def disconnect(self) -> None:
        """Отключение от WebSocket."""
        self._running = False
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
        self._connected = False
        logger.info(f"[{self.exchange_name}] Disconnected")
    
    async def _connect_with_retry(self) -> None:
        """Подключение с повторными попытками (exponential backoff)."""
        delay = self.config.reconnect_delay_base
        
        while self._running and not self._connected:
            try:
                logger.info(f"[{self.exchange_name}] Connecting to {self.config.url}...")
                self._ws = await self._create_connection()
                self._connected = True
                self._reconnect_count = 0
                logger.info(f"[{self.exchange_name}] Connected successfully")
                
                # Запуск задач
                self._ping_task = asyncio.create_task(self._ping_loop())
                self._receive_task = asyncio.create_task(self._receive_loop())
                
            except Exception as e:
                self._connected = False
                self._stats.errors_count += 1
                logger.error(
                    f"[{self.exchange_name}] Connection failed: {e}. "
                    f"Retrying in {delay:.2f}s (attempt {self._reconnect_count + 1})"
                )
                self._reconnect_count += 1
                
                if self._running:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.config.reconnect_delay_max)
    
    async def _ping_loop(self) -> None:
        """Цикл отправки heartbeat-пингов."""
        while self._running and self._connected:
            try:
                await asyncio.sleep(self.config.ping_interval)
                if self._ws and self._connected:
                    start_time = time.time()
                    pong_waiter = await self._ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=self.config.ping_timeout)
                    latency = (time.time() - start_time) * 1000  # ms
                    self._stats.latency_ms = latency
                    logger.debug(f"[{self.exchange_name}] Ping latency: {latency:.2f}ms")
            except asyncio.TimeoutError:
                logger.warning(f"[{self.exchange_name}] Ping timeout, reconnecting...")
                self._connected = False
                if self._ws:
                    await self._ws.close()
            except Exception as e:
                logger.error(f"[{self.exchange_name}] Ping error: {e}")
                self._connected = False
    
    async def _receive_loop(self) -> None:
        """Цикл получения сообщений."""
        while self._running and self._connected and self._ws:
            try:
                message = await self._ws.recv()
                receive_time = time.time() * 1000  # ms
                
                # Парсинг сообщения
                tick_data = await self._parse_message(message, receive_time)
                
                if tick_data:
                    # Логирование задержки обработки
                    msg_latency = receive_time - tick_data.timestamp_ms
                    if msg_latency > 1000:  # больше 1 секунды
                        logger.warning(
                            f"[{self.exchange_name}] High message latency: "
                            f"{msg_latency:.2f}ms for {tick_data.symbol}"
                        )
                    
                    # Добавление в очередь
                    self._message_queue.append(tick_data)
                    self._last_message_time = tick_data.timestamp_ms
                    
                    # Вызов колбэков
                    for callback in self._callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(tick_data)
                            else:
                                callback(tick_data)
                        except Exception as e:
                            logger.error(f"[{self.exchange_name}] Callback error: {e}")
                            
            except Exception as e:
                if self._running:
                    logger.error(f"[{self.exchange_name}] Receive error: {e}")
                    self._connected = False
    
    @abstractmethod
    async def _create_connection(self):
        """Создание WebSocket подключения. Должен быть реализован в наследнике."""
        pass
    
    @abstractmethod
    async def _parse_message(self, message: str, receive_time: float) -> Optional[TickData]:
        """
        Парсинг сообщения биржи в унифицированный формат.
        Должен быть реализован в наследнике.
        """
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> None:
        """
        Подписка на символы.
        Должен быть реализован в наследнике.
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Отписка от символов.
        Должен быть реализован в наследнике.
        """
        pass
    
    def get_queued_messages(self) -> List[TickData]:
        """Получение всех сообщений из очереди."""
        messages = list(self._message_queue)
        self._message_queue.clear()
        return messages
