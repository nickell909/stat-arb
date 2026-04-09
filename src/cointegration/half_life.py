"""
Half-Life Calculator

Calculates the half-life of mean reversion for spread series
using Ornstein-Uhlenbeck process.
"""

import logging
from typing import Optional
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

logger = logging.getLogger(__name__)


class HalfLifeCalculator:
    """
    Calculate half-life of mean reversion for spread series.
    
    The half-life indicates how many days it takes for the spread
    to revert halfway back to its mean value.
    
    For pairs trading, ideal half-life is between 2 and 60 days.
    """
    
    def __init__(
        self,
        min_half_life_days: float = 2.0,
        max_half_life_days: float = 60.0
    ):
        """
        Initialize the calculator.
        
        Args:
            min_half_life_days: Minimum acceptable half-life
            max_half_life_days: Maximum acceptable half-life
        """
        self.min_half_life_days = min_half_life_days
        self.max_half_life_days = max_half_life_days
    
    def calculate(
        self,
        spread: pd.Series,
        freq: str = '1D'
    ) -> tuple[float, dict]:
        """
        Calculate half-life of mean reversion.
        
        Uses the Ornstein-Uhlenbeck process:
        dS = κ(μ - S)dt + σdW
        
        Where:
        - S is the spread
        - κ is the mean reversion rate
        - μ is the long-term mean
        - σ is volatility
        - W is Wiener process
        
        Half-life = ln(2) / κ
        
        Args:
            spread: Spread time series
            freq: Frequency of data ('1D', '1H', '5T', etc.)
            
        Returns:
            Tuple of (half_life_days, details_dict)
        """
        if len(spread) < 30:
            raise ValueError("Insufficient data points for half-life calculation")
        
        # Remove NaN values
        spread_clean = spread.dropna()
        if len(spread_clean) < 30:
            raise ValueError("Insufficient valid data points after cleaning")
        
        # Calculate lagged differences
        # ΔS_t = κ(μ - S_{t-1}) + ε_t
        # Rearranged: ΔS_t = α + β * S_{t-1} + ε_t
        # Where β = -κ, so κ = -β
        
        spread_values = spread_clean.values
        
        # Lag-1 difference
        delta_spread = np.diff(spread_values)
        lag_spread = spread_values[:-1]
        
        if len(delta_spread) < 30:
            raise ValueError("Insufficient data points after differencing")
        
        # Add constant for intercept (α)
        X = add_constant(lag_spread)
        y = delta_spread
        
        # Fit OLS regression
        model = OLS(y, X)
        results = model.fit()
        
        # Extract mean reversion coefficient
        # β is the coefficient on lag_spread (index 1)
        if len(results.params) > 1:
            beta = results.params[1]
        else:
            beta = 0.0
        
        # κ = -β
        kappa = -beta
        
        # Handle edge cases
        if kappa <= 0:
            # No mean reversion or explosive
            half_life_days = float('inf')
            logger.warning(f"Negative or zero kappa ({kappa:.6f}), no mean reversion")
        else:
            # Calculate half-life in periods
            half_life_periods = np.log(2) / kappa
            
            # Convert to days based on frequency
            half_life_days = self._convert_to_days(half_life_periods, freq)
        
        # Build details dictionary
        details = {
            'kappa': kappa,
            'half_life_periods': half_life_periods if kappa > 0 else float('inf'),
            'half_life_days': half_life_days,
            'mean_reversion_rate': kappa,
            'is_tradable': self.is_tradable(half_life_days),
            'rsquared': results.rsquared,
            'std_err_beta': results.bse[1] if len(results.bse) > 1 else 0.0
        }
        
        logger.debug(
            f"Half-life: {half_life_days:.2f} days, "
            f"kappa: {kappa:.6f}, "
            f"tradable: {details['is_tradable']}"
        )
        
        return half_life_days, details
    
    def _convert_to_days(self, periods: float, freq: str) -> float:
        """
        Convert half-life from periods to days.
        
        Args:
            periods: Half-life in data periods
            freq: Data frequency string
            
        Returns:
            Half-life in days
        """
        # Parse frequency string
        freq_multipliers = {
            '1T': 1 / (24 * 60),      # Minutes to days
            '5T': 5 / (24 * 60),
            '15T': 15 / (24 * 60),
            '30T': 30 / (24 * 60),
            '1H': 1 / 24,             # Hours to days
            '4H': 4 / 24,
            '1D': 1.0,                # Days
            '1W': 7.0,                # Weeks
        }
        
        multiplier = freq_multipliers.get(freq, 1.0)
        return periods * multiplier
    
    def is_tradable(self, half_life_days: float) -> bool:
        """
        Check if half-life is within tradable range.
        
        Args:
            half_life_days: Half-life in days
            
        Returns:
            True if half-life is between min and max thresholds
        """
        if np.isinf(half_life_days) or np.isnan(half_life_days):
            return False
        return self.min_half_life_days <= half_life_days <= self.max_half_life_days
    
    def calculate_for_pairs(
        self,
        spreads: dict[str, pd.Series],
        freq: str = '1D'
    ) -> dict[str, tuple[float, dict]]:
        """
        Calculate half-life for multiple spread series.
        
        Args:
            spreads: Dictionary mapping pair_id to spread series
            freq: Data frequency
            
        Returns:
            Dictionary mapping pair_id to (half_life, details) tuple
        """
        results = {}
        
        for pair_id, spread in spreads.items():
            try:
                result = self.calculate(spread, freq)
                results[pair_id] = result
            except Exception as e:
                logger.error(f"Failed to calculate half-life for {pair_id}: {e}")
                results[pair_id] = (float('inf'), {'error': str(e)})
        
        return results
    
    def get_optimal_pairs(
        self,
        half_life_results: dict[str, tuple[float, dict]]
    ) -> list[str]:
        """
        Filter pairs with optimal half-life for trading.
        
        Args:
            half_life_results: Results from calculate_for_pairs
            
        Returns:
            List of pair_ids with tradable half-life
        """
        optimal = []
        
        for pair_id, (half_life, details) in half_life_results.items():
            if self.is_tradable(half_life):
                optimal.append(pair_id)
        
        # Sort by half-life (prefer shorter but not too short)
        optimal.sort(key=lambda x: half_life_results[x][0])
        
        return optimal
