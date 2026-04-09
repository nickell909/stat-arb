"""
WebSocket коннектор для Bybit.
Реализация адаптера для Bybit WebSocket API.
"""

import asyncio
import json
import logging
from typing import Optional, List
import websockets

from src.connectors.base_connector import BaseWebSocketConnector, WebSocketConfig
from src.models.data_models import TickData


logger = logging.getLogger(__name__)


class BybitConnector(BaseWebSocketConnector):
    """
    WebSocket коннектор для Bybit.
    
    Документация: https://bybit-exchange.github.io/docs/v5/ws/connect
    """
    
    def __init__(self, testnet: bool = False):
        url = "wss://stream.bybit.com/v5/public/spot"
        if testnet:
            url = "wss://stream-testnet.bybit.com/v5/public/spot"
        
        config = WebSocketConfig(
            url=url,
            ping_interval=30,
            ping_timeout=10,
            reconnect_delay_base=1.0,
            reconnect_delay_max=60.0,
            message_queue_size=10000
        )
        super().__init__(config, exchange_name="bybit")
        self._subscribed_symbols: List[str] = []
        self._testnet = testnet
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Нормализация символа Bybit в формат BASE/QUOTE.
        Пример: BTCUSDT -> BTC/USDT
        """
        symbol = symbol.upper()
        # Основные котируемые валюты
        quote_currencies = ['USDT', 'USDC', 'BTC', 'ETH', 'USD']
        
        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
        
        # Если не найдено совпадение, пытаемся разделить
        if len(symbol) > 6:
            return f"{symbol[:-4]}/{symbol[-4:]}"
        return f"{symbol[:-3]}/{symbol[-3:]}"
    
    async def _create_connection(self):
        """Создание WebSocket подключения к Bybit."""
        return await websockets.connect(
            self.config.url,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout
        )
    
    async def _parse_message(self, message: str, receive_time: float) -> Optional[TickData]:
        """Парсинг сообщения Bybit в унифицированный формат."""
        try:
            data = json.loads(message)
            
            # Обработка trade сообщений
            if 'topic' in data and 'data' in data:
                topic = data['topic']
                
                # Public trade topics
                if 'publicTrade' in topic:
                    for trade in data.get('data', []):
                        symbol = self._normalize_symbol(trade.get('s', ''))
                        return TickData(
                            exchange='bybit',
                            symbol=symbol,
                            timestamp_ms=int(trade.get('T', receive_time)),
                            bid=0.0,
                            ask=0.0,
                            last=float(trade.get('p', 0)),
                            volume=float(trade.get('v', 0)),
                            is_interpolated=False
                        )
                
                # Ticker topics (kline, tickers)
                elif 'tickers' in topic or 'kline' in topic:
                    ticker_data = data.get('data', [{}])[0]
                    symbol = self._normalize_symbol(ticker_data.get('symbol', ''))
                    
                    bid = float(ticker_data.get('bid1Price', 0) or 0)
                    ask = float(ticker_data.get('ask1Price', 0) or 0)
                    last = float(ticker_data.get('lastPrice', 0) or 0)
                    volume = float(ticker_data.get('volume24h', 0) or 0)
                    
                    return TickData(
                        exchange='bybit',
                        symbol=symbol,
                        timestamp_ms=int(data.get('ts', receive_time)),
                        bid=bid,
                        ask=ask,
                        last=last,
                        volume=volume,
                        is_interpolated=False
                    )
                
                # Book snapshots (orderbook)
                elif 'orderbook' in topic:
                    book_data = data.get('data', {})
                    symbol = self._normalize_symbol(book_data.get('s', ''))
                    
                    bids = book_data.get('b', [])
                    asks = book_data.get('a', [])
                    
                    bid = float(bids[0][0]) if bids else 0.0
                    ask = float(asks[0][0]) if asks else 0.0
                    
                    return TickData(
                        exchange='bybit',
                        symbol=symbol,
                        timestamp_ms=int(data.get('ts', receive_time)),
                        bid=bid,
                        ask=ask,
                        last=bid,  # Используем bid как last
                        volume=0.0,
                        is_interpolated=False
                    )
            
            # Ping от сервера
            elif 'op' in data and data['op'] == 'ping':
                # Отправляем pong в ответ
                pong_msg = {"op": "pong"}
                if self._ws:
                    await self._ws.send(json.dumps(pong_msg))
                return None
            
            # Подтверждение подписки
            elif 'op' in data and data['op'] == 'subscribe':
                logger.debug(f"[Bybit] Subscription confirmed: {data}")
                return None
            
            # Ошибки
            elif 'op' in data and data['op'] == 'auth' or 'retMsg' in data:
                if data.get('retCode') != 0:
                    logger.error(f"[Bybit] Error: {data}")
                return None
            
            else:
                logger.debug(f"[Bybit] Unknown message type: {data}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"[Bybit] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[Bybit] Parse error: {e}")
            return None
    
    async def subscribe(self, symbols: List[str]) -> None:
        """
        Подписка на символы Bybit.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE (например, ['BTC/USDT', 'ETH/USDT'])
        """
        if not self.is_connected:
            logger.warning("[Bybit] Cannot subscribe, not connected")
            return
        
        # Создаем список topics для подписки
        topics = []
        for symbol in symbols:
            # Конвертация в формат Bybit
            bybit_symbol = symbol.replace('/', '').upper()
            self._subscribed_symbols.append(symbol)
            
            # Подписка на public trade
            topics.append(f"publicTrade.{bybit_symbol}")
            # Подписка на orderbook (лучшие bid/ask)
            topics.append(f"orderbook.1.{bybit_symbol}")
        
        # Отправка запроса на подписку
        subscribe_msg = {
            "op": "subscribe",
            "args": topics
        }
        
        await self._ws.send(json.dumps(subscribe_msg))
        logger.info(f"[Bybit] Subscribed to {len(symbols)} symbols")
    
    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Отписка от символов.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE
        """
        if not self.is_connected:
            return
        
        # Создаем список topics для отписки
        topics = []
        for symbol in symbols:
            bybit_symbol = symbol.replace('/', '').upper()
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.remove(symbol)
            topics.append(f"publicTrade.{bybit_symbol}")
            topics.append(f"orderbook.1.{bybit_symbol}")
        
        # Отправка запроса на отписку
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": topics
        }
        
        await self._ws.send(json.dumps(unsubscribe_msg))
        logger.info(f"[Bybit] Unsubscribed from {len(symbols)} symbols")
