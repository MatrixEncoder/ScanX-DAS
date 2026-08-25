import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Assess from './pages/Assess'
import Targets from './pages/Targets'
import Crawls from './pages/Crawls'
import Endpoints from './pages/Endpoints'
import Reports from './pages/Reports'
import GithubScan from './pages/GithubScan'
import AttackSurface from './pages/AttackSurface'

function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/"              element={<Dashboard />} />
          <Route path="/assess"        element={<Assess />} />
          <Route path="/targets"       element={<Targets />} />
          <Route path="/crawls"        element={<Crawls />} />
          <Route path="/endpoints"     element={<Endpoints />} />
          <Route path="/github"        element={<GithubScan />} />
          <Route path="/attack-surface" element={<AttackSurface />} />
          <Route path="/reports"       element={<Reports />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app/*" element={<AppLayout />} />
        <Route path="*" element={<AppLayout />} />
      </Routes>
    </BrowserRouter>
  )
}
