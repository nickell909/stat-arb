"""
Johansen Test for Cointegration

Implements the Johansen test for finding cointegrating relationships
among multiple time series (3+ assets).
"""

import logging
from typing import List, Tuple, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from .models import JohansenResult

logger = logging.getLogger(__name__)


class JohansenTest:
    """
    Johansen test for cointegration among multiple assets.
    
    Unlike Engle-Granger which tests pairs, Johansen test can identify
    multiple cointegrating vectors among a group of assets.
    """
    
    def __init__(
        self,
        significance_level: float = 0.05,
        max_lag: int = 2
    ):
        """
        Initialize the Johansen test.
        
        Args:
            significance_level: Significance level for hypothesis testing
            max_lag: Maximum lag order for the VAR model
        """
        self.significance_level = significance_level
        self.max_lag = max_lag
    
    def test(
        self,
        price_data: pd.DataFrame,
        det_order: int = 0,
        klag: Optional[int] = None
    ) -> Optional[JohansenResult]:
        """
        Perform Johansen test on multiple assets.
        
        Args:
            price_data: DataFrame with price series as columns
            det_order: Deterministic terms order
                0: no constant
                1: constant within cointegration space
                2: linear trend within cointegration space
            klag: Lag order for VAR model (default: auto-select)
            
        Returns:
            JohansenResult object if test succeeds, None otherwise
        """
        # Remove NaN values
        data_clean = price_data.dropna()
        
        if len(data_clean) < self.max_lag + 10:
            logger.warning("Insufficient data for Johansen test")
            return None
        
        if data_clean.shape[1] < 2:
            logger.warning("Need at least 2 assets for Johansen test")
            return None
        
        try:
            # Run Johansen test
            klag = klag or self.max_lag
            result = coint_johansen(data_clean.values, det_order, klag)
            
            # Extract results
            assets = list(data_clean.columns)
            eigenvalues = result.eig.tolist()
            trace_stats = result.lr1.tolist()
            
            # Critical values
            cv_90 = result.cvt[:, 0].tolist()
            cv_95 = result.cvt[:, 1].tolist()
            cv_99 = result.cvt[:, 2].tolist()
            
            # Determine number of cointegrating vectors
            num_coint_vectors = self._count_cointegrating_vectors(
                trace_stats, cv_95
            )
            
            # Extract cointegrating vectors (use 'evec' attribute)
            coint_vectors = result.evec.tolist()
            
            johansen_result = JohansenResult(
                assets=assets,
                eigenvalues=eigenvalues,
                trace_stats=trace_stats,
                critical_values_90=cv_90,
                critical_values_95=cv_95,
                critical_values_99=cv_99,
                num_cointegrating_vectors=num_coint_vectors,
                cointegrating_vectors=coint_vectors
            )
            
            logger.info(
                f"Johansen test completed: {num_coint_vectors} "
                f"cointegrating vector(s) found among {len(assets)} assets"
            )
            
            return johansen_result
            
        except Exception as e:
            logger.error(f"Johansen test failed: {e}")
            return None
    
    def _count_cointegrating_vectors(
        self,
        trace_stats: List[float],
        critical_values: List[float]
    ) -> int:
        """
        Determine number of cointegrating vectors based on trace statistics.
        
        Uses the trace test: compare trace statistic to critical value
        for each rank r = 0, 1, 2, ...
        
        Args:
            trace_stats: Trace statistics for each rank
            critical_values: Critical values at chosen significance level
            
        Returns:
            Number of cointegrating vectors
        """
        n = len(trace_stats)
        num_coint = 0
        
        for r in range(n):
            if r >= len(critical_values):
                break
                
            # Null hypothesis: at most r cointegrating vectors
            # If trace_stat > critical_value, reject null
            if trace_stats[r] > critical_values[r]:
                num_coint = r + 1
            else:
                break
        
        return num_coint
    
    def get_portfolio_weights(
        self,
        result: JohansenResult,
        vector_index: int = 0
    ) -> dict[str, float]:
        """
        Extract portfolio weights from a cointegrating vector.
        
        The cointegrating vector represents weights for a stationary
        linear combination of the assets.
        
        Args:
            result: JohansenResult from test()
            vector_index: Which cointegrating vector to use (0 = strongest)
            
        Returns:
            Dictionary mapping asset to weight
        """
        if vector_index >= len(result.cointegrating_vectors):
            raise ValueError(
                f"Vector index {vector_index} out of range, "
                f"only {len(result.cointegrating_vectors)} vectors available"
            )
        
        weights = result.cointegrating_vectors[vector_index]
        assets = result.assets
        
        portfolio = {asset: weight for asset, weight in zip(assets, weights)}
        
        logger.debug(
            f"Portfolio weights from vector {vector_index}: {portfolio}"
        )
        
        return portfolio
    
    def calculate_portfolio_series(
        self,
        price_data: pd.DataFrame,
        result: JohansenResult,
        vector_index: int = 0
    ) -> pd.Series:
        """
        Calculate the stationary portfolio (spread) series.
        
        Args:
            price_data: DataFrame with price series
            result: JohansenResult from test()
            vector_index: Which cointegrating vector to use
            
        Returns:
            Portfolio value series (should be stationary)
        """
        weights = self.get_portfolio_weights(result, vector_index)
        
        # Align prices with weights
        aligned_prices = price_data[list(weights.keys())]
        
        # Calculate weighted sum
        portfolio_values = (aligned_prices * pd.Series(weights)).sum(axis=1)
        portfolio_values.name = f"johansen_portfolio_{vector_index}"
        
        return portfolio_values
    
    def test_group(
        self,
        price_data: pd.DataFrame,
        assets: List[str]
    ) -> Optional[JohansenResult]:
        """
        Convenience method to test a specific group of assets.
        
        Args:
            price_data: Full price DataFrame
            assets: List of asset symbols to test
            
        Returns:
            JohansenResult or None
        """
        subset = price_data[assets].copy()
        return self.test(subset)
    
    def screen_groups(
        self,
        price_data: pd.DataFrame,
        group_size: int = 3,
        max_groups: int = 100
    ) -> List[JohansenResult]:
        """
        Screen multiple groups of assets for cointegration.
        
        Args:
            price_data: DataFrame with price series
            group_size: Number of assets per group
            max_groups: Maximum number of groups to test
            
        Returns:
            List of JohansenResult for groups with cointegration
        """
        from itertools import combinations
        
        assets = list(price_data.columns)
        results = []
        groups_tested = 0
        
        logger.info(
            f"Screening groups of {group_size} assets for cointegration..."
        )
        
        for group in combinations(assets, group_size):
            if groups_tested >= max_groups:
                break
            
            try:
                result = self.test_group(price_data, list(group))
                if result and result.num_cointegrating_vectors > 0:
                    results.append(result)
                    logger.debug(
                        f"Cointegrated group found: {group}, "
                        f"{result.num_cointegrating_vectors} vector(s)"
                    )
            except Exception as e:
                logger.debug(f"Group {group} test failed: {e}")
            
            groups_tested += 1
        
        logger.info(
            f"Tested {groups_tested} groups, "
            f"found {len(results)} cointegrated groups"
        )
        
        return results
