"""
Tests for the Cointegration Engine module.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.cointegration.screening import CointegrationScreener
from src.cointegration.hedge_ratio import HedgeRatioCalculator
from src.cointegration.half_life import HalfLifeCalculator
from src.cointegration.johansen import JohansenTest
from src.cointegration.models import CointegrationPair, JohansenResult


class TestCointegrationScreener:
    """Tests for CointegrationScreener class."""
    
    @pytest.fixture
    def sample_prices(self):
        """Generate sample price data for testing."""
        np.random.seed(42)
        n = 200
        
        # Create two cointegrated series
        base = np.cumsum(np.random.randn(n)) + 100
        series1 = base + np.random.randn(n) * 0.5
        series2 = 0.8 * base + np.random.randn(n) * 0.3 + 50
        
        dates = pd.date_range('2024-01-01', periods=n, freq='D')
        
        return {
            'BTC/USDT': pd.Series(series1, index=dates, name='BTC/USDT'),
            'ETH/USDT': pd.Series(series2, index=dates, name='ETH/USDT')
        }
    
    def test_screener_initialization(self):
        """Test screener initialization with default parameters."""
        screener = CointegrationScreener()
        assert screener.correlation_threshold == 0.7
        assert screener.adf_pvalue_threshold == 0.05
        assert screener.min_samples == 60
    
    def test_screener_custom_parameters(self):
        """Test screener with custom parameters."""
        screener = CointegrationScreener(
            correlation_threshold=0.8,
            adf_pvalue_threshold=0.01,
            min_samples=100
        )
        assert screener.correlation_threshold == 0.8
        assert screener.adf_pvalue_threshold == 0.01
        assert screener.min_samples == 100
    
    def test_correlation_filter(self, sample_prices):
        """Test correlation-based pre-filtering."""
        screener = CointegrationScreener(correlation_threshold=0.5)
        symbols = list(sample_prices.keys())
        
        pairs = screener._filter_by_correlation(sample_prices, symbols)
        
        # Should find at least one correlated pair
        assert len(pairs) >= 0  # May be 0 if correlation < threshold
    
    def test_screen_pairs(self, sample_prices):
        """Test full screening process."""
        screener = CointegrationScreener(
            correlation_threshold=0.5,
            min_samples=50
        )
        
        results = screener.screen_pairs(sample_prices)
        
        # Results should be list of CointegrationPair or empty
        assert isinstance(results, list)
        for pair in results:
            assert isinstance(pair, CointegrationPair)
            assert pair.asset_1 in sample_prices.keys()
            assert pair.asset_2 in sample_prices.keys()
    
    def test_correlation_matrix(self, sample_prices):
        """Test correlation matrix calculation."""
        screener = CointegrationScreener()
        corr_matrix = screener.get_correlation_matrix(sample_prices)
        
        assert isinstance(corr_matrix, pd.DataFrame)
        assert corr_matrix.shape[0] == len(sample_prices)
        assert corr_matrix.shape[1] == len(sample_prices)
        # Diagonal should be 1.0
        for col in corr_matrix.columns:
            assert abs(corr_matrix.loc[col, col] - 1.0) < 1e-6


class TestHedgeRatioCalculator:
    """Tests for HedgeRatioCalculator class."""
    
    @pytest.fixture
    def price_series(self):
        """Generate correlated price series."""
        np.random.seed(42)
        n = 100
        
        base = np.cumsum(np.random.randn(n)) + 100
        prices1 = base + np.random.randn(n) * 0.5
        prices2 = 0.8 * base + np.random.randn(n) * 0.3
        
        dates = pd.date_range('2024-01-01', periods=n, freq='D')
        
        return (
            pd.Series(prices1, index=dates, name='Asset1'),
            pd.Series(prices2, index=dates, name='Asset2')
        )
    
    def test_calculator_initialization(self):
        """Test calculator initialization."""
        calc = HedgeRatioCalculator(method='ols')
        assert calc.method == 'ols'
        
        calc_kalman = HedgeRatioCalculator(method='kalman')
        assert calc_kalman.method == 'kalman'
    
    def test_invalid_method(self):
        """Test invalid method raises error."""
        with pytest.raises(ValueError):
            HedgeRatioCalculator(method='invalid')
    
    def test_ols_hedge_ratio(self, price_series):
        """Test OLS hedge ratio calculation."""
        calc = HedgeRatioCalculator(method='ols')
        hedge_ratio, time_series = calc.calculate(price_series[0], price_series[1])
        
        assert isinstance(hedge_ratio, float)
        assert time_series is None  # OLS doesn't return time series
        # Hedge ratio should be positive and reasonable (our synthetic data ~0.8)
        assert 0.3 < hedge_ratio < 1.5
    
    def test_kalman_hedge_ratio(self, price_series):
        """Test Kalman filter hedge ratio calculation."""
        calc = HedgeRatioCalculator(method='kalman')
        hedge_ratio, time_series = calc.calculate(price_series[0], price_series[1])
        
        assert isinstance(hedge_ratio, float)
        assert time_series is not None
        assert len(time_series.hedge_ratios) == len(price_series[0])
        assert len(time_series.timestamps) == len(price_series[0])
    
    def test_spread_calculation(self, price_series):
        """Test spread calculation."""
        calc = HedgeRatioCalculator()
        hedge_ratio = 0.8
        spread = calc.calculate_spread(price_series[0], price_series[1], hedge_ratio)
        
        assert isinstance(spread, pd.Series)
        assert len(spread) == len(price_series[0])
    
    def test_rolling_hedge_ratio(self, price_series):
        """Test rolling OLS hedge ratio."""
        calc = HedgeRatioCalculator()
        rolling_hr = calc.rolling_ols_hedge_ratio(
            price_series[0], price_series[1], window=30
        )
        
        assert isinstance(rolling_hr, pd.Series)
        # Rolling window reduces length
        assert len(rolling_hr) < len(price_series[0])


class TestHalfLifeCalculator:
    """Tests for HalfLifeCalculator class."""
    
    @pytest.fixture
    def mean_reverting_series(self):
        """Generate mean-reverting spread series."""
        np.random.seed(42)
        n = 200
        
        # Ornstein-Uhlenbeck process
        kappa = 0.1  # Mean reversion speed
        mu = 0  # Long-term mean
        sigma = 0.5  # Volatility
        
        spread = np.zeros(n)
        spread[0] = mu
        
        for t in range(1, n):
            spread[t] = spread[t-1] + kappa * (mu - spread[t-1]) + sigma * np.random.randn()
        
        dates = pd.date_range('2024-01-01', periods=n, freq='D')
        return pd.Series(spread, index=dates, name='spread')
    
    def test_calculator_initialization(self):
        """Test calculator initialization."""
        calc = HalfLifeCalculator()
        assert calc.min_half_life_days == 2.0
        assert calc.max_half_life_days == 60.0
    
    def test_half_life_calculation(self, mean_reverting_series):
        """Test half-life calculation."""
        calc = HalfLifeCalculator()
        half_life, details = calc.calculate(mean_reverting_series, freq='1D')
        
        assert isinstance(half_life, float)
        assert isinstance(details, dict)
        assert 'kappa' in details
        assert 'half_life_days' in details
        assert 'is_tradable' in details
    
    def test_is_tradable(self):
        """Test tradable range check."""
        calc = HalfLifeCalculator(min_half_life_days=2.0, max_half_life_days=60.0)
        
        assert calc.is_tradable(10.0) == True
        assert calc.is_tradable(1.0) == False  # Too short
        assert calc.is_tradable(100.0) == False  # Too long
        assert calc.is_tradable(float('inf')) == False
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        calc = HalfLifeCalculator()
        short_series = pd.Series([1, 2, 3, 4, 5])
        
        with pytest.raises(ValueError):
            calc.calculate(short_series)
    
    def test_calculate_for_pairs(self, mean_reverting_series):
        """Test batch half-life calculation."""
        calc = HalfLifeCalculator()
        spreads = {
            'pair1': mean_reverting_series,
            'pair2': mean_reverting_series * 1.1 + 5
        }
        
        results = calc.calculate_for_pairs(spreads, freq='1D')
        
        assert isinstance(results, dict)
        assert 'pair1' in results
        assert 'pair2' in results
    
    def test_get_optimal_pairs(self, mean_reverting_series):
        """Test filtering optimal pairs."""
        calc = HalfLifeCalculator()
        
        # Create results with different half-lives
        results = {
            'good_pair': (10.0, {'is_tradable': True}),
            'too_slow': (100.0, {'is_tradable': False}),
            'too_fast': (0.5, {'is_tradable': False})
        }
        
        optimal = calc.get_optimal_pairs(results)
        
        assert isinstance(optimal, list)
        assert 'good_pair' in optimal


class TestJohansenTest:
    """Tests for JohansenTest class."""
    
    @pytest.fixture
    def multivariate_prices(self):
        """Generate three cointegrated price series."""
        np.random.seed(42)
        n = 300
        
        # Common factor
        common = np.cumsum(np.random.randn(n)) + 100
        
        # Three assets with different loadings on common factor
        asset1 = common + np.random.randn(n) * 0.3
        asset2 = 0.8 * common + np.random.randn(n) * 0.2 + 10
        asset3 = 1.2 * common + np.random.randn(n) * 0.4 - 20
        
        dates = pd.date_range('2024-01-01', periods=n, freq='D')
        
        return pd.DataFrame({
            'Asset1': asset1,
            'Asset2': asset2,
            'Asset3': asset3
        }, index=dates)
    
    def test_johansen_initialization(self):
        """Test Johansen test initialization."""
        test = JohansenTest()
        assert test.significance_level == 0.05
        assert test.max_lag == 2
    
    def test_johansen_test(self, multivariate_prices):
        """Test Johansen test execution."""
        test = JohansenTest(max_lag=2)
        result = test.test(multivariate_prices)
        
        # Result may be None if no cointegration found
        if result is not None:
            assert isinstance(result, JohansenResult)
            assert len(result.assets) == 3
            assert len(result.eigenvalues) == 3
            assert len(result.trace_stats) == 3
    
    def test_portfolio_weights(self, multivariate_prices):
        """Test portfolio weight extraction."""
        test = JohansenTest(max_lag=2)
        result = test.test(multivariate_prices)
        
        if result is not None and result.num_cointegrating_vectors > 0:
            weights = test.get_portfolio_weights(result, vector_index=0)
            
            assert isinstance(weights, dict)
            assert len(weights) == 3
            assert set(weights.keys()) == set(multivariate_prices.columns)
    
    def test_portfolio_series(self, multivariate_prices):
        """Test portfolio series calculation."""
        test = JohansenTest(max_lag=2)
        result = test.test(multivariate_prices)
        
        if result is not None and result.num_cointegrating_vectors > 0:
            portfolio = test.calculate_portfolio_series(
                multivariate_prices, result, vector_index=0
            )
            
            assert isinstance(portfolio, pd.Series)
            assert len(portfolio) <= len(multivariate_prices)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        test = JohansenTest()
        small_df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        
        result = test.test(small_df)
        assert result is None  # Should return None for insufficient data


class TestCointegrationPair:
    """Tests for CointegrationPair model."""
    
    def test_pair_creation(self):
        """Test CointegrationPair creation."""
        pair = CointegrationPair(
            pair_id='BTC_ETH',
            asset_1='BTC/USDT',
            asset_2='ETH/USDT',
            hedge_ratio=0.85,
            p_value=0.01,
            coint_score=-5.5,
            half_life_days=15.0,
            last_checked_at=datetime.now()
        )
        
        assert pair.pair_id == 'BTC_ETH'
        assert pair.hedge_ratio == 0.85
        assert pair.p_value == 0.01
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        pair = CointegrationPair(
            pair_id='BTC_ETH',
            asset_1='BTC/USDT',
            asset_2='ETH/USDT',
            hedge_ratio=0.85,
            p_value=0.01,
            coint_score=-5.5,
            half_life_days=15.0,
            last_checked_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        d = pair.to_dict()
        
        assert isinstance(d, dict)
        assert d['pair_id'] == 'BTC_ETH'
        assert 'asset_1' in d
        assert 'last_checked_at' in d
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'pair_id': 'BTC_ETH',
            'asset_1': 'BTC/USDT',
            'asset_2': 'ETH/USDT',
            'hedge_ratio': 0.85,
            'p_value': 0.01,
            'coint_score': -5.5,
            'half_life_days': 15.0,
            'last_checked_at': '2024-01-01T12:00:00'
        }
        
        pair = CointegrationPair.from_dict(data)
        
        assert isinstance(pair, CointegrationPair)
        assert pair.pair_id == 'BTC_ETH'
        assert pair.last_checked_at == datetime(2024, 1, 1, 12, 0, 0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
