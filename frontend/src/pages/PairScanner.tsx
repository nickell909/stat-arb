import { useState, useMemo } from 'react'
import { CointegratedPair } from '../types'
import { Search, Filter, ArrowUpDown } from 'lucide-react'

const mockPairs: CointegratedPair[] = [
  {
    pair_id: '1',
    asset_1: 'BTC/USDT',
    asset_2: 'ETH/USDT',
    exchange_1: 'Binance',
    exchange_2: 'Binance',
    p_value: 0.001,
    hedge_ratio: 15.234,
    half_life_days: 5.2,
    coint_score: 0.95,
    current_z_score: 1.82,
    last_checked_at: new Date().toISOString()
  },
  {
    pair_id: '2',
    asset_1: 'SOL/USDT',
    asset_2: 'AVAX/USDT',
    exchange_1: 'Bybit',
    exchange_2: 'OKX',
    p_value: 0.023,
    hedge_ratio: 2.145,
    half_life_days: 12.5,
    coint_score: 0.87,
    current_z_score: -0.45,
    last_checked_at: new Date().toISOString()
  },
  {
    pair_id: '3',
    asset_1: 'BNB/USDT',
    asset_2: 'ETH/USDT',
    exchange_1: 'Binance',
    exchange_2: 'Binance',
    p_value: 0.008,
    hedge_ratio: 0.156,
    half_life_days: 3.8,
    coint_score: 0.92,
    current_z_score: 2.15,
    last_checked_at: new Date().toISOString()
  },
  {
    pair_id: '4',
    asset_1: 'XRP/USDT',
    asset_2: 'ADA/USDT',
    exchange_1: 'OKX',
    exchange_2: 'Bybit',
    p_value: 0.045,
    hedge_ratio: 1.892,
    half_life_days: 25.3,
    coint_score: 0.78,
    current_z_score: -1.67,
    last_checked_at: new Date().toISOString()
  },
]

type SortKey = keyof CointegratedPair
type SortOrder = 'asc' | 'desc'

export default function PairScanner() {
  const [searchTerm, setSearchTerm] = useState('')
  const [exchangeFilter, setExchangeFilter] = useState('all')
  const [pValueThreshold, setPValueThreshold] = useState(0.05)
  const [halfLifeMin, setHalfLifeMin] = useState(2)
  const [halfLifeMax, setHalfLifeMax] = useState(60)
  const [zScoreAbs, setZScoreAbs] = useState(0)
  const [sortKey, setSortKey] = useState<SortKey>('coint_score')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const filteredAndSortedPairs = useMemo(() => {
    let result = [...mockPairs]

    if (searchTerm) {
      result = result.filter(pair =>
        pair.asset_1.toLowerCase().includes(searchTerm.toLowerCase()) ||
        pair.asset_2.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (exchangeFilter !== 'all') {
      result = result.filter(pair =>
        pair.exchange_1 === exchangeFilter || pair.exchange_2 === exchangeFilter
      )
    }

    result = result.filter(pair =>
      pair.p_value <= pValueThreshold &&
      pair.half_life_days >= halfLifeMin &&
      pair.half_life_days <= halfLifeMax &&
      Math.abs(pair.current_z_score) >= zScoreAbs
    )

    result.sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      }
      return sortOrder === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
    })

    return result
  }, [searchTerm, exchangeFilter, pValueThreshold, halfLifeMin, halfLifeMax, zScoreAbs, sortKey, sortOrder])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortOrder('desc')
    }
  }

  const getZScoreBadge = (zScore: number) => {
    const absZ = Math.abs(zScore)
    if (absZ >= 2) return <span className="badge badge-danger">{zScore.toFixed(2)}</span>
    if (absZ >= 1.5) return <span className="badge badge-warning">{zScore.toFixed(2)}</span>
    return <span className="badge badge-success">{zScore.toFixed(2)}</span>
  }

  return (
    <div>
      <h1 className="card-title">Pair Scanner</h1>
      
      <div className="card">
        <div className="filter-row">
          <div style={{ flex: 1, minWidth: '200px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Search size={18} />
              <input
                type="text"
                className="input"
                placeholder="Search pairs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          <select
            className="select"
            value={exchangeFilter}
            onChange={(e) => setExchangeFilter(e.target.value)}
          >
            <option value="all">All Exchanges</option>
            <option value="Binance">Binance</option>
            <option value="Bybit">Bybit</option>
            <option value="OKX">OKX</option>
          </select>

          <div>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
              Max P-Value: {pValueThreshold}
            </label>
            <input
              type="range"
              min="0.001"
              max="0.1"
              step="0.001"
              value={pValueThreshold}
              onChange={(e) => setPValueThreshold(parseFloat(e.target.value))}
              style={{ width: '120px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
              Min |Z-Score|: {zScoreAbs}
            </label>
            <input
              type="range"
              min="0"
              max="3"
              step="0.1"
              value={zScoreAbs}
              onChange={(e) => setZScoreAbs(parseFloat(e.target.value))}
              style={{ width: '120px' }}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('asset_1')} style={{ cursor: 'pointer' }}>
                  Pair <ArrowUpDown size={12} style={{ marginLeft: '4px' }} />
                </th>
                <th>Exchanges</th>
                <th onClick={() => handleSort('p_value')} style={{ cursor: 'pointer' }}>
                  P-Value <ArrowUpDown size={12} style={{ marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('hedge_ratio')} style={{ cursor: 'pointer' }}>
                  Hedge Ratio <ArrowUpDown size={12} style={{ marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('half_life_days')} style={{ cursor: 'pointer' }}>
                  Half-Life (days) <ArrowUpDown size={12} style={{ marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('coint_score')} style={{ cursor: 'pointer' }}>
                  Score <ArrowUpDown size={12} style={{ marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('current_z_score')} style={{ cursor: 'pointer' }}>
                  Z-Score <ArrowUpDown size={12} style={{ marginLeft: '4px' }} />
                </th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedPairs.map((pair) => (
                <tr key={pair.pair_id}>
                  <td>
                    <strong>{pair.asset_1}</strong> / {pair.asset_2}
                  </td>
                  <td>{pair.exchange_1} / {pair.exchange_2}</td>
                  <td className={pair.p_value < 0.01 ? 'positive' : ''}>{pair.p_value.toFixed(4)}</td>
                  <td>{pair.hedge_ratio.toFixed(4)}</td>
                  <td>{pair.half_life_days.toFixed(1)}</td>
                  <td>{(pair.coint_score * 100).toFixed(0)}%</td>
                  <td>{getZScoreBadge(pair.current_z_score)}</td>
                  <td>{new Date(pair.last_checked_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredAndSortedPairs.length === 0 && (
          <p style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
            No pairs found matching your criteria
          </p>
        )}
      </div>
    </div>
  )
}
