import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, AreaChart, Area } from 'recharts'
import { SpreadData, PricePoint, Signal } from '../types'

const mockSpreadData: SpreadData[] = Array.from({ length: 50 }, (_, i) => ({
  timestamp: Date.now() - (50 - i) * 60000,
  raw_spread: Math.sin(i * 0.2) * 2 + Math.random() * 0.5,
  z_score: Math.sin(i * 0.2) * 1.5 + Math.random() * 0.3,
  percentile_rank: Math.random() * 100,
  moving_average: Math.sin(i * 0.2) * 2,
  upper_band_1: Math.sin(i * 0.2) * 2 + 1,
  lower_band_1: Math.sin(i * 0.2) * 2 - 1,
  upper_band_2: Math.sin(i * 0.2) * 2 + 2,
  lower_band_2: Math.sin(i * 0.2) * 2 - 2,
}))

const mockPriceData: PricePoint[] = Array.from({ length: 50 }, (_, i) => ({
  timestamp: Date.now() - (50 - i) * 60000,
  price: 45000 + Math.random() * 1000 + i * 10,
  normalized_price: 100 + Math.sin(i * 0.2) * 5 + Math.random(),
}))

const mockSignals: Signal[] = [
  { id: '1', pair_id: '1', timestamp: new Date(Date.now() - 3600000).toISOString(), z_score: 2.1, direction: 'short', type: 'entry' },
  { id: '2', pair_id: '1', timestamp: new Date(Date.now() - 1800000).toISOString(), z_score: 0.5, direction: 'short', type: 'exit', pnl: 125.50 },
  { id: '3', pair_id: '1', timestamp: new Date(Date.now() - 900000).toISOString(), z_score: -2.2, direction: 'long', type: 'entry' },
]

export default function SpreadMonitor() {
  const [period, setPeriod] = useState('7D')
  const [selectedPair, setSelectedPair] = useState('BTC/USDT - ETH/USDT')

  const periods = ['1D', '7D', '30D', '90D', '1Y']

  return (
    <div>
      <h1 className="card-title">Spread Monitor</h1>
      
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '16px', color: '#f1f5f9' }}>{selectedPair}</h2>
          <div className="period-selector">
            {periods.map((p) => (
              <button
                key={p}
                className={`period-btn ${period === p ? 'active' : ''}`}
                onClick={() => setPeriod(p)}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="grid-2">
          <div>
            <h3 style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '12px' }}>Normalized Prices</h3>
            <div className="chart-container" style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockPriceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleTimeString()} stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#fff' }}
                    labelFormatter={(l) => new Date(l).toLocaleString()}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="normalized_price" stroke="#3b82f6" name="Asset 1" dot={false} />
                  <Line type="monotone" dataKey="price" stroke="#10b981" name="Asset 2" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '12px' }}>Z-Score</h3>
            <div className="chart-container" style={{ height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockSpreadData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleTimeString()} stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" domain={[-3, 3]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#fff' }}
                    labelFormatter={(l) => new Date(l).toLocaleString()}
                  />
                  <ReferenceLine y={2} stroke="#ef4444" strokeDasharray="3 3" />
                  <ReferenceLine y={-2} stroke="#ef4444" strokeDasharray="3 3" />
                  <ReferenceLine y={1.5} stroke="#f59e0b" strokeDasharray="3 3" />
                  <ReferenceLine y={-1.5} stroke="#f59e0b" strokeDasharray="3 3" />
                  <ReferenceLine y={0} stroke="#94a3b8" />
                  <Area type="monotone" dataKey="z_score" fill="#3b82f6" fillOpacity={0.3} stroke="#3b82f6" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h3 style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '12px' }}>Raw Spread with Bands</h3>
          <div className="chart-container" style={{ height: '250px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockSpreadData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleTimeString()} stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#fff' }}
                  labelFormatter={(l) => new Date(l).toLocaleString()}
                />
                <Legend />
                <Line type="monotone" dataKey="raw_spread" stroke="#8b5cf6" name="Raw Spread" dot={false} />
                <Line type="monotone" dataKey="moving_average" stroke="#22d3ee" name="MA" dot={false} />
                <Line type="monotone" dataKey="upper_band_1" stroke="#94a3b8" name="+1σ" dot={false} strokeDasharray="3 3" />
                <Line type="monotone" dataKey="lower_band_1" stroke="#94a3b8" name="-1σ" dot={false} strokeDasharray="3 3" />
                <Line type="monotone" dataKey="upper_band_2" stroke="#64748b" name="+2σ" dot={false} strokeDasharray="3 3" />
                <Line type="monotone" dataKey="lower_band_2" stroke="#64748b" name="-2σ" dot={false} strokeDasharray="3 3" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Signal History</h3>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Direction</th>
                <th>Z-Score</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {mockSignals.map((signal) => (
                <tr key={signal.id}>
                  <td>{new Date(signal.timestamp).toLocaleString()}</td>
                  <td>
                    <span className={`badge ${signal.type === 'entry' ? 'badge-success' : signal.type === 'exit' ? 'badge-warning' : 'badge-danger'}`}>
                      {signal.type.toUpperCase()}
                    </span>
                  </td>
                  <td className={signal.direction === 'long' ? 'positive' : 'negative'}>
                    {signal.direction.toUpperCase()}
                  </td>
                  <td>{signal.z_score.toFixed(2)}</td>
                  <td className={signal.pnl && signal.pnl > 0 ? 'positive' : signal.pnl && signal.pnl < 0 ? 'negative' : ''}>
                    {signal.pnl ? `$${signal.pnl.toFixed(2)}` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
