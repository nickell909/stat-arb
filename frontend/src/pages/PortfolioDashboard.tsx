import { useState } from 'react'
import { PortfolioPosition, CorrelationMatrix } from '../types'
import { TrendingUp, DollarSign, Activity, AlertTriangle } from 'lucide-react'

const mockPositions: PortfolioPosition[] = [
  {
    pair_id: '1',
    direction: 'long',
    entry_z_score: -2.1,
    current_z_score: -0.8,
    entry_time: new Date(Date.now() - 7200000).toISOString(),
    pnl: 342.50,
    size: 10000
  },
  {
    pair_id: '2',
    direction: 'short',
    entry_z_score: 2.3,
    current_z_score: 1.1,
    entry_time: new Date(Date.now() - 14400000).toISOString(),
    pnl: 189.75,
    size: 8000
  },
  {
    pair_id: '3',
    direction: 'long',
    entry_z_score: -1.8,
    current_z_score: -0.3,
    entry_time: new Date(Date.now() - 28800000).toISOString(),
    pnl: -56.25,
    size: 5000
  },
]

const mockCorrelations: CorrelationMatrix = {
  assets: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'],
  matrix: [
    [1.00, 0.85, 0.72, 0.68],
    [0.85, 1.00, 0.79, 0.74],
    [0.72, 0.79, 1.00, 0.65],
    [0.68, 0.74, 0.65, 1.00]
  ]
}

const mockAlerts = [
  { id: '1', type: 'warning', message: 'BTC/USDT-ETH/USDT Z-Score exceeded 2.0', time: new Date(Date.now() - 300000).toISOString() },
  { id: '2', type: 'info', message: 'SOL/USDT-AVAX/USDT pair cointegration score updated', time: new Date(Date.now() - 900000).toISOString() },
  { id: '3', type: 'success', message: 'Position closed with +$125.50 profit', time: new Date(Date.now() - 3600000).toISOString() },
]

export default function PortfolioDashboard() {
  const totalPnl = mockPositions.reduce((sum, pos) => sum + pos.pnl, 0)
  const totalSize = mockPositions.reduce((sum, pos) => sum + pos.size, 0)

  const getCorrelationColor = (value: number) => {
    if (value >= 0.8) return '#ef4444'
    if (value >= 0.6) return '#f59e0b'
    return '#059669'
  }

  return (
    <div>
      <h1 className="card-title">Portfolio Dashboard</h1>

      <div className="grid-3" style={{ marginBottom: '20px' }}>
        <div className="stat-card">
          <div className="stat-label">Total PnL</div>
          <div className={`stat-value ${totalPnl >= 0 ? 'positive' : 'negative'}`}>
            ${totalPnl.toFixed(2)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Exposure</div>
          <div className="stat-value">${totalSize.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Open Positions</div>
          <div className="stat-value">{mockPositions.length}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 className="card-title">Open Positions</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Pair</th>
                  <th>Direction</th>
                  <th>Entry Z</th>
                  <th>Current Z</th>
                  <th>PnL</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {mockPositions.map((pos, index) => (
                  <tr key={index}>
                    <td><strong>Pair #{pos.pair_id}</strong></td>
                    <td className={pos.direction === 'long' ? 'positive' : 'negative'}>
                      {pos.direction.toUpperCase()}
                    </td>
                    <td>{pos.entry_z_score.toFixed(2)}</td>
                    <td>{pos.current_z_score.toFixed(2)}</td>
                    <td className={pos.pnl >= 0 ? 'positive' : 'negative'}>
                      ${pos.pnl.toFixed(2)}
                    </td>
                    <td>${pos.size.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h3 className="card-title">Recent Alerts</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {mockAlerts.map((alert) => (
              <div 
                key={alert.id} 
                style={{ 
                  padding: '12px', 
                  backgroundColor: alert.type === 'warning' ? '#d9770620' : alert.type === 'success' ? '#05966920' : '#3b82f620',
                  borderRadius: '8px',
                  borderLeft: `3px solid ${alert.type === 'warning' ? '#d97706' : alert.type === 'success' ? '#059669' : '#3b82f6'}`
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  {alert.type === 'warning' ? <AlertTriangle size={16} color="#d97706" /> : <Activity size={16} color="#3b82f6" />}
                  <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                    {new Date(alert.time).toLocaleTimeString()}
                  </span>
                </div>
                <div style={{ color: '#fff' }}>{alert.message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Correlation Heatmap</h3>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th></th>
                {mockCorrelations.assets.map((asset) => (
                  <th key={asset}>{asset}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mockCorrelations.assets.map((rowAsset, rowIndex) => (
                <tr key={rowAsset}>
                  <td><strong>{rowAsset}</strong></td>
                  {mockCorrelations.matrix[rowIndex].map((value, colIndex) => (
                    <td 
                      key={colIndex} 
                      style={{ 
                        backgroundColor: `${getCorrelationColor(value)}${Math.floor(Math.abs(value) * 50).toString(16).padStart(2, '0')}`,
                        color: value > 0.5 ? '#fff' : '#94a3b8'
                      }}
                    >
                      {value.toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Watch List</h3>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Pair</th>
                <th>Z-Score</th>
                <th>Half-Life</th>
                <th>Score</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>BTC/USDT - ETH/USDT</td>
                <td>1.82</td>
                <td>5.2 days</td>
                <td>95%</td>
                <td><span className="badge badge-warning">Monitor</span></td>
              </tr>
              <tr>
                <td>SOL/USDT - AVAX/USDT</td>
                <td>-0.45</td>
                <td>12.5 days</td>
                <td>87%</td>
                <td><span className="badge badge-success">Normal</span></td>
              </tr>
              <tr>
                <td>BNB/USDT - ETH/USDT</td>
                <td>2.15</td>
                <td>3.8 days</td>
                <td>92%</td>
                <td><span className="badge badge-danger">Signal</span></td>
              </tr>
              <tr>
                <td>XRP/USDT - ADA/USDT</td>
                <td>-1.67</td>
                <td>25.3 days</td>
                <td>78%</td>
                <td><span className="badge badge-warning">Monitor</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
