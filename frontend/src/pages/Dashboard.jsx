import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/client'
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts'
import {
  Target, Radar, MapPin, Lock, AlertTriangle, Activity,
  Crosshair, ArrowUpRight, Plus, Layers, BarChart3, Github, Zap, FileSearch,
} from 'lucide-react'

const STATUS_LABELS = {
  created: 'Created', queued: 'Queued', running: 'Running',
  completed: 'Completed', failed: 'Failed',
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] || status}</span>
}

function KPICard({ label, value, color, icon: Icon, sub }) {
  return (
    <div className="kpi-card" style={{ '--kpi-accent': color }}>
      <div className="kpi-top">
        <div className="kpi-label">{label}</div>
        <div className="kpi-icon-tile" style={{ background: `${color}22`, color }}>
          <Icon size={16} />
        </div>
      </div>
      <div className="kpi-value" style={{ color }}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

function PipelineNode({ label, value, color, icon: Icon, note }) {
  return (
    <div className="pipeline-node">
      <div className="pn-icon" style={{ background: `${color}22`, color }}>
        <Icon size={14} />
      </div>
      <div className="pn-value" style={{ color }}>{value}</div>
      <div className="pn-label">{label}</div>
      <div className="pn-note">{note}</div>
    </div>
  )
}

function Panel({ title, icon: Icon, accent, right, children }) {
  return (
    <div className="card">
      <div className="panel-header">
        <div className="panel-title">
          <Icon size={15} color={accent} /> {title}
        </div>
        {right}
      </div>
      {children}
    </div>
  )
}

function DonutCard({ title, icon, accent, data, colors, total, totalLabel, center }) {
  const legend = data.map((d, i) => ({ ...d, color: colors[i % colors.length] }))
  return (
    <Panel title={title} icon={icon} accent={accent}>
      <div className="donut-wrap">
        <div className="donut">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%" cy="50%"
                innerRadius={46} outerRadius={68}
                paddingAngle={3} dataKey="value"
                stroke="none"
              >
                {legend.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 8, fontSize: 13 }}
                labelStyle={{ color: '#e6edf3', fontWeight: 600 }}
                itemStyle={{ color: '#c6cdd8' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="donut-center">
            <div className="donut-center-value">{center}</div>
            <div className="donut-center-label">{totalLabel}</div>
          </div>
        </div>
        <div className="legend">
          {legend.map(s => (
            <div key={s.name} className="legend-row">
              <span className="legend-dot" style={{ background: s.color }} />
              <span className="legend-label">{s.name}</span>
              <span className="legend-value">{s.value}</span>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  )
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try {
      const res = await getDashboard()
      setData(res.data)
      setError(null)
    } catch {
      setError('Could not connect to Scan-X backend. Make sure it is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return (
    <div className="loading"><div className="spinner" /><span style={{ fontSize: 14 }}>Connecting to backend...</span></div>
  )

  if (error) return (
    <div style={{ padding: 40 }}>
      <div className="card" style={{ borderColor: 'rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.05)' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <AlertTriangle color="#ef4444" size={20} style={{ marginTop: 2 }} />
          <div>
            <div style={{ fontWeight: 700, color: '#f87171', marginBottom: 6, fontSize: 14 }}>Backend Offline</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 14.5 }}>{error}</div>
          </div>
        </div>
      </div>
    </div>
  )

  const recentCrawls = data.recent_crawls || []
  const bySource = data.endpoints_by_source || {}
  const byMethod = data.endpoints_by_method || {}

  const sourceData = [
    { name: 'Links', value: bySource.link || 0 },
    { name: 'Forms', value: bySource.form || 0 },
    { name: 'JavaScript', value: bySource.js || 0 },
    { name: 'Wordlist', value: bySource.wordlist || 0 },
  ]
  const sourceColors = ['#3b82f6', '#eab308', '#a855f7', '#ef4444']

  const statusData = [
    { name: 'Completed', value: data.completed_crawls || 0 },
    { name: 'Failed', value: data.failed_crawls || 0 },
    { name: 'Running', value: data.running_crawls || 0 },
  ]
  const statusColors = ['#22c55e', '#ef4444', '#eab308']

  const methodData = Object.entries(byMethod).map(([method, count]) => ({ method, count }))
  const maxEndpoints = Math.max(1, ...recentCrawls.map(c => c.total_endpoints || 0))

  return (
    <div>
      {/* Header */}
      <div className="dash-header">
        <div>
          <h1>Dashboard</h1>
          <p>Security assessment overview</p>
        </div>
        <div className="dash-header-actions">
          <span className="status-chip"><span className="dot" />Backend online</span>
          <button className="btn btn-primary" onClick={() => navigate('/app/assess')}>
            <Plus size={15} /> New Assessment
          </button>
        </div>
      </div>

      {/* Discovery */}
      <div className="section-label">Discovery</div>
      <div className="kpi-grid">
        <KPICard label="Targets" value={data.total_targets} color="#a855f7" icon={Target} sub="Registered apps" />
        <KPICard label="Crawls" value={data.total_crawls} color="#22c55e" icon={Radar} sub="Scan sessions" />
        <KPICard label="Endpoints" value={data.total_endpoints} color="#3b82f6" icon={MapPin} sub="Discovered URLs" />
        <KPICard label="API Endpoints" value={data.api_endpoints} color="#06b6d4" icon={Activity} sub="REST / GraphQL" />
        <KPICard label="Login Forms" value={data.login_forms} color="#f97316" icon={Lock} sub="Auth surfaces" />
      </div>

      {/* Assessment pipeline */}
      <div className="section-label">Assessment Pipeline</div>
      <div className="card">
        <div className="panel-header">
          <div className="panel-title">
            <Zap size={15} color="#fbbf24" /> End-to-end coverage
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/app/assess')}>
            Run assessment <ArrowUpRight size={12} />
          </button>
        </div>
        <div className="pipeline">
          <PipelineNode label="Web Recon" value={data.web_assessments} color="#22c55e" icon={Radar} note="URL only" />
          <PipelineNode label="Repo Scan" value={data.repo_assessments} color="#a855f7" icon={Github} note="Source code" />
          <PipelineNode label="Full Assessment" value={data.full_assessments} color="#eab308" icon={Crosshair} note="Both combined" />
          <PipelineNode label="Correlations" value={data.source_mappings} color="#06b6d4" icon={Layers} note="Endpoint ↔ file" />
          <PipelineNode label="Linked Findings" value={data.correlation_findings} color="#ef4444" icon={FileSearch} note="Issues chained" />
        </div>
      </div>

      {/* Analytics */}
      <div className="section-label">Analytics</div>
      <div className="chart-grid">
        <DonutCard
          title="Endpoint Sources" icon={Layers} accent="#3b82f6"
          data={sourceData} colors={sourceColors}
          center={data.total_endpoints} totalLabel="endpoints"
        />
        <DonutCard
          title="Crawl Status" icon={Radar} accent="#22c55e"
          data={statusData} colors={statusColors}
          center={data.total_crawls} totalLabel="crawls"
        />
        <Panel title="Endpoints by Method" icon={BarChart3} accent="#a855f7">
          <div style={{ height: 176 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={methodData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <XAxis dataKey="method" tick={{ fontSize: 13, fill: '#9aa4b2' }} axisLine={false} tickLine={false} />
                <YAxis
                  tick={{ fontSize: 13, fill: '#9aa4b2' }}
                  axisLine={false}
                  tickLine={false}
                  width={44}
                  allowDecimals={false}
                  tickFormatter={(v) => String(v)}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ background: '#161b22', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 8, fontSize: 13 }}
                  labelStyle={{ color: '#e6edf3', fontWeight: 600 }}
                  itemStyle={{ color: '#c6cdd8' }}
                />
                <Bar dataKey="count" radius={[5, 5, 0, 0]} maxBarSize={46}>
                  {methodData.map((_, i) => (
                    <Cell key={i} fill={['#22c55e', '#3b82f6', '#eab308', '#ef4444', '#a855f7'][i % 5]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      {/* Activity */}
      <div className="section-label">Activity</div>
      <Panel
        title="Recent Crawls" icon={Radar} accent="#22c55e"
        right={recentCrawls.length > 0 && (
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/app/crawls')}>
            View all <ArrowUpRight size={12} />
          </button>
        )}
      >
        {recentCrawls.length === 0 ? (
          <div className="empty-state">
            <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.5 }}>🔍</div>
            <p>No crawls yet. Add a target and start discovering endpoints.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>Endpoints</th>
                  <th>Pages</th>
                  <th>Forms</th>
                  <th>Duration</th>
                  <th>Requests</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {recentCrawls.map(c => (
                  <tr key={c.id}>
                    <td className="mono" style={{ color: 'var(--text-muted)' }}>#{c.id}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td>
                      <div className="cell-bar">
                        <strong>{c.total_endpoints}</strong>
                        <span className="mini-bar">
                          <i
                            className="mini-bar-fill"
                            style={{
                              width: `${Math.max(6, Math.round(((c.total_endpoints || 0) / maxEndpoints) * 100))}%`,
                              background: '#3b82f6',
                            }}
                          />
                        </span>
                      </div>
                    </td>
                    <td>{c.pages_crawled}</td>
                    <td>{c.forms_found}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{(c.crawl_duration || 0).toFixed(1)}s</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{c.total_requests}</td>
                    <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {new Date(c.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
