import { useEffect, useState } from 'react'
import {
  getAssessments, getAssessment, startWebRecon, startRepoScan, startFullAssessment,
  getCorrelations, deleteAssessment, generateAssessmentReport, downloadAssessmentReport
} from '../api/client'
import { Shield, Globe, Github, Link, Trash2, FileText, Download, RefreshCw, ChevronRight, Crosshair } from 'lucide-react'

const MODES = [
  {
    id: 'WEB_RECON',
    icon: Globe,
    title: 'Web Reconnaissance',
    desc: 'Discover endpoints, forms, JavaScript routes, technologies and attack-surface information.',
    color: '#00d4ff',
  },
  {
    id: 'REPOSITORY_SCAN',
    icon: Github,
    title: 'Repository Security Analysis',
    desc: 'Analyze source code for secrets, vulnerabilities and security misconfigurations.',
    color: '#a78bfa',
  },
  {
    id: 'FULL_ASSESSMENT',
    icon: Link,
    title: 'Full Assessment',
    desc: 'Analyze both the web target and repository and correlate the resulting security information.',
    color: '#fbbf24',
  },
]

export default function Assess() {
  const [mode, setMode] = useState(null)
  const [assessments, setAssessments] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [correlations, setCorrelations] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [phase, setPhase] = useState('')

  // Form state
  const [targetUrl, setTargetUrl] = useState('')
  const [repoUrl, setRepoUrl] = useState('')
  const [pat, setPat] = useState('')
  const [branch, setBranch] = useState('main')

  const loadAssessments = async () => {
    try {
      const res = await getAssessments()
      setAssessments(res.data)
    } catch { setAssessments([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { loadAssessments() }, [])

  const handleStart = async (e) => {
    e.preventDefault()
    setError('')
    setScanning(true)
    setPhase('submitting')
    setElapsed(0)

    const timer = setInterval(() => setElapsed(t => t + 1), 1000)

    try {
      let res
      if (mode === 'WEB_RECON') {
        if (!targetUrl.trim()) { setError('Target URL is required'); setScanning(false); clearInterval(timer); return }
        setPhase('crawling')
        res = await startWebRecon(targetUrl)
      } else if (mode === 'REPOSITORY_SCAN') {
        if (!repoUrl.trim()) { setError('Repository URL is required'); setScanning(false); clearInterval(timer); return }
        setPhase('scanning')
        res = await startRepoScan({ repo_url: repoUrl, pat, branch })
      } else {
        if (!targetUrl.trim() && !repoUrl.trim()) { setError('Provide at least a target URL or repository URL'); setScanning(false); clearInterval(timer); return }
        setPhase('running')
        res = await startFullAssessment({ target_url: targetUrl, repo_url: repoUrl, pat, branch })
      }

      const assessmentId = res.data.id
      setPhase('processing')

      // Poll until done
      let attempts = 0
      while (attempts < 180) {
        await new Promise(r => setTimeout(r, 2000))
        const statusRes = await getAssessment(assessmentId)
        const st = statusRes.data.status
        if (st === 'running') setPhase('processing')
        if (st === 'completed' || st === 'failed') {
          if (st === 'failed') {
            setError(statusRes.data.error_message || 'Assessment failed')
            setScanning(false)
            clearInterval(timer)
            return
          }
          setPhase('done')
          clearInterval(timer)
          await new Promise(r => setTimeout(r, 800))
          setSelected(assessmentId)
          setScanning(false)
          await loadAssessments()
          if (mode === 'FULL_ASSESSMENT') {
            loadCorrelations(assessmentId)
          }
          return
        }
        attempts++
      }
      setError('Assessment timed out')
      clearInterval(timer)
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to start assessment')
      clearInterval(timer)
    } finally { setScanning(false) }
  }

  const loadCorrelations = async (id) => {
    try {
      const res = await getCorrelations(id)
      setCorrelations(res.data)
    } catch { setCorrelations(null) }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this assessment?')) return
    await deleteAssessment(id)
    if (selected === id) { setSelected(null); setCorrelations(null) }
    await loadAssessments()
  }

  const handleGenerateReport = async (id) => {
    try {
      await generateAssessmentReport(id)
      window.open(downloadAssessmentReport(id), '_blank')
    } catch { alert('Failed to generate report') }
  }

  const steps = [
    { key: 'submitting', label: 'Initializing' },
    { key: 'crawling', label: 'Crawling target' },
    { key: 'scanning', label: 'Scanning repository' },
    { key: 'running', label: 'Running analysis' },
    { key: 'processing', label: 'Processing results' },
    { key: 'done', label: 'Complete' },
  ]
  const stepOrder = ['submitting', 'crawling', 'scanning', 'running', 'processing', 'done']
  const currentIdx = stepOrder.indexOf(phase)

  const selectedAssessment = assessments.find(a => a.id === selected)

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <Shield size={20} color="#00d4ff" />
          <h1>Assessment</h1>
        </div>
        <p>Choose an assessment mode and provide the required inputs</p>
      </div>

      {/* Mode Selection */}
      {!mode && !selected && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 30 }}>
          {MODES.map(m => (
            <div
              key={m.id}
              onClick={() => setMode(m.id)}
              style={{
                background: '#161b22', border: '1px solid #30363d', borderRadius: 12,
                padding: 24, cursor: 'pointer', transition: 'all 0.2s',
                display: 'flex', flexDirection: 'column', gap: 12,
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = m.color; e.currentTarget.style.transform = 'translateY(-2px)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#30363d'; e.currentTarget.style.transform = 'none' }}
            >
              <m.icon size={32} color={m.color} />
              <div style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3' }}>{m.title}</div>
              <div style={{ fontSize: 13, color: '#8b949e', lineHeight: 1.5 }}>{m.desc}</div>
            </div>
          ))}
        </div>
      )}

      {/* Scan Form */}
      {mode && !scanning && !selected && (
        <div className="card" style={{ maxWidth: 600 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <button onClick={() => setMode(null)} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 18 }}>←</button>
            <span style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3' }}>
              {MODES.find(m => m.id === mode)?.title}
            </span>
          </div>

          <form onSubmit={handleStart}>
            {(mode === 'WEB_RECON' || mode === 'FULL_ASSESSMENT') && (
              <div className="form-group">
                <label>Target URL</label>
                <input className="form-input" placeholder="https://example.com"
                  value={targetUrl} onChange={e => setTargetUrl(e.target.value)} />
              </div>
            )}

            {(mode === 'REPOSITORY_SCAN' || mode === 'FULL_ASSESSMENT') && (
              <>
                <div className="form-group">
                  <label>GitHub Repository URL</label>
                  <input className="form-input" placeholder="https://github.com/owner/repo"
                    value={repoUrl} onChange={e => setRepoUrl(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Personal Access Token (optional — for private repos)</label>
                  <input className="form-input" type="password" placeholder="ghp_xxxxxxxxxxxx"
                    value={pat} onChange={e => setPat(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Branch</label>
                  <input className="form-input" placeholder="main"
                    value={branch} onChange={e => setBranch(e.target.value)} />
                </div>
              </>
            )}

            {error && <div style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>{error}</div>}

            <div className="modal-footer">
              <button type="button" className="btn btn-ghost" onClick={() => setMode(null)}>Cancel</button>
              <button type="submit" className="btn btn-primary">
                <Shield size={14} /> Start {MODES.find(m => m.id === mode)?.title}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Scanning Progress */}
      {scanning && (
        <div className="card" style={{ maxWidth: 500 }}>
          <div style={{ background: '#21262d', borderRadius: 8, height: 6, marginBottom: 24, overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 8,
              background: 'linear-gradient(90deg, #00d4ff, #7c3aed)',
              width: phase === 'done' ? '100%' : `${Math.min(((currentIdx + 1) / steps.length) * 100, 95)}%`,
              transition: 'width 0.6s ease',
            }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {steps.map((step, i) => {
              const isActive = step.key === phase
              const isDone = currentIdx > i || phase === 'done'
              return (
                <div key={step.key} style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px',
                  borderRadius: 8, transition: 'all 0.3s',
                  background: isActive ? 'rgba(0,212,255,0.08)' : 'transparent',
                  border: `1px solid ${isActive ? 'rgba(0,212,255,0.3)' : 'transparent'}`,
                }}>
                  <span style={{ width: 20, textAlign: 'center', fontSize: 14 }}>
                    {isDone ? '✅' : isActive ? <RefreshCw size={14} style={{ animation: 'spin 1s linear infinite', color: '#00d4ff' }} /> : '○'}
                  </span>
                  <span style={{ fontSize: 13, color: isDone ? '#4ade80' : isActive ? '#e6edf3' : '#484f58', fontWeight: isActive ? 600 : 400 }}>
                    {step.label}
                  </span>
                </div>
              )
            })}
          </div>
          <div style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: '#8b949e' }}>
            {phase !== 'done' && <span><RefreshCw size={11} style={{ animation: 'spin 1s linear infinite', marginRight: 6, verticalAlign: 'middle' }} />Elapsed: {elapsed}s</span>}
            {phase === 'done' && <span style={{ color: '#4ade80' }}>Done in {elapsed}s</span>}
          </div>
        </div>
      )}

      {/* Assessment Results / History */}
      {!mode && !scanning && (
        <>
          {selected && selectedAssessment && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Shield size={16} color="#00d4ff" />
                  <span style={{ fontWeight: 700, fontSize: 15 }}>Assessment #{selected}</span>
                  <span className={`badge badge-${selectedAssessment.status === 'completed' ? '2xx' : selectedAssessment.status === 'failed' ? '5xx' : '3xx'}`}>
                    {selectedAssessment.status}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-ghost" onClick={() => { setSelected(null); setCorrelations(null) }}>Back to list</button>
                  {selectedAssessment.status === 'completed' && (
                    <>
                      <button className="btn btn-primary" onClick={() => handleGenerateReport(selected)}>
                        <FileText size={14} /> Generate Report
                      </button>
                    </>
                  )}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 16 }}>
                {selectedAssessment.target_url && (
                  <div><div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase' }}>Target</div><div className="mono" style={{ marginTop: 4, fontSize: 12 }}>{selectedAssessment.target_url}</div></div>
                )}
                {selectedAssessment.repo_url && (
                  <div><div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase' }}>Repository</div><div className="mono" style={{ marginTop: 4, fontSize: 12 }}>{selectedAssessment.repo_url}</div></div>
                )}
                <div><div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase' }}>Type</div><div style={{ marginTop: 4, fontWeight: 600 }}>{selectedAssessment.assessment_type}</div></div>
                {selectedAssessment.source_mappings > 0 && (
                  <div><div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase' }}>Source Mappings</div><div style={{ marginTop: 4, fontWeight: 600, color: '#00d4ff' }}>{selectedAssessment.source_mappings}</div></div>
                )}
                {selectedAssessment.correlation_findings > 0 && (
                  <div><div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase' }}>Linked Findings</div><div style={{ marginTop: 4, fontWeight: 600, color: '#fbbf24' }}>{selectedAssessment.correlation_findings}</div></div>
                )}
              </div>

              {/* Correlations */}
              {correlations && correlations.correlations.length > 0 && (
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Crosshair size={14} color="#fbbf24" /> Correlations
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr><th>Endpoint</th><th>Source File</th><th>Finding</th><th>Confidence</th><th>Signals</th></tr>
                      </thead>
                      <tbody>
                        {correlations.correlations.map((c, i) => (
                          <tr key={i}>
                            <td className="mono" style={{ fontSize: 12 }}>{c.endpoint_url}</td>
                            <td className="mono" style={{ fontSize: 12 }}>{c.source_file}</td>
                            <td>{c.finding_title ? <span className={`badge badge-${c.finding_severity}`}>{c.finding_title}</span> : '—'}</td>
                            <td>
                              <span className={`badge badge-${c.confidence >= 90 ? 'critical' : c.confidence >= 70 ? 'high' : c.confidence >= 40 ? 'medium' : 'low'}`}>
                                {c.confidence}%
                              </span>
                            </td>
                            <td style={{ fontSize: 11 }}>
                              {c.evidence.filter(e => e.matched).map((e, j) => (
                                <span key={j} style={{ color: '#4ade80', marginRight: 6 }}>✓ {e.signal_type}</span>
                              ))}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Assessment History */}
          <div className="card">
            <div style={{ fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Shield size={16} color="#00d4ff" />
              Assessment History
            </div>
            {assessments.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🛡️</div>
                <p>No assessments yet. Choose a mode above to get started.</p>
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>ID</th><th>Type</th><th>Status</th><th>Target</th><th>Repository</th><th>Created</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {assessments.map(a => (
                      <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => { setSelected(a.id); if (a.assessment_type === 'FULL_ASSESSMENT') loadCorrelations(a.id) }}>
                        <td style={{ color: '#8b949e', fontSize: 12 }}>#{a.id}</td>
                        <td><span className="badge" style={{ background: 'rgba(0,212,255,0.15)', color: '#00d4ff' }}>{a.assessment_type}</span></td>
                        <td><span className={`badge badge-${a.status === 'completed' ? '2xx' : a.status === 'failed' ? '5xx' : '3xx'}`}>{a.status}</span></td>
                        <td className="mono" style={{ fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.target_url || '—'}</td>
                        <td className="mono" style={{ fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.repo_url || '—'}</td>
                        <td style={{ fontSize: 12, color: '#8b949e' }}>{new Date(a.created_at).toLocaleDateString()}</td>
                        <td onClick={e => e.stopPropagation()}>
                          <div style={{ display: 'flex', gap: 4 }}>
                            {a.status === 'completed' && (
                              <button className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 11 }}
                                onClick={() => handleGenerateReport(a.id)}>
                                <FileText size={12} />
                              </button>
                            )}
                            <button className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 11, color: '#f87171' }}
                              onClick={() => handleDelete(a.id)}>
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
