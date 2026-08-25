import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/client'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import { Target, Radar, MapPin, Lock, AlertTriangle, Activity, Zap, Shield, Crosshair, FileCode, ExternalLink, TrendingUp, ArrowUpRight } from 'lucide-react'

const STATUS_LABELS = {
  created: 'Created', queued: 'Queued', running: 'Running',
  completed: 'Completed', failed: 'Failed',
}

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
  info: '#6366f1',
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] || status}</span>
}

function KPICard({ label, value, color, icon: Icon, sub }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color }}>{value}</div>
      {sub && <div className="text-sm text-muted" style={{ marginTop: 6 }}>{sub}</div>}
      <div style={{ position: 'absolute', top: 14, right: 14, opacity: 0.1 }}>
        <Icon size={32} color={color} />
      </div>
    </div>
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
    <div className="loading"><div className="spinner" /><span style={{ fontSize: 13 }}>Connecting to backend...</span></div>
  )

  if (error) return (
    <div style={{ padding: 40 }}>
      <div className="card" style={{ borderColor: 'rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.04)' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <AlertTriangle color="#ef4444" size={20} style={{ marginTop: 2 }} />
          <div>
            <div style={{ fontWeight: 700, color: '#ef4444', marginBottom: 6, fontSize: 14 }}>Backend Offline</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{error}</div>
          </div>
        </div>
      </div>
    </div>
  )

  const recentCrawls = data.recent_crawls || []
  const topEndpoints = data.recent_endpoints || []

  return (
    <div>
      {/* Header */}
      <div className="page-actions" style={{ marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 2 }}>Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Security assessment overview</p>
        </div>
        <div className="pill-group">
          <button className="pill active">24H</button>
          <button className="pill">7D</button>
          <button className="pill">30D</button>
        </div>
      </div>

      {/* Primary KPIs */}
      <div className="kpi-grid">
        <KPICard label="Targets" value={data.total_targets} color="#a855f7" icon={Target} />
        <KPICard label="Crawls" value={data.total_crawls} color="#22c55e" icon={Radar} />
        <KPICard label="Endpoints" value={data.total_endpoints} color="#3b82f6" icon={MapPin} />
        <KPICard label="API Endpoints" value={data.api_endpoints} color="#06b6d4" icon={Activity} />
        <KPICard label="Login Forms" value={data.login_forms} color="#f97316" icon={Lock} />
      </div>

      {/* Assessment KPIs */}
      <div className="kpi-grid">
        <KPICard label="Web Assessments" value={data.web_assessments} color="#22c55e" icon={Shield} sub="URL only" />
        <KPICard label="Repo Assessments" value={data.repo_assessments} color="#a855f7" icon={Shield} sub="GitHub repos" />
        <KPICard label="Full Assessments" value={data.full_assessments} color="#eab308" icon={Crosshair} sub="Combined" />
        {data.full_assessments > 0 && (
          <>
            <KPICard label="Correlated" value={data.correlated_endpoints} color="#06b6d4" icon={Crosshair} sub="Matched endpoints" />
            <KPICard label="Linked Findings" value={data.correlation_findings} color="#ef4444" icon={AlertTriangle} sub="Security issues" />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Endpoint Sources */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--text-secondary)' }}>Endpoint Sources</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div style={{ width: 140, height: 140 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Links', value: data.endpoints_by_source?.link || 0 },
                      { name: 'Forms', value: data.endpoints_by_source?.form || 0 },
                      { name: 'JavaScript', value: data.endpoints_by_source?.js || 0 },
                      { name: 'Wordlist', value: data.endpoints_by_source?.wordlist || 0 },
                    ]}
                    cx="50%" cy="50%" innerRadius={40} outerRadius={60}
                    paddingAngle={3} dataKey="value"
                  >
                    {['#3b82f6', '#eab308', '#a855f7', '#ef4444'].map((c, i) => <Cell key={i} fill={c} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ flex: 1, fontSize: 12 }}>
              {[
                { label: 'Links', value: data.endpoints_by_source?.link || 0, color: '#3b82f6' },
                { label: 'Forms', value: data.endpoints_by_source?.form || 0, color: '#eab308' },
                { label: 'JavaScript', value: data.endpoints_by_source?.js || 0, color: '#a855f7' },
                { label: 'Wordlist', value: data.endpoints_by_source?.wordlist || 0, color: '#ef4444' },
              ].map(s => (
                <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                  <span style={{ color: 'var(--text-secondary)', flex: 1 }}>{s.label}</span>
                  <span style={{ fontWeight: 600 }}>{s.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Status Distribution */}
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--text-secondary)' }}>Crawl Status</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div style={{ width: 140, height: 140 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Completed', value: data.completed_crawls || 0 },
                      { name: 'Failed', value: data.failed_crawls || 0 },
                      { name: 'Running', value: data.running_crawls || 0 },
                    ]}
                    cx="50%" cy="50%" innerRadius={40} outerRadius={60}
                    paddingAngle={3} dataKey="value"
                  >
                    <Cell fill="#22c55e" />
                    <Cell fill="#ef4444" />
                    <Cell fill="#eab308" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ flex: 1, fontSize: 12 }}>
              {[
                { label: 'Completed', value: data.completed_crawls || 0, color: '#22c55e' },
                { label: 'Failed', value: data.failed_crawls || 0, color: '#ef4444' },
                { label: 'Running', value: data.running_crawls || 0, color: '#eab308' },
              ].map(s => (
                <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color, flexShrink: 0 }} />
                  <span style={{ color: 'var(--text-secondary)', flex: 1 }}>{s.label}</span>
                  <span style={{ fontWeight: 600 }}>{s.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Endpoints by method chart */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--text-secondary)' }}>Endpoints by Method</div>
        <div style={{ height: 160 }}>
          <ResponsiveContainer>
            <BarChart data={Object.entries(data.endpoints_by_method || {}).map(([method, count]) => ({ method, count }))}>
              <XAxis dataKey="method" tick={{ fontSize: 11, fill: '#555' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#555' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip
                contentStyle={{ background: '#1a1a1a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#aaa' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {(Object.entries(data.endpoints_by_method || {})).map(([method], i) => (
                  <Cell key={method} fill={['#22c55e', '#3b82f6', '#eab308', '#ef4444'][i % 4]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Crawls */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)' }}>Recent Crawls</div>
          {recentCrawls.length > 0 && (
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/app/crawls')}>
              View all <ArrowUpRight size={12} />
            </button>
          )}
        </div>
        {recentCrawls.length === 0 ? (
          <div className="empty-state">
            <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.3 }}>🔍</div>
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
                    <td style={{ fontWeight: 600 }}>{c.total_endpoints}</td>
                    <td className="text-sm" style={{ color: 'var(--text-muted)' }}>{c.crawl_duration.toFixed(1)}s</td>
                    <td className="text-sm" style={{ color: 'var(--text-muted)' }}>{c.total_requests}</td>
                    <td className="text-sm" style={{ color: 'var(--text-muted)' }}>{new Date(c.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
