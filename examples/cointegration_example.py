"""
Example usage of the Cointegration Engine module.

This script demonstrates how to use the cointegration analysis tools
to find tradable pairs for statistical arbitrage.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

from src.cointegration.screening import CointegrationScreener
from src.cointegration.hedge_ratio import HedgeRatioCalculator
from src.cointegration.half_life import HalfLifeCalculator
from src.cointegration.johansen import JohansenTest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_data(n_assets: int = 5, n_points: int = 500):
    """
    Generate synthetic price data for demonstration.
    
    Creates assets with varying degrees of cointegration.
    """
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=n_points, freq='D')
    
    # Common factor (market trend)
    common_factor = np.cumsum(np.random.randn(n_points)) + 100
    
    prices = {}
    
    # Asset 1 & 2: Highly cointegrated (same exposure to common factor)
    prices['BTC/USDT'] = pd.Series(
        common_factor + np.random.randn(n_points) * 0.5,
        index=dates, name='BTC/USDT'
    )
    prices['ETH/USDT'] = pd.Series(
        0.9 * common_factor + np.random.randn(n_points) * 0.3 + 50,
        index=dates, name='ETH/USDT'
    )
    
    # Asset 3 & 4: Moderately cointegrated
    prices['SOL/USDT'] = pd.Series(
        0.7 * common_factor + np.random.randn(n_points) * 0.8 + 20,
        index=dates, name='SOL/USDT'
    )
    prices['AVAX/USDT'] = pd.Series(
        0.75 * common_factor + np.random.randn(n_points) * 0.6 + 30,
        index=dates, name='AVAX/USDT'
    )
    
    # Asset 5: Independent (not cointegrated with others)
    prices['INDEPENDENT'] = pd.Series(
        np.cumsum(np.random.randn(n_points)) + 50,
        index=dates, name='INDEPENDENT'
    )
    
    return prices


def main():
    print("=" * 70)
    print("COINTEGRATION ENGINE - EXAMPLE USAGE")
    print("=" * 70)
    
    # Generate synthetic data
    print("\n1. Generating synthetic price data...")
    prices = generate_synthetic_data(n_assets=5, n_points=500)
    print(f"   Generated {len(prices)} assets with 500 data points each")
    
    # Step 1: Screen for cointegrated pairs
    print("\n2. Screening for cointegrated pairs...")
    print("-" * 70)
    
    screener = CointegrationScreener(
        correlation_threshold=0.7,
        adf_pvalue_threshold=0.05,
        min_samples=100
    )
    
    cointegrated_pairs = screener.screen_pairs(prices)
    
    print(f"\n   Found {len(cointegrated_pairs)} cointegrated pairs:")
    for pair in cointegrated_pairs:
        print(f"   - {pair.asset_1} / {pair.asset_2}")
        print(f"     Correlation: {pair.correlation:.4f}")
        print(f"     Hedge Ratio: {pair.hedge_ratio:.4f}")
        print(f"     P-value: {pair.p_value:.6f}")
        print(f"     ADF Score: {pair.adf_stat_residual:.4f}")
    
    # Step 2: Calculate hedge ratios (OLS and Kalman)
    print("\n\n3. Calculating hedge ratios...")
    print("-" * 70)
    
    if cointegrated_pairs:
        best_pair = cointegrated_pairs[0]
        p1 = prices[best_pair.asset_1]
        p2 = prices[best_pair.asset_2]
        
        calc = HedgeRatioCalculator()
        
        # OLS method
        ols_hr, _ = calc.calculate(p1, p2, method='ols')
        print(f"\n   Pair: {best_pair.asset_1} / {best_pair.asset_2}")
        print(f"   OLS Hedge Ratio: {ols_hr:.6f}")
        
        # Kalman filter method
        kalman_hr, time_series = calc.calculate(p1, p2, method='kalman')
        print(f"   Kalman Hedge Ratio (final): {kalman_hr:.6f}")
        
        # Show hedge ratio evolution
        if time_series:
            print(f"   Hedge Ratio Range: [{min(time_series.hedge_ratios):.4f}, "
                  f"{max(time_series.hedge_ratios):.4f}]")
            print(f"   Std Error (final): {time_series.std_errors[-1]:.6f}")
        
        # Calculate spread
        spread = calc.calculate_spread(p1, p2, ols_hr)
        print(f"\n   Spread Statistics:")
        print(f"   Mean: {spread.mean():.4f}")
        print(f"   Std Dev: {spread.std():.4f}")
        print(f"   Min: {spread.min():.4f}")
        print(f"   Max: {spread.max():.4f}")
    
    # Step 3: Calculate half-life of mean reversion
    print("\n\n4. Calculating half-life of mean reversion...")
    print("-" * 70)
    
    half_life_calc = HalfLifeCalculator(
        min_half_life_days=2.0,
        max_half_life_days=60.0
    )
    
    spreads = {}
    for pair in cointegrated_pairs:
        p1 = prices[pair.asset_1]
        p2 = prices[pair.asset_2]
        spread = calc.calculate_spread(p1, p2, pair.hedge_ratio)
        spreads[pair.pair_id] = spread
    
    half_life_results = half_life_calc.calculate_for_pairs(spreads, freq='1D')
    
    print("\n   Half-life results:")
    for pair_id, (half_life, details) in half_life_results.items():
        tradable = "✓" if details.get('is_tradable', False) else "✗"
        hl_str = f"{half_life:.2f}" if not np.isinf(half_life) else "∞"
        print(f"   {tradable} {pair_id}: {hl_str} days "
              f"(κ={details.get('kappa', 0):.6f})")
    
    # Get optimal pairs
    optimal_pairs = half_life_calc.get_optimal_pairs(half_life_results)
    print(f"\n   Optimal pairs for trading (half-life 2-60 days): {len(optimal_pairs)}")
    for pair_id in optimal_pairs:
        print(f"   - {pair_id}")
    
    # Step 4: Johansen test for multiple assets
    print("\n\n5. Johansen test for multiple assets...")
    print("-" * 70)
    
    # Test group of 3 assets
    johansen_test = JohansenTest(max_lag=2)
    
    # Create DataFrame for selected assets
    test_assets = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    price_df = pd.DataFrame({asset: prices[asset] for asset in test_assets})
    
    result = johansen_test.test(price_df)
    
    if result:
        print(f"\n   Assets: {result.assets}")
        print(f"   Number of cointegrating vectors: {result.num_cointegrating_vectors}")
        
        if result.num_cointegrating_vectors > 0:
            print(f"\n   Eigenvalues: {[f'{e:.4f}' for e in result.eigenvalues]}")
            print(f"   Trace stats: {[f'{t:.4f}' for t in result.trace_stats]}")
            
            # Get portfolio weights
            weights = johansen_test.get_portfolio_weights(result, vector_index=0)
            print(f"\n   Portfolio weights (vector 0):")
            for asset, weight in weights.items():
                print(f"   - {asset}: {weight:.6f}")
            
            # Calculate portfolio series
            portfolio = johansen_test.calculate_portfolio_series(
                price_df, result, vector_index=0
            )
            print(f"\n   Portfolio Statistics:")
            print(f"   Mean: {portfolio.mean():.4f}")
            print(f"   Std Dev: {portfolio.std():.4f}")
    
    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total pairs screened: {len(prices) * (len(prices) - 1) // 2}")
    print(f"Cointegrated pairs found: {len(cointegrated_pairs)}")
    print(f"Optimal pairs for trading: {len(optimal_pairs)}")
    
    if cointegrated_pairs:
        print("\nTop recommended pairs:")
        for i, pair in enumerate(cointegrated_pairs[:3], 1):
            hl, details = half_life_results.get(pair.pair_id, (float('inf'), {}))
            tradable = "Yes" if details.get('is_tradable', False) else "No"
            print(f"   {i}. {pair.asset_1} / {pair.asset_2}")
            print(f"      P-value: {pair.p_value:.6f}, "
                  f"Hedge Ratio: {pair.hedge_ratio:.4f}, "
                  f"Half-life: {hl:.2f} days, "
                  f"Tradable: {tradable}")
    
    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    main()
