import { useEffect, useState, useCallback, useRef } from 'react'
import { getCrawls, getTargets, createCrawl, cancelCrawl } from '../api/client'
import { Radar, Play, XCircle, RefreshCw } from 'lucide-react'

function StatusBadge({ status }) {
  return (
    <span className={`badge badge-${status}`}>
      {status === 'running' && <span className="pulse" style={{ marginRight: 5 }} />}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export default function Crawls() {
  const [crawls, setCrawls] = useState([])
  const [targets, setTargets] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ target_id: '', max_depth: 2, max_pages: 80 })
  const [launching, setLaunching] = useState(false)
  const pollRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const [crawlsRes, targetsRes] = await Promise.all([getCrawls(), getTargets()])
      setCrawls(crawlsRes.data)
      setTargets(targetsRes.data)
    } catch {}
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    load()
    pollRef.current = setInterval(load, 5000)
    return () => clearInterval(pollRef.current)
  }, [load])

  const handleLaunch = async (e) => {
    e.preventDefault()
    if (!form.target_id) return
    setLaunching(true)
    try {
      await createCrawl({
        target_id: parseInt(form.target_id),
        max_depth: parseInt(form.max_depth),
        max_pages: parseInt(form.max_pages),
      })
      await load()
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to launch crawl.')
    } finally {
      setLaunching(false)
    }
  }

  const handleCancel = async (id) => {
    if (!window.confirm('Cancel this crawl?')) return
    await cancelCrawl(id)
    await load()
  }

  const targetName = (tid) => targets.find(t => t.id === tid)?.name || 'Target #' + tid
  const targetUrl = (tid) => targets.find(t => t.id === tid)?.base_url || ''

  const duration = (c) => {
    if (!c.started_at || !c.completed_at) return c.started_at ? 'Running...' : '-'
    const secs = Math.round((new Date(c.completed_at) - new Date(c.started_at)) / 1000)
    return secs < 60 ? secs + 's' : Math.floor(secs / 60) + 'm ' + (secs % 60) + 's'
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Radar size={20} color="#00d4ff" />
          <h1>Crawl Management</h1>
        </div>
        <p>Launch deep crawls and discover all endpoints</p>
      </div>

      <div className="card" style={{ marginBottom: 28 }}>
        <div style={{ fontWeight: 700, marginBottom: 16, fontSize: 15 }}>Launch New Crawl</div>
        <form onSubmit={handleLaunch} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 2, minWidth: 200, marginBottom: 0 }}>
            <label>Target Application</label>
            <select className="form-select" value={form.target_id}
              onChange={e => setForm(f => ({ ...f, target_id: e.target.value }))}>
              <option value="">Select a target</option>
              {targets.map(t => (
                <option key={t.id} value={t.id}>{t.name} ({t.base_url})</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ flex: 1, minWidth: 120, marginBottom: 0 }}>
            <label>Max Depth</label>
            <select className="form-select" value={form.max_depth}
              onChange={e => setForm(f => ({ ...f, max_depth: e.target.value }))}>
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="4">4</option>
            </select>
          </div>
          <div className="form-group" style={{ flex: 1, minWidth: 120, marginBottom: 0 }}>
            <label>Max Pages</label>
            <select className="form-select" value={form.max_pages}
              onChange={e => setForm(f => ({ ...f, max_pages: e.target.value }))}>
              <option value="30">30</option>
              <option value="50">50</option>
              <option value="80">80</option>
              <option value="150">150</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={launching || !form.target_id}
            style={{ marginBottom: 0 }}>
            {launching ? <><div className="spinner" /> Launching...</> : <><Play size={15} /> Start Crawl</>}
          </button>
        </form>
        {targets.length === 0 && (
          <div style={{ marginTop: 12, fontSize: 13, color: '#fbbf24' }}>
            No targets found. <a href="/targets" style={{ color: '#00d4ff' }}>Add a target first</a>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 16 }}>Crawl History</div>
        <button className="btn btn-ghost btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading crawls...</span></div>
      ) : crawls.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <h3>No Crawls Yet</h3>
            <p>Launch your first crawl using the form above.</p>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th><th>Target</th><th>Status</th>
                <th>Endpoints</th><th>Pages</th><th>Forms</th>
                <th>Duration</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {crawls.map(c => (
                <tr key={c.id}>
                  <td style={{ color: '#8b949e', fontSize: 12 }}>#{c.id}</td>
                  <td style={{ fontWeight: 600 }}>{targetName(c.target_id)}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td style={{ fontWeight: 600, color: c.total_endpoints > 0 ? '#00d4ff' : '#8b949e' }}>
                    {c.total_endpoints}
                  </td>
                  <td style={{ fontSize: 12, color: '#8b949e' }}>{c.pages_crawled}</td>
                  <td style={{ fontSize: 12, color: '#8b949e' }}>{c.forms_found}</td>
                  <td style={{ fontSize: 12, color: '#8b949e' }}>{duration(c)}</td>
                  <td>
                    {(c.status === 'running' || c.status === 'queued') && (
                      <button className="btn btn-danger btn-sm" onClick={() => handleCancel(c.id)}>
                        <XCircle size={13} /> Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
