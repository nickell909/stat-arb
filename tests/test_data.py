"""
Тесты для модуля data (нормализация и БД).
"""

import pytest
from datetime import datetime
from src.data.normalizer import DataNormalizer
from src.models.data_models import OHLCV


class TestDataNormalizer:
    """Тесты для нормализатора данных."""
    
    def test_outlier_detection(self):
        """Тест обнаружения выбросов."""
        normalizer = DataNormalizer(outlier_threshold_pct=5.0)
        
        # Нормальные цены
        prices = [100, 101, 102, 103, 104]
        outliers = normalizer.detect_outliers(prices)
        assert len(outliers) == 0
        
        # Цены с выбросом (выброс и возврат к норме дают 2 выброса)
        prices_with_outlier = [100, 101, 150, 103, 104]  # 150 - выброс
        outliers = normalizer.detect_outliers(prices_with_outlier)
        assert len(outliers) == 2  # Выброс вверх на 150 и вниз на 103
        assert outliers[0][0] == 2  # индекс первого выброса
        assert outliers[0][1] == 150  # цена первого выброса
    
    def test_candle_validation(self):
        """Тест валидации свечей."""
        normalizer = DataNormalizer()
        
        # Валидная свеча
        valid_candle = OHLCV(
            exchange='binance',
            symbol='BTC/USDT',
            timestamp_ms=1234567890000,
            open=50000,
            high=51000,
            low=49000,
            close=50500,
            volume=100
        )
        assert normalizer.validate_candle(valid_candle) == True
        
        # Невалидная: high < low
        invalid_high_low = OHLCV(
            exchange='binance',
            symbol='BTC/USDT',
            timestamp_ms=1234567890000,
            open=50000,
            high=49000,  # меньше low
            low=51000,
            close=50500,
            volume=100
        )
        assert normalizer.validate_candle(invalid_high_low) == False
        
        # Невалидная: open вне диапазона [low, high]
        invalid_open = OHLCV(
            exchange='binance',
            symbol='BTC/USDT',
            timestamp_ms=1234567890000,
            open=52000,  # выше high
            high=51000,
            low=49000,
            close=50500,
            volume=100
        )
        assert normalizer.validate_candle(invalid_open) == False
    
    def test_filter_invalid_candles(self):
        """Тест фильтрации невалидных свечей."""
        normalizer = DataNormalizer()
        
        candles = [
            OHLCV('binance', 'BTC/USDT', 1000, 50000, 51000, 49000, 50500, 100),  # валидная
            OHLCV('binance', 'BTC/USDT', 2000, 50000, 49000, 51000, 50500, 100),  # невалидная
            OHLCV('binance', 'BTC/USDT', 3000, 50000, 51000, 49000, 50500, 100),  # валидная
        ]
        
        filtered = normalizer.filter_invalid_candles(candles)
        assert len(filtered) == 2
    
    def test_candles_to_dataframe(self):
        """Тест конвертации свечей в DataFrame."""
        normalizer = DataNormalizer()
        
        candles = [
            OHLCV('binance', 'BTC/USDT', 1000, 50000, 51000, 49000, 50500, 100),
            OHLCV('binance', 'BTC/USDT', 2000, 50500, 51500, 50000, 51000, 150),
        ]
        
        df = normalizer.candles_to_dataframe(candles)
        
        assert len(df) == 2
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns


class TestSpreadCalculation:
    """Тесты для расчета спредов."""
    
    def test_spread_calculation(self):
        """Тест вычисления значения спреда."""
        from src.models.data_models import Spread
        
        spread = Spread(
            name='BTC_ETH_spread',
            leg1_symbol='BTC/USDT',
            leg1_exchange='binance',
            leg2_symbol='ETH/USDT',
            leg2_exchange='binance',
            leg1_ratio=1.0,
            leg2_ratio=15.0  # ETH примерно в 15 раз дешевле BTC
        )
        
        value = spread.calculate_spread(50000, 3000)
        assert value == 50000 - 15 * 3000
        assert value == 5000
    
    def test_z_score_calculation(self):
        """Тест вычисления Z-score."""
        from src.models.data_models import Spread
        
        spread = Spread(
            name='test_spread',
            leg1_symbol='A',
            leg1_exchange='binance',
            leg2_symbol='B',
            leg2_exchange='binance',
            mean=100,
            std=10
        )
        
        z_score = spread.calculate_z_score(120)
        assert z_score == 2.0  # (120 - 100) / 10 = 2
        
        z_score = spread.calculate_z_score(80)
        assert z_score == -2.0  # (80 - 100) / 10 = -2
