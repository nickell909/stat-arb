"""
Главный модуль приложения.
Инициализация и запуск.
"""

import asyncio
import logging
import signal
from datetime import datetime, timedelta
from typing import List

from src.connectors import ExchangeManager
from src.api import HistoricalDataClient
from src.data import DataNormalizer, DatabaseManager
from src.models import Timeframe, OHLCV


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crypto_arb.log')
    ]
)

logger = logging.getLogger(__name__)


class CryptoArbitrageApp:
    """
    Главное приложение для мониторинга криптовалютных бирж.
    
    Объединяет все компоненты:
    - WebSocket коннекторы для real-time данных
    - REST API клиент для исторических данных
    - База данных для хранения
    - Нормализатор для обработки данных
    """
    
    def __init__(self, db_path: str = "crypto_data.db"):
        self.exchange_manager = ExchangeManager()
        self.historical_client = HistoricalDataClient()
        self.normalizer = DataNormalizer(outlier_threshold_pct=5.0)
        self.database = DatabaseManager(db_path=db_path)
        
        self._running = False
    
    async def start(self, symbols: List[str]) -> None:
        """
        Запуск приложения.
        
        Args:
            symbols: Список символов для мониторинга (например, ['BTC/USDT', 'ETH/USDT'])
        """
        self._running = True
        
        # Подключение к биржам
        logger.info("Connecting to exchanges...")
        await self.exchange_manager.connect_all()
        
        # Подписка на символы
        logger.info(f"Subscribing to symbols: {symbols}")
        await self.exchange_manager.subscribe_all(symbols)
        
        logger.info("Application started. Press Ctrl+C to stop.")
        
        # Основной цикл обработки тиков
        await self._process_ticks()
    
    async def _process_ticks(self) -> None:
        """Обработка входящих тиковых данных."""
        while self._running:
            try:
                tick = await self.exchange_manager.get_next_tick()
                
                # Здесь можно добавить логику обработки тиков
                # Например, вычисление спредов, поиск арбитражных возможностей
                logger.debug(
                    f"Tick: {tick.exchange} {tick.symbol} "
                    f"last={tick.last} volume={tick.volume}"
                )
                
            except Exception as e:
                logger.error(f"Error processing tick: {e}")
    
    async def load_historical_data(
        self,
        exchange: str,
        symbol: str,
        timeframe: Timeframe,
        days: int = 30
    ) -> List[OHLCV]:
        """
        Загрузка исторических данных с умной проверкой БД.
        
        Args:
            exchange: Название биржи
            symbol: Символ
            timeframe: Таймфрейм
            days: Количество дней для загрузки
        
        Returns:
            Список OHLCV свечей
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Проверяем, какие данные уже есть в БД
        missing_periods = await self.database.get_missing_periods(
            exchange, symbol, timeframe, start_date, end_date
        )
        
        all_candles = []
        
        for period_start, period_end in missing_periods:
            logger.info(
                f"Loading data for {exchange} {symbol} {timeframe.value} "
                f"from {period_start} to {period_end}"
            )
            
            # Загружаем с биржи
            candles = await self.historical_client.fetch_ohlcv(
                exchange, symbol, timeframe, period_start, period_end
            )
            
            if candles:
                # Нормализация и валидация
                candles = self.normalizer.filter_invalid_candles(candles)
                candles = self.normalizer.remove_outliers(candles)
                candles = self.normalizer.fill_gaps(
                    candles, 
                    self._timeframe_to_minutes(timeframe)
                )
                
                # Сохраняем в БД
                saved = await self.database.save_candles(candles, timeframe)
                logger.info(f"Saved {saved} candles to database")
                
                all_candles.extend(candles)
        
        # Загружаем все данные из БД (включая ранее сохраненные)
        db_candles = await self.database.get_candles(
            exchange, symbol, timeframe, start_date, end_date
        )
        
        return db_candles
    
    def _timeframe_to_minutes(self, timeframe: Timeframe) -> int:
        """Конвертация таймфрейма в минуты."""
        mapping = {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440,
        }
        return mapping.get(timeframe, 1)
    
    async def stop(self) -> None:
        """Остановка приложения."""
        logger.info("Stopping application...")
        self._running = False
        
        await self.exchange_manager.disconnect_all()
        await self.historical_client.close()
        
        logger.info("Application stopped")


async def main():
    """Точка входа приложения."""
    app = CryptoArbitrageApp()
    
    # Обработка сигналов остановки
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received stop signal")
        asyncio.create_task(app.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        # Запуск с примером символов
        symbols = ['BTC/USDT', 'ETH/USDT']
        await app.start(symbols)
    except Exception as e:
        logger.error(f"Application error: {e}")
        await app.stop()


if __name__ == '__main__':
    asyncio.run(main())
