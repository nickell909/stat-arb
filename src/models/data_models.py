"""
Модели данных для приложения крипто-арбитража.
Единая схема данных для всех бирж.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Exchange(Enum):
    """Перечисление поддерживаемых бирж."""
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"


class Timeframe(Enum):
    """Поддерживаемые таймфреймы."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


@dataclass
class TickData:
    """Тиковые данные (real-time)."""
    exchange: str
    symbol: str  # Нормализованный формат BASE/QUOTE
    timestamp_ms: int
    bid: float
    ask: float
    last: float
    volume: float
    is_interpolated: bool = False

    @property
    def timestamp(self) -> datetime:
        """Конвертация timestamp в datetime."""
        return datetime.fromtimestamp(self.timestamp_ms / 1000)


@dataclass
class OHLCV:
    """OHLCV свеча."""
    exchange: str
    symbol: str
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    is_interpolated: bool = False

    @property
    def timestamp(self) -> datetime:
        """Конвертация timestamp в datetime."""
        return datetime.fromtimestamp(self.timestamp_ms / 1000)

    def to_dict(self) -> dict:
        """Конвертация в словарь."""
        return {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'timestamp_ms': self.timestamp_ms,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'quote_volume': self.quote_volume,
            'is_interpolated': self.is_interpolated
        }


@dataclass
class Spread:
    """Спред между двумя инструментами."""
    name: str
    leg1_symbol: str
    leg1_exchange: str
    leg2_symbol: str
    leg2_exchange: str
    leg1_ratio: float = 1.0
    leg2_ratio: float = 1.0
    
    # Статистика
    mean: Optional[float] = None
    std: Optional[float] = None
    z_score: Optional[float] = None

    def calculate_spread(self, price1: float, price2: float) -> float:
        """Вычисление значения спреда."""
        return self.leg1_ratio * price1 - self.leg2_ratio * price2

    def calculate_z_score(self, value: float) -> float:
        """Вычисление Z-score для текущего значения спреда."""
        if self.std is None or self.std == 0:
            return 0.0
        return (value - self.mean) / self.std


@dataclass
class ConnectionStats:
    """Статистика подключения к бирже."""
    exchange: str
    connected: bool = False
    last_message_time: Optional[int] = None
    latency_ms: float = 0.0
    reconnect_count: int = 0
    messages_received: int = 0
    errors_count: int = 0
