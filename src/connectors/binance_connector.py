"""
WebSocket коннектор для Binance.
Реализация адаптера для Binance WebSocket API.
"""

import asyncio
import json
import logging
from typing import Optional, List
import websockets

from src.connectors.base_connector import BaseWebSocketConnector, WebSocketConfig
from src.models.data_models import TickData


logger = logging.getLogger(__name__)


class BinanceConnector(BaseWebSocketConnector):
    """
    WebSocket коннектор для Binance.
    
    Документация: https://binance-docs.github.io/apidocs/
    """
    
    def __init__(self):
        config = WebSocketConfig(
            url="wss://stream.binance.com:9443/ws",
            ping_interval=30,
            ping_timeout=10,
            reconnect_delay_base=1.0,
            reconnect_delay_max=60.0,
            message_queue_size=10000
        )
        super().__init__(config, exchange_name="binance")
        self._subscribed_symbols: List[str] = []
        self._stream_names: List[str] = []
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Нормализация символа Binance в формат BASE/QUOTE.
        Пример: BTCUSDT -> BTC/USDT
        """
        symbol = symbol.upper()
        # Основные котируемые валюты
        quote_currencies = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB']
        
        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
        
        # Если не найдено совпадение, пытаемся разделить по последним 3-4 символам
        if len(symbol) > 6:
            return f"{symbol[:-4]}/{symbol[-4:]}"
        return f"{symbol[:-3]}/{symbol[-3:]}"
    
    async def _create_connection(self):
        """Создание WebSocket подключения к Binance."""
        return await websockets.connect(
            self.config.url,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout
        )
    
    async def _parse_message(self, message: str, receive_time: float) -> Optional[TickData]:
        """Парсинг сообщения Binance в унифицированный формат."""
        try:
            data = json.loads(message)
            
            # Обработка trade сообщений
            if 'e' in data and data['e'] == 'trade':
                symbol = self._normalize_symbol(data['s'])
                return TickData(
                    exchange='binance',
                    symbol=symbol,
                    timestamp_ms=data['T'],
                    bid=float(data.get('b', 0)),
                    ask=float(data.get('a', 0)),
                    last=float(data['p']),
                    volume=float(data['q']),
                    is_interpolated=False
                )
            
            # Обработка ticker сообщений (24hr mini ticker)
            elif 'e' in data and data['e'] == '24hrMiniTicker':
                symbol = self._normalize_symbol(data['s'])
                return TickData(
                    exchange='binance',
                    symbol=symbol,
                    timestamp_ms=int(data.get('E', receive_time)),
                    bid=float(data.get('b', 0)),
                    ask=float(data.get('a', 0)),
                    last=float(data.get('c', 0)),
                    volume=float(data.get('v', 0)),
                    is_interpolated=False
                )
            
            # Обработка bookTicker (лучшие bid/ask)
            elif 'u' in data and 's' in data:
                symbol = self._normalize_symbol(data['s'])
                return TickData(
                    exchange='binance',
                    symbol=symbol,
                    timestamp_ms=int(data.get('E', receive_time)),
                    bid=float(data.get('b', 0)),
                    ask=float(data.get('a', 0)),
                    last=float(data.get('b', 0)),  # Используем bid как last
                    volume=0.0,
                    is_interpolated=False
                )
            
            # Подтверждение подписки
            elif 'result' in data:
                logger.debug(f"[Binance] Subscription result: {data}")
                return None
            
            else:
                logger.debug(f"[Binance] Unknown message type: {data}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"[Binance] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[Binance] Parse error: {e}")
            return None
    
    async def subscribe(self, symbols: List[str]) -> None:
        """
        Подписка на символы Binance.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE (например, ['BTC/USDT', 'ETH/USDT'])
        """
        if not self.is_connected:
            logger.warning("[Binance] Cannot subscribe, not connected")
            return
        
        # Конвертация в формат Binance и создание stream names
        stream_names = []
        for symbol in symbols:
            # Конвертация из BASE/QUOTE в формат Binance
            binance_symbol = symbol.replace('/', '').upper()
            self._subscribed_symbols.append(symbol)
            
            # Создаем stream для trade данных
            stream_names.append(f"{binance_symbol.lower()}@trade")
            # Также можно подписаться на bookTicker для лучших bid/ask
            stream_names.append(f"{binance_symbol.lower()}@bookTicker")
        
        # Убираем дубликаты
        stream_names = list(set(stream_names))
        self._stream_names = stream_names
        
        # Отправка запроса на подписку
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": stream_names,
            "id": 1
        }
        
        await self._ws.send(json.dumps(subscribe_msg))
        logger.info(f"[Binance] Subscribed to {len(symbols)} symbols")
    
    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Отписка от символов.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE
        """
        if not self.is_connected:
            return
        
        # Конвертация в формат Binance
        stream_names = []
        for symbol in symbols:
            binance_symbol = symbol.replace('/', '').upper()
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.remove(symbol)
            stream_names.append(f"{binance_symbol.lower()}@trade")
            stream_names.append(f"{binance_symbol.lower()}@bookTicker")
        
        # Отправка запроса на отписку
        unsubscribe_msg = {
            "method": "UNSUBSCRIBE",
            "params": stream_names,
            "id": 2
        }
        
        await self._ws.send(json.dumps(unsubscribe_msg))
        logger.info(f"[Binance] Unsubscribed from {len(symbols)} symbols")
