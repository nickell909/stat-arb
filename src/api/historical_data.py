"""
REST API клиент для загрузки исторических данных OHLCV.
Поддержка Binance, Bybit, OKX.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import httpx

from src.models.data_models import OHLCV, Timeframe, Exchange


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Конфигурация rate limits."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    burst_size: int = 5


class HistoricalDataClient:
    """
    Клиент для загрузки исторических OHLCV данных.
    
    Поддерживает:
    - Загрузку свечей с нескольких бирж
    - Умную загрузку (только недостающие данные)
    - Параллельную загрузку с соблюдением rate limits
    """
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        self._rate_limiter: Dict[str, asyncio.Semaphore] = {}
        self._last_request_time: Dict[str, float] = {}
        
        # Rate limits для каждой биржи
        self._rate_limits = {
            'binance': RateLimitConfig(requests_per_second=10, requests_per_minute=1200),
            'bybit': RateLimitConfig(requests_per_second=10, requests_per_minute=600),
            'okx': RateLimitConfig(requests_per_second=5, requests_per_minute=300),
        }
    
    async def close(self) -> None:
        """Закрытие HTTP клиента."""
        await self._client.aclose()
    
    async def _respect_rate_limit(self, exchange: str) -> None:
        """Соблюдение rate limits биржи."""
        config = self._rate_limits.get(exchange, RateLimitConfig())
        now = asyncio.get_event_loop().time()
        
        last_time = self._last_request_time.get(exchange, 0)
        min_interval = 1.0 / config.requests_per_second
        
        if now - last_time < min_interval:
            await asyncio.sleep(min_interval - (now - last_time))
        
        self._last_request_time[exchange] = asyncio.get_event_loop().time()
    
    def _timeframe_to_interval(self, timeframe: Timeframe) -> str:
        """Конвертация таймфрейма в интервал для API."""
        mapping = {
            Timeframe.M1: '1m',
            Timeframe.M5: '5m',
            Timeframe.M15: '15m',
            Timeframe.H1: '1h',
            Timeframe.H4: '4h',
            Timeframe.D1: '1d',
        }
        return mapping.get(timeframe, '1m')
    
    async def fetch_ohlcv(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000
    ) -> List[OHLCV]:
        """
        Загрузка OHLCV данных с указанной биржи.
        
        Args:
            exchange: Название биржи (binance, bybit, okx)
            symbol: Символ в формате BASE/QUOTE
            timeframe: Таймфрейм
            start_date: Дата начала
            end_date: Дата конца
            limit: Максимальное количество свечей за запрос
        
        Returns:
            Список OHLCV свечей
        """
        if exchange == 'binance':
            return await self._fetch_binance(symbol, timeframe, start_date, end_date, limit)
        elif exchange == 'bybit':
            return await self._fetch_bybit(symbol, timeframe, start_date, end_date, limit)
        elif exchange == 'okx':
            return await self._fetch_okx(symbol, timeframe, start_date, end_date, limit)
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")
    
    async def _fetch_binance(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
        limit: int
    ) -> List[OHLCV]:
        """Загрузка данных с Binance."""
        candles = []
        interval = self._timeframe_to_interval(timeframe)
        binance_symbol = symbol.replace('/', '')
        
        current_start = start_date
        while current_start < end_date:
            await self._respect_rate_limit('binance')
            
            start_ms = int(current_start.timestamp() * 1000)
            
            try:
                response = await self._client.get(
                    'https://api.binance.com/api/v3/klines',
                    params={
                        'symbol': binance_symbol,
                        'interval': interval,
                        'startTime': start_ms,
                        'limit': limit
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                for candle in data:
                    candle_time = datetime.fromtimestamp(candle[0] / 1000)
                    if candle_time > end_date:
                        break
                    
                    ohlcv = OHLCV(
                        exchange='binance',
                        symbol=symbol,
                        timestamp_ms=candle[0],
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=float(candle[5]),
                        quote_volume=float(candle[7]),
                        is_interpolated=False
                    )
                    candles.append(ohlcv)
                
                # Переход к следующему периоду
                if len(data) < limit:
                    break
                current_start = datetime.fromtimestamp(data[-1][0] / 1000)
                
            except Exception as e:
                logger.error(f"Binance fetch error: {e}")
                break
        
        return candles
    
    async def _fetch_bybit(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
        limit: int
    ) -> List[OHLCV]:
        """Загрузка данных с Bybit."""
        candles = []
        interval = self._timeframe_to_interval(timeframe)
        bybit_symbol = symbol.replace('/', '')
        
        current_start = start_date
        while current_start < end_date:
            await self._respect_rate_limit('bybit')
            
            start_ms = int(current_start.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)
            
            try:
                response = await self._client.get(
                    'https://api.bybit.com/v5/market/kline',
                    params={
                        'category': 'spot',
                        'symbol': bybit_symbol,
                        'interval': interval,
                        'start': start_ms,
                        'end': end_ms,
                        'limit': limit
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get('retCode') != 0:
                    logger.error(f"Bybit API error: {result}")
                    break
                
                data = result.get('result', {}).get('list', [])
                
                if not data:
                    break
                
                for candle in reversed(data):  # Bybit возвращает в обратном порядке
                    candle_time = datetime.fromtimestamp(int(candle[0]) / 1000)
                    if candle_time > end_date:
                        continue
                    if candle_time < start_date:
                        break
                    
                    ohlcv = OHLCV(
                        exchange='bybit',
                        symbol=symbol,
                        timestamp_ms=int(candle[0]),
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=float(candle[5]),
                        quote_volume=float(candle[6]),
                        is_interpolated=False
                    )
                    candles.append(ohlcv)
                
                if len(data) < limit:
                    break
                current_start = datetime.fromtimestamp(int(data[-1][0]) / 1000)
                
            except Exception as e:
                logger.error(f"Bybit fetch error: {e}")
                break
        
        return sorted(candles, key=lambda x: x.timestamp_ms)
    
    async def _fetch_okx(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
        limit: int
    ) -> List[OHLCV]:
        """Загрузка данных с OKX."""
        candles = []
        interval = self._timeframe_to_interval(timeframe)
        okx_symbol = symbol.replace('/', '-')
        
        current_start = start_date
        while current_start < end_date:
            await self._respect_rate_limit('okx')
            
            # OKX использует after/before параметры
            before = int(current_start.timestamp() * 1000)
            
            try:
                response = await self._client.get(
                    'https://www.okx.com/api/v5/market/candles',
                    params={
                        'instId': okx_symbol,
                        'bar': interval,
                        'before': before,
                        'limit': limit
                    },
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get('code') != '0':
                    logger.error(f"OKX API error: {result}")
                    break
                
                data = result.get('data', [])
                
                if not data:
                    break
                
                for candle in reversed(data):  # OKX возвращает в обратном порядке
                    candle_time = datetime.fromtimestamp(int(candle[0]) / 1000)
                    if candle_time > end_date:
                        continue
                    if candle_time < start_date:
                        break
                    
                    ohlcv = OHLCV(
                        exchange='okx',
                        symbol=symbol,
                        timestamp_ms=int(candle[0]),
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=float(candle[5]),
                        quote_volume=float(candle[6]),
                        is_interpolated=False
                    )
                    candles.append(ohlcv)
                
                if len(data) < limit:
                    break
                current_start = datetime.fromtimestamp(int(data[-1][0]) / 1000)
                
            except Exception as e:
                logger.error(f"OKX fetch error: {e}")
                break
        
        return sorted(candles, key=lambda x: x.timestamp_ms)
    
    async def fetch_parallel(
        self,
        requests: List[Tuple[str, str, Timeframe, datetime, datetime]]
    ) -> Dict[str, List[OHLCV]]:
        """
        Параллельная загрузка данных для нескольких запросов.
        
        Args:
            requests: Список кортежей (exchange, symbol, timeframe, start_date, end_date)
        
        Returns:
            Словарь {key: candles} где key = "{exchange}:{symbol}:{timeframe}"
        """
        async def fetch_with_key(req):
            exchange, symbol, timeframe, start, end = req
            key = f"{exchange}:{symbol}:{timeframe.value}"
            candles = await self.fetch_ohlcv(exchange, symbol, timeframe, start, end)
            return key, candles
        
        tasks = [fetch_with_key(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel fetch error: {result}")
            else:
                key, candles = result
                output[key] = candles
        
        return output
