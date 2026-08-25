import { useEffect, useState } from 'react'
import {
  getGithubAnalyses, getGithubAnalysis, startGithubAnalysis, getGithubFindings,
  deleteGithubAnalysis, generateGithubReport, downloadGithubReport
} from '../api/client'
import { Plus, Trash2, FileText, Download, RefreshCw, AlertTriangle, Github, ExternalLink } from 'lucide-react'

const SEVERITY_COLORS = {
  critical: '#f87171', high: '#fbbf24', medium: '#60a5fa', low: '#8b949e', info: '#4ade80'
}

export default function GithubScan() {
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [selected, setSelected] = useState(null)
  const [findings, setFindings] = useState([])
  const [filter, setFilter] = useState('all')
  const [generating, setGenerating] = useState(false)

  const loadAnalyses = async () => {
    try {
      const res = await getGithubAnalyses()
      setAnalyses(res.data)
    } catch { setAnalyses([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { loadAnalyses() }, [])

  const loadFindings = async (id) => {
    setSelected(id)
    try {
      const res = await getGithubFindings(id)
      setFindings(res.data)
    } catch { setFindings([]) }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this analysis and all findings?')) return
    await deleteGithubAnalysis(id)
    if (selected === id) { setSelected(null); setFindings([]) }
    await loadAnalyses()
  }

  const handleGenerateReport = async (id) => {
    setGenerating(true)
    try {
      await generateGithubReport(id)
      window.open(downloadGithubReport(id), '_blank')
    } catch (err) {
      alert('Failed to generate report: ' + (err?.response?.data?.detail || err.message))
    } finally { setGenerating(false) }
  }

  const pollStatus = async (id) => {
    const res = await getGithubAnalysis(id)
    return res.data.status
  }

  const filteredFindings = filter === 'all' ? findings : findings.filter(f => f.severity === filter)
  const selectedAnalysis = analyses.find(a => a.id === selected)

  return (
    <div>
      <div className="page-actions">
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Github size={20} color="#00d4ff" />
            <h1>GitHub Repository Scanner</h1>
          </div>
          <p>Analyze repositories for hardcoded secrets, injection vulnerabilities, and security misconfigurations</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> New Scan
        </button>
      </div>

      {showForm && (
        <ScanForm onClose={() => setShowForm(false)} onDone={async (id) => {
          setShowForm(false)
          await loadAnalyses()
          await loadFindings(id)
        }} />
      )}

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading…</span></div>
      ) : analyses.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon"><Github size={48} /></div>
            <h3>No Scans Yet</h3>
            <p>Paste a GitHub repository URL to scan for security vulnerabilities.</p>
            <button className="btn btn-primary" style={{ marginTop: 20 }}
              onClick={() => setShowForm(true)}>
              <Plus size={16} /> Start First Scan
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: selected ? '350px 1fr' : '1fr', gap: 20 }}>
          {/* Analysis list */}
          <div className="table-wrap" style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Status</th>
                  <th>Findings</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {analyses.map(a => (
                  <tr key={a.id}
                    onClick={() => loadFindings(a.id)}
                    style={{ cursor: 'pointer', background: selected === a.id ? '#1c2333' : undefined }}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{a.repo_name}</div>
                      <div style={{ fontSize: 11, color: '#8b949e' }}>{a.branch}</div>
                    </td>
                    <td>
                      <StatusBadge status={a.status} />
                    </td>
                    <td>
                      {a.status === 'completed' ? (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {a.critical_count > 0 && <span className="badge badge-critical">{a.critical_count}C</span>}
                          {a.high_count > 0 && <span className="badge badge-high">{a.high_count}H</span>}
                          {a.medium_count > 0 && <span className="badge badge-medium">{a.medium_count}M</span>}
                          {a.low_count > 0 && <span className="badge badge-low">{a.low_count}L</span>}
                          {a.info_count > 0 && <span className="badge badge-info">{a.info_count}I</span>}
                          {a.total_findings === 0 && <span className="badge badge-info">Clean</span>}
                        </div>
                      ) : '—'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {a.status === 'completed' && (
                          <>
                            <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); handleGenerateReport(a.id) }}
                              disabled={generating}>
                              <FileText size={13} /> Report
                            </button>
                            <a href={downloadGithubReport(a.id)} target="_blank" rel="noreferrer"
                              className="btn btn-ghost btn-sm" onClick={e => e.stopPropagation()}>
                              <Download size={13} />
                            </a>
                          </>
                        )}
                        <button className="btn btn-danger btn-sm" onClick={(e) => { e.stopPropagation(); handleDelete(a.id) }}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Findings panel */}
          {selected && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <h2 style={{ fontSize: 16 }}>{selectedAnalysis?.repo_name}</h2>
                  <p style={{ fontSize: 12, color: '#8b949e' }}>
                    {selectedAnalysis?.total_findings} findings across {selectedAnalysis?.files_scanned} files
                    {selectedAnalysis?.analysis_duration ? ` in ${selectedAnalysis.analysis_duration}s` : ''}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {['all', 'critical', 'high', 'medium', 'low', 'info'].map(s => (
                    <button key={s}
                      className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-ghost'}`}
                      onClick={() => setFilter(s)}
                      style={{ textTransform: 'capitalize' }}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {filteredFindings.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                  <div style={{ color: '#4ade80', fontSize: 18, marginBottom: 8 }}>✓</div>
                  <div>No {filter !== 'all' ? filter + ' ' : ''}findings</div>
                </div>
              ) : (
                <div style={{ maxHeight: 'calc(100vh - 280px)', overflowY: 'auto' }}>
                  {filteredFindings.map(f => (
                    <FindingCard key={f.id} finding={f} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }) {
  const colors = {
    queued: '#8b949e', scanning: '#60a5fa', completed: '#4ade80', failed: '#f87171'
  }
  return (
    <span className="badge" style={{
      background: `${colors[status] || '#8b949e'}20`,
      color: colors[status] || '#8b949e'
    }}>
      {status === 'scanning' && <RefreshCw size={10} style={{ marginRight: 4, animation: 'spin 1s linear infinite' }} />}
      {status}
    </span>
  )
}

function FindingCard({ finding }) {
  const f = finding
  return (
    <div style={{
      background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
      padding: 14, marginBottom: 10, borderLeft: `3px solid ${SEVERITY_COLORS[f.severity] || '#8b949e'}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 6 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="badge" style={{
            background: `${SEVERITY_COLORS[f.severity]}20`, color: SEVERITY_COLORS[f.severity]
          }}>{f.severity.toUpperCase()}</span>
          <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#79c0ff' }}>{f.rule_id}</span>
          <span className="badge" style={{ background: 'rgba(0,212,255,0.15)', color: '#00d4ff' }}>
            {f.category}
          </span>
        </div>
        <span style={{ fontSize: 11, color: '#8b949e' }}>L{f.line_number}</span>
      </div>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{f.title}</div>
      <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#79c0ff', marginBottom: 6 }}>{f.file_path}</div>
      <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 6 }}>{f.description}</div>
      {f.evidence && (
        <pre style={{
          background: '#0d1117', border: '1px solid #30363d', borderRadius: 6,
          padding: 8, fontSize: 11, color: '#f87171', fontFamily: 'monospace',
          overflow: 'hidden', maxHeight: 50, marginBottom: 6, whiteSpace: 'pre-wrap', wordBreak: 'break-all'
        }}>{f.evidence}</pre>
      )}
      <div style={{ fontSize: 12, color: '#4ade80' }}>→ {f.recommendation}</div>
    </div>
  )
}

function ScanForm({ onClose, onDone }) {
  const [form, setForm] = useState({ repo_url: '', pat: '', branch: 'main' })
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')
  const [phase, setPhase] = useState('')
  const [elapsed, setElapsed] = useState(0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.repo_url.trim()) { setError('Repository URL is required.'); return }
    setScanning(true)
    setError('')
    setPhase('connecting')
    setElapsed(0)

    const timer = setInterval(() => setElapsed(t => t + 1), 1000)

    try {
      setPhase('submitting')
      const res = await startGithubAnalysis(form)
      const analysisId = res.data.id

      setPhase('cloning')
      let attempts = 0
      const maxAttempts = 120
      while (attempts < maxAttempts) {
        await new Promise(r => setTimeout(r, 2000))
        const statusRes = await getGithubAnalysis(analysisId)
        const st = statusRes.data.status
        if (st === 'scanning') setPhase('scanning')
        if (st === 'completed' || st === 'failed') {
          if (st === 'failed') {
            setError(statusRes.data.error_message || 'Analysis failed')
            setScanning(false)
            clearInterval(timer)
            return
          }
          setPhase('done')
          clearInterval(timer)
          await new Promise(r => setTimeout(r, 800))
          onDone(analysisId)
          return
        }
        attempts++
      }
      setError('Analysis timed out after 6 minutes')
      clearInterval(timer)
    } catch (err) {
      console.error('GitHub scan error:', err)
      setError(err?.response?.data?.detail || err?.message || 'Failed to start analysis')
      clearInterval(timer)
    } finally { setScanning(false) }
  }

  const steps = [
    { key: 'submitting', label: 'Connecting to GitHub', icon: '🔗' },
    { key: 'cloning', label: 'Cloning repository', icon: '📦' },
    { key: 'scanning', label: 'Scanning for vulnerabilities', icon: '🔍' },
    { key: 'done', label: 'Analysis complete', icon: '✅' },
  ]

  const stepOrder = ['submitting', 'cloning', 'scanning', 'done']
  const currentIdx = stepOrder.indexOf(phase)

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2><Github size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />New GitHub Scan</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {!scanning ? (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Repository URL *</label>
              <input className="form-input" placeholder="https://github.com/owner/repo"
                value={form.repo_url} onChange={e => setForm(f => ({ ...f, repo_url: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Personal Access Token (optional — for private repos)</label>
              <input className="form-input" type="password" placeholder="ghp_xxxxxxxxxxxx"
                value={form.pat} onChange={e => setForm(f => ({ ...f, pat: e.target.value }))} />
              <div style={{ fontSize: 11, color: '#8b949e', marginTop: 4 }}>
                Required for private repos. Create at github.com → Settings → Developer settings → PAT
              </div>
            </div>
            <div className="form-group">
              <label>Branch</label>
              <input className="form-input" placeholder="main"
                value={form.branch} onChange={e => setForm(f => ({ ...f, branch: e.target.value }))} />
            </div>
            {error && <div style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>{error}</div>}
            <div className="modal-footer">
              <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary">
                <Github size={14} /> Start Scan
              </button>
            </div>
          </form>
        ) : (
          <div style={{ padding: '20px 0' }}>
            {/* Progress bar */}
            <div style={{ background: '#21262d', borderRadius: 8, height: 6, marginBottom: 24, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 8,
                background: 'linear-gradient(90deg, #00d4ff, #7c3aed)',
                width: phase === 'done' ? '100%' : `${Math.min(((currentIdx + 1) / steps.length) * 100, 95)}%`,
                transition: 'width 0.6s ease',
              }} />
            </div>

            {/* Steps */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {steps.map((step, i) => {
                const isActive = step.key === phase
                const isDone = currentIdx > i || phase === 'done'
                return (
                  <div key={step.key} style={{
                    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                    borderRadius: 8, transition: 'all 0.3s',
                    background: isActive ? 'rgba(0,212,255,0.08)' : 'transparent',
                    border: `1px solid ${isActive ? 'rgba(0,212,255,0.3)' : 'transparent'}`,
                  }}>
                    <span style={{ fontSize: 18, width: 28, textAlign: 'center' }}>
                      {isDone ? '✅' : isActive ? (
                        <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite', color: '#00d4ff' }} />
                      ) : (
                        <span style={{ color: '#484f58' }}>{step.icon}</span>
                      )}
                    </span>
                    <span style={{
                      fontSize: 13, fontWeight: isActive ? 600 : 400,
                      color: isDone ? '#4ade80' : isActive ? '#e6edf3' : '#484f58',
                    }}>
                      {step.label}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Timer */}
            <div style={{ textAlign: 'center', marginTop: 20, fontSize: 12, color: '#8b949e' }}>
              {phase !== 'done' && (
                <span>
                  <RefreshCw size={11} style={{ animation: 'spin 1s linear infinite', marginRight: 6, verticalAlign: 'middle' }} />
                  Elapsed: {elapsed}s
                </span>
              )}
              {phase === 'done' && <span style={{ color: '#4ade80' }}>Done in {elapsed}s — loading results…</span>}
            </div>

            {error && (
              <div style={{ color: '#f87171', fontSize: 13, marginTop: 12, textAlign: 'center' }}>{error}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
