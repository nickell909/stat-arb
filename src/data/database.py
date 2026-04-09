"""
База данных для хранения исторических данных.
Использует SQLite с SQLAlchemy.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Index
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.dialects.sqlite import insert

from src.models.data_models import OHLCV, Timeframe


logger = logging.getLogger(__name__)

Base = declarative_base()


class CandleModel(Base):
    """Модель свечи для хранения в БД."""
    
    __tablename__ = 'candles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange = Column(String(50), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp_ms = Column(Integer, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False, default=0)
    quote_volume = Column(Float, nullable=False, default=0)
    is_interpolated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_unique_candle', 'exchange', 'symbol', 'timeframe', 'timestamp_ms', unique=True),
    )
    
    def to_ohlcv(self) -> OHLCV:
        """Конвертация в OHLCV модель."""
        return OHLCV(
            exchange=self.exchange,
            symbol=self.symbol,
            timestamp_ms=self.timestamp_ms,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            quote_volume=self.quote_volume,
            is_interpolated=self.is_interpolated
        )
    
    @classmethod
    def from_ohlcv(cls, ohlcv: OHLCV, timeframe: str) -> 'CandleModel':
        """Создание из OHLCV модели."""
        return cls(
            exchange=ohlcv.exchange,
            symbol=ohlcv.symbol,
            timeframe=timeframe,
            timestamp_ms=ohlcv.timestamp_ms,
            open=ohlcv.open,
            high=ohlcv.high,
            low=ohlcv.low,
            close=ohlcv.close,
            volume=ohlcv.volume,
            quote_volume=ohlcv.quote_volume,
            is_interpolated=ohlcv.is_interpolated
        )


class DatabaseManager:
    """
    Менеджер базы данных для хранения исторических данных.
    
    Функции:
    - Сохранение OHLCV данных
    - Загрузка данных по периодам
    - Проверка наличия данных
    - Умная загрузка (только недостающее)
    """
    
    def __init__(self, db_path: str = "crypto_data.db"):
        """
        Args:
            db_path: Путь к SQLite файлу
        """
        self.db_path = db_path
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False,
            pool_pre_ping=True
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _get_session(self) -> Session:
        """Получение сессии БД."""
        return self.SessionLocal()
    
    async def save_candles(self, candles: List[OHLCV], timeframe: Timeframe) -> int:
        """
        Сохранение свечей в базу данных.
        
        Args:
            candles: Список свечей для сохранения
            timeframe: Таймфрейм
        
        Returns:
            Количество сохраненных записей
        """
        loop = asyncio.get_event_loop()
        
        def _save():
            session = self._get_session()
            try:
                models = [CandleModel.from_ohlcv(c, timeframe.value) for c in candles]
                
                # Используем upsert для избежания дубликатов
                data = []
                for m in models:
                    data.append({
                        'exchange': m.exchange,
                        'symbol': m.symbol,
                        'timeframe': m.timeframe,
                        'timestamp_ms': m.timestamp_ms,
                        'open': m.open,
                        'high': m.high,
                        'low': m.low,
                        'close': m.close,
                        'volume': m.volume,
                        'quote_volume': m.quote_volume,
                        'is_interpolated': m.is_interpolated
                    })
                
                if data:
                    stmt = insert(CandleModel).values(data)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=['exchange', 'symbol', 'timeframe', 'timestamp_ms']
                    )
                    session.execute(stmt)
                    session.commit()
                    return len(data)
                return 0
            except Exception as e:
                session.rollback()
                logger.error(f"Database save error: {e}")
                return 0
            finally:
                session.close()
        
        return await loop.run_in_executor(None, _save)
    
    async def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime
    ) -> List[OHLCV]:
        """
        Загрузка свечей из базы данных.
        
        Args:
            exchange: Название биржи
            symbol: Символ
            timeframe: Таймфрейм
            start_date: Дата начала
            end_date: Дата конца
        
        Returns:
            Список свечей
        """
        loop = asyncio.get_event_loop()
        
        def _query():
            session = self._get_session()
            try:
                start_ms = int(start_date.timestamp() * 1000)
                end_ms = int(end_date.timestamp() * 1000)
                
                results = session.query(CandleModel).filter(
                    CandleModel.exchange == exchange,
                    CandleModel.symbol == symbol,
                    CandleModel.timeframe == timeframe.value,
                    CandleModel.timestamp_ms >= start_ms,
                    CandleModel.timestamp_ms <= end_ms
                ).order_by(CandleModel.timestamp_ms).all()
                
                return [r.to_ohlcv() for r in results]
            except Exception as e:
                logger.error(f"Database query error: {e}")
                return []
            finally:
                session.close()
        
        return await loop.run_in_executor(None, _query)
    
    async def get_missing_periods(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """
        Определение периодов, для которых нет данных в БД.
        
        Args:
            exchange: Название биржи
            symbol: Символ
            timeframe: Таймфрейм
            start_date: Начало запрашиваемого периода
            end_date: Конец запрашиваемого периода
        
        Returns:
            Список кортежей (start, end) для недостающих периодов
        """
        loop = asyncio.get_event_loop()
        
        def _query():
            session = self._get_session()
            try:
                start_ms = int(start_date.timestamp() * 1000)
                end_ms = int(end_date.timestamp() * 1000)
                
                # Получаем все имеющиеся свечи за период
                results = session.query(CandleModel.timestamp_ms).filter(
                    CandleModel.exchange == exchange,
                    CandleModel.symbol == symbol,
                    CandleModel.timeframe == timeframe.value,
                    CandleModel.timestamp_ms >= start_ms,
                    CandleModel.timestamp_ms <= end_ms
                ).order_by(CandleModel.timestamp_ms).all()
                
                if not results:
                    return [(start_date, end_date)]
                
                existing_timestamps = [r[0] for r in results]
                
                # Находим пропуски
                missing = []
                timeframe_ms = self._timeframe_to_ms(timeframe)
                
                # Проверка начала периода
                if existing_timestamps[0] > start_ms:
                    missing.append((
                        start_date,
                        datetime.fromtimestamp(existing_timestamps[0] / 1000)
                    ))
                
                # Проверка пропусков между свечами
                for i in range(1, len(existing_timestamps)):
                    gap = existing_timestamps[i] - existing_timestamps[i-1]
                    if gap > timeframe_ms * 1.5:  # Допускаем небольшой разброс
                        missing.append((
                            datetime.fromtimestamp(existing_timestamps[i-1] / 1000),
                            datetime.fromtimestamp(existing_timestamps[i] / 1000)
                        ))
                
                # Проверка конца периода
                if existing_timestamps[-1] < end_ms:
                    missing.append((
                        datetime.fromtimestamp(existing_timestamps[-1] / 1000),
                        end_date
                    ))
                
                return missing
            except Exception as e:
                logger.error(f"Database query error: {e}")
                return [(start_date, end_date)]
            finally:
                session.close()
        
        return await loop.run_in_executor(None, _query)
    
    def _timeframe_to_ms(self, timeframe: Timeframe) -> int:
        """Конвертация таймфрейма в миллисекунды."""
        mapping = {
            Timeframe.M1: 60 * 1000,
            Timeframe.M5: 5 * 60 * 1000,
            Timeframe.M15: 15 * 60 * 1000,
            Timeframe.H1: 60 * 60 * 1000,
            Timeframe.H4: 4 * 60 * 60 * 1000,
            Timeframe.D1: 24 * 60 * 60 * 1000,
        }
        return mapping.get(timeframe, 60 * 1000)
    
    async def get_latest_timestamp(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe
    ) -> Optional[datetime]:
        """
        Получение последней доступной даты в БД.
        
        Args:
            exchange: Название биржи
            symbol: Символ
            timeframe: Таймфрейм
        
        Returns:
            Дата последней свечи или None
        """
        loop = asyncio.get_event_loop()
        
        def _query():
            session = self._get_session()
            try:
                result = session.query(CandleModel.timestamp_ms).filter(
                    CandleModel.exchange == exchange,
                    CandleModel.symbol == symbol,
                    CandleModel.timeframe == timeframe.value
                ).order_by(CandleModel.timestamp_ms.desc()).first()
                
                if result:
                    return datetime.fromtimestamp(result[0] / 1000)
                return None
            except Exception as e:
                logger.error(f"Database query error: {e}")
                return None
            finally:
                session.close()
        
        return await loop.run_in_executor(None, _query)
    
    async def count_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe
    ) -> int:
        """Подсчет количества свечей в БД."""
        loop = asyncio.get_event_loop()
        
        def _query():
            session = self._get_session()
            try:
                return session.query(CandleModel).filter(
                    CandleModel.exchange == exchange,
                    CandleModel.symbol == symbol,
                    CandleModel.timeframe == timeframe.value
                ).count()
            except Exception as e:
                logger.error(f"Database count error: {e}")
                return 0
            finally:
                session.close()
        
        return await loop.run_in_executor(None, _query)
