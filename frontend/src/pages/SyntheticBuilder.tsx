import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { SyntheticComponent, SyntheticAsset } from '../types'
import { Plus, Trash2, TrendingUp } from 'lucide-react'

const mockChart = Array.from({ length: 30 }, (_, i) => ({
  timestamp: Date.now() - (30 - i) * 86400000,
  value: 100 + Math.sin(i * 0.3) * 5 + Math.random() * 2,
}))

export default function SyntheticBuilder() {
  const [components, setComponents] = useState<SyntheticComponent[]>([
    { symbol: 'BTC/USDT', exchange: 'Binance', weight: 40 },
    { symbol: 'ETH/USDT', exchange: 'Binance', weight: 35 },
    { symbol: 'SOL/USDT', exchange: 'Bybit', weight: 25 },
  ])
  const [name, setName] = useState('')
  const [newSymbol, setNewSymbol] = useState('')

  const totalWeight = components.reduce((sum, c) => sum + c.weight, 0)

  const addComponent = () => {
    if (newSymbol && components.length < 10) {
      const remainingWeight = 100 - totalWeight
      setComponents([...components, { 
        symbol: newSymbol, 
        exchange: 'Binance', 
        weight: remainingWeight > 0 ? remainingWeight : 10 
      }])
      setNewSymbol('')
    }
  }

  const removeComponent = (index: number) => {
    setComponents(components.filter((_, i) => i !== index))
  }

  const updateWeight = (index: number, weight: number) => {
    const updated = [...components]
    updated[index].weight = weight
    setComponents(updated)
  }

  const optimizePCA = () => {
    const equalWeight = 100 / components.length
    setComponents(components.map(c => ({ ...c, weight: parseFloat(equalWeight.toFixed(2)) })))
  }

  const normalizeWeights = () => {
    if (totalWeight === 0) return
    const factor = 100 / totalWeight
    setComponents(components.map(c => ({ ...c, weight: parseFloat((c.weight * factor).toFixed(2)) }))
    )
  }

  return (
    <div>
      <h1 className="card-title">Synthetic Builder</h1>
      
      <div className="grid-2">
        <div className="card">
          <h3 className="card-title">Basket Components</h3>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
              Synthetic Name
            </label>
            <input
              type="text"
              className="input"
              placeholder="My Custom Basket"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '8px' }}>
              Add Asset
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                className="input"
                placeholder="BTC/USDT"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addComponent()}
              />
              <button className="btn btn-primary" onClick={addComponent}>
                <Plus size={18} />
              </button>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            {components.map((component, index) => (
              <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', padding: '8px', backgroundColor: '#0f172a', borderRadius: '6px' }}>
                <div style={{ flex: 1 }}>
                  <strong style={{ color: '#fff' }}>{component.symbol}</strong>
                  <span style={{ fontSize: '12px', color: '#94a3b8', marginLeft: '8px' }}>{component.exchange}</span>
                </div>
                <input
                  type="number"
                  className="input"
                  style={{ width: '80px' }}
                  value={component.weight}
                  onChange={(e) => updateWeight(index, parseFloat(e.target.value) || 0)}
                  min="0"
                  max="100"
                />
                <span style={{ color: '#94a3b8', fontSize: '12px' }}>%</span>
                <button 
                  onClick={() => removeComponent(index)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>

          <div style={{ padding: '12px', backgroundColor: totalWeight === 100 ? '#05966920' : '#d9770620', borderRadius: '6px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#94a3b8' }}>Total Weight:</span>
              <span className={totalWeight === 100 ? 'positive' : 'negative'} style={{ fontWeight: 'bold' }}>
                {totalWeight.toFixed(1)}%
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={optimizePCA}>
              Optimize via PCA
            </button>
            <button className="btn btn-secondary" onClick={normalizeWeights}>
              Normalize to 100%
            </button>
            <button 
              className="btn btn-primary" 
              disabled={totalWeight !== 100 || !name}
              style={{ opacity: totalWeight !== 100 || !name ? 0.5 : 1 }}
            >
              Save Synthetic
            </button>
          </div>
        </div>

        <div className="card">
          <h3 className="card-title">Preview (Normalized to 100)</h3>
          <div className="chart-container" style={{ height: '400px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(t) => new Date(t).toLocaleDateString()} 
                  stroke="#94a3b8" 
                />
                <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#fff' }}
                  labelFormatter={(l) => new Date(l).toLocaleDateString()}
                  formatter={(value: number) => [value.toFixed(2), 'Value']}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#3b82f6" 
                  name={name || 'Synthetic'} 
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div style={{ marginTop: '20px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            <div className="stat-card">
              <div className="stat-label">Current Value</div>
              <div className="stat-value">102.45</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">24h Change</div>
              <div className="stat-value positive">+2.34%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Volatility</div>
              <div className="stat-value" style={{ fontSize: '20px' }}>1.2%</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Saved Synthetics</h3>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Components</th>
                <th>Current Value</th>
                <th>24h Change</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Crypto Blue Chip</strong></td>
                <td>BTC (50%), ETH (30%), SOL (20%)</td>
                <td>105.23</td>
                <td className="positive">+3.12%</td>
                <td>2024-01-15</td>
                <td><button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }}>View</button></td>
              </tr>
              <tr>
                <td><strong>DeFi Basket</strong></td>
                <td>UNI (40%), AAVE (35%), MKR (25%)</td>
                <td>98.76</td>
                <td className="negative">-1.45%</td>
                <td>2024-01-10</td>
                <td><button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }}>View</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
