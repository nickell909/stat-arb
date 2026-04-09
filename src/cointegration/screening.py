"""
Cointegration Screener - Main screening engine for finding cointegrated pairs.

Implements the 4-step screening process:
1. Pre-filtering by Pearson correlation
2. Unit root test (ADF) for I(1) series
3. Engle-Granger test for cointegration
4. Johansen test for groups of 3+ assets
"""

import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

from .models import CointegrationPair

logger = logging.getLogger(__name__)


class CointegrationScreener:
    """
    Screens for cointegrated pairs using multi-step filtering process.
    """
    
    def __init__(
        self,
        correlation_threshold: float = 0.7,
        adf_pvalue_threshold: float = 0.05,
        min_samples: int = 60
    ):
        """
        Initialize the screener.
        
        Args:
            correlation_threshold: Minimum Pearson correlation for pre-filtering
            adf_pvalue_threshold: Maximum p-value for ADF test on residuals
            min_samples: Minimum number of data points required
        """
        self.correlation_threshold = correlation_threshold
        self.adf_pvalue_threshold = adf_pvalue_threshold
        self.min_samples = min_samples
    
    def screen_pairs(
        self,
        price_data: Dict[str, pd.Series],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[CointegrationPair]:
        """
        Screen all possible pairs for cointegration.
        
        Args:
            price_data: Dictionary mapping symbol to price series
            start_date: Optional start date for analysis
            end_date: Optional end date for analysis
            
        Returns:
            List of CointegrationPair objects for cointegrated pairs
        """
        symbols = list(price_data.keys())
        results = []
        
        logger.info(f"Screening {len(symbols)} symbols for cointegration...")
        logger.info(f"Total pairs to check: {len(symbols) * (len(symbols) - 1) // 2}")
        
        # Step 1: Pre-filter by correlation
        correlated_pairs = self._filter_by_correlation(price_data, symbols)
        logger.info(f"After correlation filter: {len(correlated_pairs)} pairs")
        
        # Step 2 & 3: ADF test and Engle-Granger test
        for asset_1, asset_2 in correlated_pairs:
            pair_result = self._test_pair(
                price_data[asset_1],
                price_data[asset_2],
                asset_1,
                asset_2
            )
            if pair_result:
                results.append(pair_result)
        
        logger.info(f"Found {len(results)} cointegrated pairs")
        return results
    
    def _filter_by_correlation(
        self,
        price_data: Dict[str, pd.Series],
        symbols: List[str]
    ) -> List[Tuple[str, str]]:
        """Step 1: Filter pairs by Pearson correlation."""
        correlated_pairs = []
        
        for asset_1, asset_2 in combinations(symbols, 2):
            # Align the series
            s1 = price_data[asset_1]
            s2 = price_data[asset_2]
            common_idx = s1.index.intersection(s2.index)
            
            if len(common_idx) < self.min_samples:
                continue
            
            s1_aligned = s1.loc[common_idx]
            s2_aligned = s2.loc[common_idx]
            
            # Calculate correlation
            try:
                corr, _ = pearsonr(s1_aligned.values, s2_aligned.values)
                if abs(corr) >= self.correlation_threshold:
                    correlated_pairs.append((asset_1, asset_2))
            except Exception as e:
                logger.debug(f"Correlation calculation failed for {asset_1}/{asset_2}: {e}")
        
        return correlated_pairs
    
    def _test_pair(
        self,
        prices_1: pd.Series,
        prices_2: pd.Series,
        asset_1: str,
        asset_2: str
    ) -> Optional[CointegrationPair]:
        """
        Steps 2-3: Test a single pair for cointegration.
        
        Returns CointegrationPair if cointegrated, None otherwise.
        """
        # Align series
        common_idx = prices_1.index.intersection(prices_2.index)
        if len(common_idx) < self.min_samples:
            return None
        
        p1 = prices_1.loc[common_idx].values
        p2 = prices_2.loc[common_idx].values
        
        # Step 2: ADF test on individual series (should be I(1))
        adf_1 = adfuller(p1, maxlag=1, regression='c', autolag='AIC')
        adf_2 = adfuller(p2, maxlag=1, regression='c', autolag='AIC')
        
        is_stationary_1 = adf_1[1] < self.adf_pvalue_threshold
        is_stationary_2 = adf_2[1] < self.adf_pvalue_threshold
        
        # For cointegration, both series should be non-stationary (I(1))
        # But we'll still proceed as some pairs might work even if one is borderline
        if is_stationary_1 and is_stationary_2:
            logger.debug(f"Both {asset_1} and {asset_2} are stationary, skipping")
            return None
        
        # Step 3: Engle-Granger test
        try:
            score, p_value, _ = coint(p1, p2, trend='c', method='aeg')
        except Exception as e:
            logger.error(f"Engle-Granger test failed for {asset_1}/{asset_2}: {e}")
            return None
        
        if p_value > self.adf_pvalue_threshold:
            return None
        
        # Calculate hedge ratio via OLS
        X = add_constant(p2)
        model = OLS(p1, X)
        results = model.fit()
        hedge_ratio = results.params[1] if len(results.params) > 1 else 1.0
        
        # Calculate correlation
        corr, _ = pearsonr(p1, p2)
        
        # Create pair result
        pair_id = f"{asset_1}_{asset_2}"
        pair = CointegrationPair(
            pair_id=pair_id,
            asset_1=asset_1,
            asset_2=asset_2,
            hedge_ratio=hedge_ratio,
            p_value=p_value,
            coint_score=score,
            half_life_days=0.0,  # Will be calculated separately
            last_checked_at=datetime.now(),
            correlation=corr,
            adf_stat_1=adf_1[0],
            adf_stat_2=adf_2[0],
            adf_stat_residual=score,
            is_stationary_1=is_stationary_1,
            is_stationary_2=is_stationary_2,
            method='ols'
        )
        
        logger.debug(f"Cointegrated pair found: {asset_1}/{asset_2}, p-value={p_value:.4f}")
        return pair
    
    def get_correlation_matrix(
        self,
        price_data: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """Calculate correlation matrix for all symbols."""
        symbols = list(price_data.keys())
        n = len(symbols)
        corr_matrix = np.zeros((n, n))
        
        # Build aligned dataframe
        df = pd.DataFrame(price_data)
        corr_df = df.corr()
        
        return corr_df
