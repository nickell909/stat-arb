export interface CointegratedPair {
  pair_id: string;
  asset_1: string;
  asset_2: string;
  exchange_1: string;
  exchange_2: string;
  p_value: number;
  hedge_ratio: number;
  half_life_days: number;
  coint_score: number;
  current_z_score: number;
  last_checked_at: string;
}

export interface SpreadData {
  timestamp: number;
  raw_spread: number;
  z_score: number;
  percentile_rank: number;
  moving_average: number;
  upper_band_1: number;
  lower_band_1: number;
  upper_band_2: number;
  lower_band_2: number;
}

export interface PricePoint {
  timestamp: number;
  price: number;
  normalized_price: number;
}

export interface Signal {
  id: string;
  pair_id: string;
  timestamp: string;
  z_score: number;
  direction: 'long' | 'short';
  type: 'entry' | 'exit' | 'stop';
  pnl?: number;
}

export interface SyntheticAsset {
  id: string;
  name: string;
  components: SyntheticComponent[];
  normalized_value: number;
  created_at: string;
}

export interface SyntheticComponent {
  symbol: string;
  exchange: string;
  weight: number;
}

export interface PortfolioPosition {
  pair_id: string;
  direction: 'long' | 'short';
  entry_z_score: number;
  current_z_score: number;
  entry_time: string;
  pnl: number;
  size: number;
}

export interface CorrelationMatrix {
  assets: string[];
  matrix: number[][];
}
