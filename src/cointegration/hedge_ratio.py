"""
Hedge Ratio Calculator

Provides two methods for calculating hedge ratios:
1. OLS (static) - Simple linear regression
2. Kalman Filter (dynamic) - Time-varying hedge ratio
"""

import logging
from typing import Tuple, List, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from .models import HedgeRatioTimeSeries

logger = logging.getLogger(__name__)


class HedgeRatioCalculator:
    """
    Calculate hedge ratios using OLS or Kalman Filter.
    """
    
    def __init__(self, method: str = 'ols'):
        """
        Initialize the calculator.
        
        Args:
            method: 'ols' for static, 'kalman' for dynamic hedge ratio
        """
        if method not in ['ols', 'kalman']:
            raise ValueError("Method must be 'ols' or 'kalman'")
        self.method = method
    
    def calculate(
        self,
        prices_1: pd.Series,
        prices_2: pd.Series,
        method: Optional[str] = None
    ) -> Tuple[float, Optional[HedgeRatioTimeSeries]]:
        """
        Calculate hedge ratio between two price series.
        
        Args:
            prices_1: First price series (dependent variable)
            prices_2: Second price series (independent variable)
            method: Override default method ('ols' or 'kalman')
            
        Returns:
            Tuple of (hedge_ratio, time_series) where time_series is only
            populated for Kalman filter method
        """
        method = method or self.method
        
        # Align series
        common_idx = prices_1.index.intersection(prices_2.index)
        if len(common_idx) < 30:
            raise ValueError("Insufficient data points for hedge ratio calculation")
        
        p1 = prices_1.loc[common_idx].values
        p2 = prices_2.loc[common_idx].values
        timestamps = common_idx.to_pydatetime()
        
        if method == 'ols':
            hedge_ratio = self._ols_hedge_ratio(p1, p2)
            return hedge_ratio, None
        else:
            hedge_ratio, time_series = self._kalman_hedge_ratio(p1, p2, timestamps)
            return hedge_ratio, time_series
    
    def _ols_hedge_ratio(self, prices_1: np.ndarray, prices_2: np.ndarray) -> float:
        """
        Calculate static hedge ratio using OLS regression.
        
        price_1 = α + β * price_2 + ε
        
        Returns:
            β (hedge ratio)
        """
        X = add_constant(prices_2)
        model = OLS(prices_1, X)
        results = model.fit()
        
        if len(results.params) > 1:
            hedge_ratio = results.params[1]
        else:
            hedge_ratio = 1.0
        
        logger.debug(f"OLS hedge ratio: {hedge_ratio:.6f}")
        return hedge_ratio
    
    def _kalman_hedge_ratio(
        self,
        prices_1: np.ndarray,
        prices_2: np.ndarray,
        timestamps: np.ndarray
    ) -> Tuple[float, HedgeRatioTimeSeries]:
        """
        Calculate dynamic hedge ratio using Kalman Filter.
        
        Models hedge ratio as a state-space model where β is a hidden variable
        that evolves over time.
        
        State equation: β_t = β_{t-1} + η_t (random walk)
        Observation equation: y_t = β_t * x_t + ε_t
        
        Returns:
            Tuple of (final_hedge_ratio, HedgeRatioTimeSeries)
        """
        n = len(prices_1)
        
        # Kalman Filter parameters
        # Q: state covariance (how much hedge ratio can change)
        # R: observation covariance (measurement noise)
        Q = 1e-5  # Small value for slow-changing hedge ratio
        R = np.var(prices_1) * 0.01  # Observation noise
        
        # Initialize state and covariance
        beta = prices_1[0] / prices_2[0] if prices_2[0] != 0 else 1.0
        P = 1.0  # Initial covariance
        
        hedge_ratios = []
        std_errors = []
        
        for i in range(n):
            x = prices_2[i]
            y = prices_1[i]
            
            # Prediction step
            beta_pred = beta  # Random walk model
            P_pred = P + Q
            
            # Update step
            # Kalman gain
            if abs(x) > 1e-10:
                K = P_pred * x / (x * x * P_pred + R + 1e-10)
            else:
                K = 0.0
            
            # Innovation
            innovation = y - beta_pred * x
            
            # State update
            beta = beta_pred + K * innovation
            
            # Covariance update
            P = (1 - K * x) * P_pred
            
            hedge_ratios.append(beta)
            std_errors.append(np.sqrt(P))
        
        final_hedge_ratio = hedge_ratios[-1]
        
        time_series = HedgeRatioTimeSeries(
            timestamps=list(timestamps),
            hedge_ratios=hedge_ratios,
            std_errors=std_errors
        )
        
        logger.debug(f"Kalman hedge ratio: {final_hedge_ratio:.6f}")
        return final_hedge_ratio, time_series
    
    def calculate_spread(
        self,
        prices_1: pd.Series,
        prices_2: pd.Series,
        hedge_ratio: float
    ) -> pd.Series:
        """
        Calculate spread series given hedge ratio.
        
        Spread = price_1 - hedge_ratio * price_2
        
        Args:
            prices_1: First price series
            prices_2: Second price series
            hedge_ratio: Hedge ratio (β)
            
        Returns:
            Spread series
        """
        common_idx = prices_1.index.intersection(prices_2.index)
        p1 = prices_1.loc[common_idx]
        p2 = prices_2.loc[common_idx]
        
        spread = p1 - hedge_ratio * p2
        spread.name = f"{prices_1.name}_{prices_2.name}_spread"
        
        return spread
    
    def rolling_ols_hedge_ratio(
        self,
        prices_1: pd.Series,
        prices_2: pd.Series,
        window: int = 60
    ) -> pd.Series:
        """
        Calculate rolling OLS hedge ratio over a moving window.
        
        Useful for visualizing how hedge ratio changes over time
        without full Kalman filter complexity.
        
        Args:
            prices_1: First price series
            prices_2: Second price series
            window: Rolling window size
            
        Returns:
            Series of hedge ratios
        """
        common_idx = prices_1.index.intersection(prices_2.index)
        p1 = prices_1.loc[common_idx]
        p2 = prices_2.loc[common_idx]
        
        hedge_ratios = []
        indices = []
        
        for i in range(window, len(p1)):
            window_p1 = p1.iloc[i-window:i].values
            window_p2 = p2.iloc[i-window:i].values
            
            if len(window_p1) >= 30:
                hr = self._ols_hedge_ratio(window_p1, window_p2)
                hedge_ratios.append(hr)
                indices.append(common_idx[i])
        
        result = pd.Series(hedge_ratios, index=indices, name='rolling_hedge_ratio')
        return result
