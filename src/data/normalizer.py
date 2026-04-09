"""
Модуль нормализации и обработки данных.
Обработка выбросов, заполнение пропусков, валидация.
"""

import logging
from typing import List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.models.data_models import OHLCV, TickData


logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    Нормализация и обработка данных.
    
    Функции:
    - Обнаружение и обработка выбросов
    - Заполнение пропусков (forward-fill)
    - Валидация данных
    - Конвертация между форматами
    """
    
    def __init__(self, outlier_threshold_pct: float = 5.0):
        """
        Args:
            outlier_threshold_pct: Порог для обнаружения выбросов (в процентах)
        """
        self.outlier_threshold_pct = outlier_threshold_pct
    
    def normalize_tick_data(
        self,
        exchange: str,
        symbol: str,
        raw_data: dict,
        timestamp_ms: int
    ) -> TickData:
        """
        Нормализация тиковых данных к единой схеме.
        
        Args:
            exchange: Название биржи
            symbol: Символ в формате BASE/QUOTE
            raw_data: Сырые данные от биржи
            timestamp_ms: Timestamp в миллисекундах
        
        Returns:
            Нормализованные TickData
        """
        return TickData(
            exchange=exchange,
            symbol=symbol,
            timestamp_ms=timestamp_ms,
            bid=float(raw_data.get('bid', 0)),
            ask=float(raw_data.get('ask', 0)),
            last=float(raw_data.get('last', 0)),
            volume=float(raw_data.get('volume', 0)),
            is_interpolated=False
        )
    
    def detect_outliers(self, prices: List[float]) -> List[Tuple[int, float, float]]:
        """
        Обнаружение выбросов в последовательности цен.
        
        Args:
            prices: Список цен
        
        Returns:
            Список кортежей (индекс, цена, предыдущая_цена) для выбросов
        """
        outliers = []
        
        for i in range(1, len(prices)):
            prev_price = prices[i - 1]
            curr_price = prices[i]
            
            if prev_price == 0:
                continue
            
            change_pct = abs((curr_price - prev_price) / prev_price) * 100
            
            if change_pct > self.outlier_threshold_pct:
                outliers.append((i, curr_price, prev_price))
                logger.warning(
                    f"Outlier detected at index {i}: "
                    f"price {curr_price} differs by {change_pct:.2f}% "
                    f"from previous {prev_price}"
                )
        
        return outliers
    
    def remove_outliers(
        self,
        candles: List[OHLCV],
        replace_with_previous: bool = True
    ) -> List[OHLCV]:
        """
        Удаление или замена выбросов в OHLCV данных.
        
        Args:
            candles: Список OHLCV свечей
            replace_with_previous: Заменять выбросы предыдущими значениями
        
        Returns:
            Очищенный список свечей
        """
        if len(candles) < 2:
            return candles
        
        cleaned = [candles[0]]
        
        for i in range(1, len(candles)):
            prev_close = cleaned[-1].close
            curr_open = candles[i].open
            curr_close = candles[i].close
            
            # Проверка на выброс
            is_outlier = False
            if prev_close > 0:
                open_change = abs((curr_open - prev_close) / prev_close) * 100
                if open_change > self.outlier_threshold_pct:
                    is_outlier = True
            
            if is_outlier and replace_with_previous:
                # Замена на предыдущие значения
                corrected = OHLCV(
                    exchange=candles[i].exchange,
                    symbol=candles[i].symbol,
                    timestamp_ms=candles[i].timestamp_ms,
                    open=prev_close,
                    high=prev_close,
                    low=prev_close,
                    close=prev_close,
                    volume=candles[i].volume,
                    quote_volume=candles[i].quote_volume,
                    is_interpolated=True
                )
                cleaned.append(corrected)
                logger.info(
                    f"Replaced outlier at {candles[i].timestamp} "
                    f"(exchange: {candles[i].exchange}, symbol: {candles[i].symbol})"
                )
            else:
                cleaned.append(candles[i])
        
        return cleaned
    
    def fill_gaps(
        self,
        candles: List[OHLCV],
        timeframe_minutes: int
    ) -> List[OHLCV]:
        """
        Заполнение пропусков в временных рядах через forward-fill.
        
        Args:
            candles: Список OHLCV свечей
            timeframe_minutes: Длительность таймфрейма в минутах
        
        Returns:
            Список с заполненными пропусками
        """
        if len(candles) < 2:
            return candles
        
        filled = [candles[0]]
        timeframe_delta = timeframe_minutes * 60 * 1000  # в миллисекундах
        
        for i in range(1, len(candles)):
            prev_ts = candles[i - 1].timestamp_ms
            curr_ts = candles[i].timestamp_ms
            
            # Количество пропущенных свечей
            gap = (curr_ts - prev_ts) // timeframe_delta - 1
            
            if gap > 0:
                logger.info(
                    f"Filling {gap} missing candles between "
                    f"{datetime.fromtimestamp(prev_ts/1000)} and "
                    f"{datetime.fromtimestamp(curr_ts/1000)}"
                )
                
                # Forward-fill: заполняем пропуски предыдущими значениями
                prev_candle = candles[i - 1]
                for j in range(1, gap + 1):
                    fill_ts = prev_ts + j * timeframe_delta
                    filled_candle = OHLCV(
                        exchange=prev_candle.exchange,
                        symbol=prev_candle.symbol,
                        timestamp_ms=fill_ts,
                        open=prev_candle.close,
                        high=prev_candle.close,
                        low=prev_candle.close,
                        close=prev_candle.close,
                        volume=0,
                        quote_volume=0,
                        is_interpolated=True
                    )
                    filled.append(filled_candle)
            
            filled.append(candles[i])
        
        return filled
    
    def candles_to_dataframe(self, candles: List[OHLCV]) -> pd.DataFrame:
        """
        Конвертация списка OHLCV в DataFrame.
        
        Args:
            candles: Список OHLCV свечей
        
        Returns:
            pandas DataFrame
        """
        if not candles:
            return pd.DataFrame()
        
        data = [c.to_dict() for c in candles]
        df = pd.DataFrame(data)
        
        # Конвертация timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def dataframe_to_candles(self, df: pd.DataFrame, exchange: str, symbol: str) -> List[OHLCV]:
        """
        Конвертация DataFrame в список OHLCV.
        
        Args:
            df: pandas DataFrame с колонками open, high, low, close, volume
            exchange: Название биржи
            symbol: Символ
        
        Returns:
            Список OHLCV свечей
        """
        candles = []
        
        for idx, row in df.iterrows():
            timestamp_ms = int(idx.timestamp() * 1000)
            
            candle = OHLCV(
                exchange=exchange,
                symbol=symbol,
                timestamp_ms=timestamp_ms,
                open=float(row.get('open', 0)),
                high=float(row.get('high', 0)),
                low=float(row.get('low', 0)),
                close=float(row.get('close', 0)),
                volume=float(row.get('volume', 0)),
                quote_volume=float(row.get('quote_volume', 0)),
                is_interpolated=bool(row.get('is_interpolated', False))
            )
            candles.append(candle)
        
        return candles
    
    def validate_candle(self, candle: OHLCV) -> bool:
        """
        Валидация OHLCV свечи.
        
        Args:
            candle: Свеча для проверки
        
        Returns:
            True если свеча валидна
        """
        # Проверка на положительные цены
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            return False
        
        # High >= Low
        if candle.high < candle.low:
            return False
        
        # Open и Close должны быть в диапазоне [Low, High]
        if not (candle.low <= candle.open <= candle.high):
            return False
        if not (candle.low <= candle.close <= candle.high):
            return False
        
        # Volume >= 0
        if candle.volume < 0:
            return False
        
        return True
    
    def filter_invalid_candles(self, candles: List[OHLCV]) -> List[OHLCV]:
        """
        Фильтрация невалидных свечей.
        
        Args:
            candles: Список свечей
        
        Returns:
            Список только валидных свечей
        """
        valid = []
        invalid_count = 0
        
        for candle in candles:
            if self.validate_candle(candle):
                valid.append(candle)
            else:
                invalid_count += 1
                logger.warning(
                    f"Invalid candle removed: {candle.timestamp} "
                    f"(exchange: {candle.exchange}, symbol: {candle.symbol})"
                )
        
        if invalid_count > 0:
            logger.info(f"Removed {invalid_count} invalid candles")
        
        return valid
