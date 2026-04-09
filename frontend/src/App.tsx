import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, ScanLine, Activity, Box, Settings } from 'lucide-react'
import PairScanner from './pages/PairScanner'
import SpreadMonitor from './pages/SpreadMonitor'
import SyntheticBuilder from './pages/SyntheticBuilder'
import PortfolioDashboard from './pages/PortfolioDashboard'

function Sidebar() {
  const location = useLocation()
  
  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/scanner', icon: ScanLine, label: 'Pair Scanner' },
    { path: '/monitor', icon: Activity, label: 'Spread Monitor' },
    { path: '/synthetic', icon: Box, label: 'Synthetic Builder' },
    { path: '/portfolio', icon: LayoutDashboard, label: 'Portfolio' },
  ]

  return (
    <div className="sidebar">
      <h2 style={{ color: '#fff', marginBottom: '24px', fontSize: '20px' }}>
        Crypto Arbitrage
      </h2>
      <nav>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Sidebar />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<PortfolioDashboard />} />
            <Route path="/scanner" element={<PairScanner />} />
            <Route path="/monitor" element={<SpreadMonitor />} />
            <Route path="/monitor/:pairId" element={<SpreadMonitor />} />
            <Route path="/synthetic" element={<SyntheticBuilder />} />
            <Route path="/portfolio" element={<PortfolioDashboard />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
