"""
Data models for cointegration analysis results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class CointegrationPair:
    """Represents a cointegrated pair of assets."""
    pair_id: str
    asset_1: str
    asset_2: str
    hedge_ratio: float
    p_value: float
    coint_score: float
    half_life_days: float
    last_checked_at: datetime
    correlation: float = 0.0
    adf_stat_1: float = 0.0
    adf_stat_2: float = 0.0
    adf_stat_residual: float = 0.0
    is_stationary_1: bool = False
    is_stationary_2: bool = False
    method: str = "ols"  # ols or kalman
    
    def to_dict(self) -> dict:
        return {
            'pair_id': self.pair_id,
            'asset_1': self.asset_1,
            'asset_2': self.asset_2,
            'hedge_ratio': self.hedge_ratio,
            'p_value': self.p_value,
            'coint_score': self.coint_score,
            'half_life_days': self.half_life_days,
            'last_checked_at': self.last_checked_at.isoformat(),
            'correlation': self.correlation,
            'adf_stat_1': self.adf_stat_1,
            'adf_stat_2': self.adf_stat_2,
            'adf_stat_residual': self.adf_stat_residual,
            'is_stationary_1': self.is_stationary_1,
            'is_stationary_2': self.is_stationary_2,
            'method': self.method
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CointegrationPair':
        return cls(
            pair_id=data['pair_id'],
            asset_1=data['asset_1'],
            asset_2=data['asset_2'],
            hedge_ratio=data['hedge_ratio'],
            p_value=data['p_value'],
            coint_score=data['coint_score'],
            half_life_days=data['half_life_days'],
            last_checked_at=datetime.fromisoformat(data['last_checked_at']),
            correlation=data.get('correlation', 0.0),
            adf_stat_1=data.get('adf_stat_1', 0.0),
            adf_stat_2=data.get('adf_stat_2', 0.0),
            adf_stat_residual=data.get('adf_stat_residual', 0.0),
            is_stationary_1=data.get('is_stationary_1', False),
            is_stationary_2=data.get('is_stationary_2', False),
            method=data.get('method', 'ols')
        )


@dataclass
class JohansenResult:
    """Represents results from Johansen test for multiple assets."""
    assets: List[str]
    eigenvalues: List[float]
    trace_stats: List[float]
    critical_values_90: List[float]
    critical_values_95: List[float]
    critical_values_99: List[float]
    num_cointegrating_vectors: int
    cointegrating_vectors: List[List[float]]
    
    def to_dict(self) -> dict:
        return {
            'assets': self.assets,
            'eigenvalues': self.eigenvalues,
            'trace_stats': self.trace_stats,
            'critical_values_90': self.critical_values_90,
            'critical_values_95': self.critical_values_95,
            'critical_values_99': self.critical_values_99,
            'num_cointegrating_vectors': self.num_cointegrating_vectors,
            'cointegrating_vectors': self.cointegrating_vectors
        }


@dataclass
class HedgeRatioTimeSeries:
    """Time series of hedge ratios from Kalman filter."""
    timestamps: List[datetime]
    hedge_ratios: List[float]
    std_errors: List[float] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'timestamps': [t.isoformat() for t in self.timestamps],
            'hedge_ratios': self.hedge_ratios,
            'std_errors': self.std_errors
        }
