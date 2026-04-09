"""
WebSocket коннектор для OKX.
Реализация адаптера для OKX WebSocket API.
"""

import asyncio
import json
import logging
import time
from typing import Optional, List
import websockets
import hmac
import base64

from src.connectors.base_connector import BaseWebSocketConnector, WebSocketConfig
from src.models.data_models import TickData


logger = logging.getLogger(__name__)


class OKXConnector(BaseWebSocketConnector):
    """
    WebSocket коннектор для OKX.
    
    Документация: https://www.okx.com/docs-v5/
    """
    
    def __init__(self, testnet: bool = False):
        url = "wss://ws.okx.com:8443/ws/v5/public"
        if testnet:
            url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        
        config = WebSocketConfig(
            url=url,
            ping_interval=30,
            ping_timeout=10,
            reconnect_delay_base=1.0,
            reconnect_delay_max=60.0,
            message_queue_size=10000
        )
        super().__init__(config, exchange_name="okx")
        self._subscribed_symbols: List[str] = []
        self._testnet = testnet
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Нормализация символа OKX в формат BASE/QUOTE.
        Пример: BTC-USDT -> BTC/USDT
        """
        symbol = symbol.upper()
        # OKX использует формат с дефисом
        return symbol.replace('-', '/')
    
    def _denormalize_symbol(self, symbol: str) -> str:
        """
        Конвертация из нормализованного формата в формат OKX.
        Пример: BTC/USDT -> BTC-USDT
        """
        return symbol.replace('/', '-').upper()
    
    async def _create_connection(self):
        """Создание WebSocket подключения к OKX."""
        return await websockets.connect(
            self.config.url,
            ping_interval=self.config.ping_interval,
            ping_timeout=self.config.ping_timeout
        )
    
    async def _parse_message(self, message: str, receive_time: float) -> Optional[TickData]:
        """Парсинг сообщения OKX в унифицированный формат."""
        try:
            data = json.loads(message)
            
            # Обработка данных из каналов
            if 'arg' in data and 'data' in data:
                arg = data.get('arg', {})
                channel = arg.get('channel', '')
                
                # Получаем данные (может быть список или dict)
                raw_data = data.get('data', [])
                if isinstance(raw_data, list) and len(raw_data) > 0:
                    item = raw_data[0]
                else:
                    item = raw_data
                
                symbol_raw = arg.get('instId', item.get('instId', ''))
                symbol = self._normalize_symbol(symbol_raw)
                
                # Trades канал
                if channel == 'trades':
                    return TickData(
                        exchange='okx',
                        symbol=symbol,
                        timestamp_ms=int(item.get('ts', receive_time)),
                        bid=0.0,
                        ask=0.0,
                        last=float(item.get('px', 0)),
                        volume=float(item.get('sz', 0)),
                        is_interpolated=False
                    )
                
                # Tickers канал
                elif channel == 'tickers':
                    return TickData(
                        exchange='okx',
                        symbol=symbol,
                        timestamp_ms=int(item.get('ts', receive_time)),
                        bid=float(item.get('bidPx', 0) or 0),
                        ask=float(item.get('askPx', 0) or 0),
                        last=float(item.get('last', 0) or 0),
                        volume=float(item.get('vol24h', 0) or 0),
                        is_interpolated=False
                    )
                
                # BBO-TBT канал (лучшие bid/ask)
                elif channel == 'bbo-tbt' or channel == 'books':
                    bids = item.get('bids', [])
                    asks = item.get('asks', [])
                    
                    bid = float(bids[0][0]) if bids else 0.0
                    ask = float(asks[0][0]) if asks else 0.0
                    
                    return TickData(
                        exchange='okx',
                        symbol=symbol,
                        timestamp_ms=int(item.get('ts', receive_time)),
                        bid=bid,
                        ask=ask,
                        last=bid,  # Используем bid как last
                        volume=0.0,
                        is_interpolated=False
                    )
                
                # Книги ордеров
                elif 'books' in channel:
                    bids = item.get('bids', [])
                    asks = item.get('asks', [])
                    
                    bid = float(bids[0][0]) if bids else 0.0
                    ask = float(asks[0][0]) if asks else 0.0
                    
                    return TickData(
                        exchange='okx',
                        symbol=symbol,
                        timestamp_ms=int(item.get('ts', receive_time)),
                        bid=bid,
                        ask=ask,
                        last=bid,
                        volume=0.0,
                        is_interpolated=False
                    )
            
            # Подтверждение подписки
            elif 'event' in data:
                event = data['event']
                
                if event == 'subscribe':
                    logger.debug(f"[OKX] Subscription confirmed: {data}")
                    return None
                
                elif event == 'error':
                    logger.error(f"[OKX] Error: {data}")
                    return None
                
                elif event == 'login':
                    logger.debug(f"[OKX] Login result: {data}")
                    return None
                
                # Ping от сервера (требуется ответ pong)
                elif event == 'ping':
                    if self._ws:
                        await self._ws.send(json.dumps({"event": "pong"}))
                    return None
            
            else:
                logger.debug(f"[OKX] Unknown message type: {data}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"[OKX] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[OKX] Parse error: {e}")
            return None
    
    async def subscribe(self, symbols: List[str]) -> None:
        """
        Подписка на символы OKX.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE (например, ['BTC/USDT', 'ETH/USDT'])
        """
        if not self.is_connected:
            logger.warning("[OKX] Cannot subscribe, not connected")
            return
        
        # Создаем список аргументов для подписки
        args = []
        for symbol in symbols:
            # Конвертация в формат OKX
            okx_symbol = self._denormalize_symbol(symbol)
            self._subscribed_symbols.append(symbol)
            
            # Подписка на trades канал
            args.append({
                "channel": "trades",
                "instId": okx_symbol
            })
            
            # Подписка на tickers канал
            args.append({
                "channel": "tickers",
                "instId": okx_symbol
            })
        
        # Отправка запроса на подписку
        subscribe_msg = {
            "op": "subscribe",
            "args": args
        }
        
        await self._ws.send(json.dumps(subscribe_msg))
        logger.info(f"[OKX] Subscribed to {len(symbols)} symbols")
    
    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        Отписка от символов.
        
        Args:
            symbols: Список символов в формате BASE/QUOTE
        """
        if not self.is_connected:
            return
        
        # Создаем список аргументов для отписки
        args = []
        for symbol in symbols:
            okx_symbol = self._denormalize_symbol(symbol)
            if symbol in self._subscribed_symbols:
                self._subscribed_symbols.remove(symbol)
            
            args.append({
                "channel": "trades",
                "instId": okx_symbol
            })
            args.append({
                "channel": "tickers",
                "instId": okx_symbol
            })
        
        # Отправка запроса на отписку
        unsubscribe_msg = {
            "op": "unsubscribe",
            "args": args
        }
        
        await self._ws.send(json.dumps(unsubscribe_msg))
        logger.info(f"[OKX] Unsubscribed from {len(symbols)} symbols")
