import { useEffect, useState } from 'react'
import { getAssessments, getAssessment, getCorrelations, getEndpoints } from '../api/client'
import { Crosshair, ChevronDown, ChevronRight, ExternalLink, AlertTriangle, FileCode, Target } from 'lucide-react'

const SEVERITY_COLORS = {
  critical: '#f87171', high: '#fbbf24', medium: '#60a5fa', low: '#8b949e', info: '#4ade80',
}

export default function AttackSurface() {
  const [assessments, setAssessments] = useState([])
  const [selected, setSelected] = useState(null)
  const [correlations, setCorrelations] = useState(null)
  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getAssessments()
        const full = res.data.filter(a => a.assessment_type === 'FULL_ASSESSMENT' && a.status === 'completed')
        setAssessments(full)
        if (full.length > 0) {
          setSelected(full[0].id)
        }
      } catch { setAssessments([]) }
      finally { setLoading(false) }
    }
    load()
  }, [])

  useEffect(() => {
    if (!selected) return
    const load = async () => {
      try {
        const [corrRes, aRes] = await Promise.all([
          getCorrelations(selected),
          getAssessment(selected),
        ])
        setCorrelations(corrRes.data)

        // Load endpoints from crawl
        if (aRes.data.crawl_id) {
          const epRes = await getEndpoints({ crawl_id: aRes.data.crawl_id })
          setEndpoints(epRes.data)
        }
      } catch {
        setCorrelations(null)
        setEndpoints([])
      }
    }
    load()
  }, [selected])

  const toggle = (key) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }))

  if (loading) return (
    <div className="loading"><div className="spinner" /><span>Loading attack surface...</span></div>
  )

  if (assessments.length === 0) return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <Crosshair size={20} color="#fbbf24" />
          <h1>Attack Surface</h1>
        </div>
        <p>Run a Full Assessment first to see correlated attack surface data</p>
      </div>
      <div className="card">
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <p>No full assessments with correlations yet.</p>
          <p style={{ fontSize: 13, color: '#8b949e', marginTop: 8 }}>Go to <strong>Assess</strong> → <strong>Full Assessment</strong> to generate correlated data.</p>
        </div>
      </div>
    </div>
  )

  // Build tree structure
  const tree = []
  const epMap = {}
  endpoints.forEach(ep => { epMap[ep.id] = ep })

  // Map correlations by endpoint
  const corrByEp = {}
  if (correlations?.correlations) {
    correlations.correlations.forEach(c => {
      if (!corrByEp[c.endpoint_url]) corrByEp[c.endpoint_url] = []
      corrByEp[c.endpoint_url].push(c)
    })
  }

  endpoints.forEach(ep => {
    const node = {
      id: ep.id,
      url: ep.url,
      methods: ep.methods,
      status: ep.status_code,
      source: ep.source,
      is_api: ep.is_api,
      has_login: ep.has_login_form,
      correlations: corrByEp[ep.url] || [],
    }
    tree.push(node)
  })

  // Group by source
  const grouped = {}
  tree.forEach(node => {
    const src = node.source || 'other'
    if (!grouped[src]) grouped[src] = []
    grouped[src].push(node)
  })

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <Crosshair size={20} color="#fbbf24" />
          <h1>Attack Surface</h1>
        </div>
        <p>Correlated view of endpoints, source files, and findings</p>
      </div>

      {/* Assessment selector */}
      <div style={{ marginBottom: 20 }}>
        <label style={{ fontSize: 12, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1 }}>Full Assessment</label>
        <select
          value={selected || ''}
          onChange={e => setSelected(Number(e.target.value))}
          style={{
            marginTop: 6, background: '#161b22', border: '1px solid #30363d', borderRadius: 6,
            color: '#e6edf3', padding: '8px 12px', fontSize: 13, width: '100%', maxWidth: 400,
          }}
        >
          {assessments.map(a => (
            <option key={a.id} value={a.id}>#{a.id} — {a.target_url || a.repo_url} ({new Date(a.created_at).toLocaleDateString()})</option>
          ))}
        </select>
      </div>

      {/* Stats */}
      {correlations && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
          <div className="stat-card" style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16, textAlign: 'center' }}>
            <span style={{ fontSize: 28, fontWeight: 900, color: '#00d4ff', display: 'block' }}>{endpoints.length}</span>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: '#8b949e' }}>Endpoints</div>
          </div>
          <div className="stat-card" style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16, textAlign: 'center' }}>
            <span style={{ fontSize: 28, fontWeight: 900, color: '#fbbf24', display: 'block' }}>{correlations.source_mappings}</span>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: '#8b949e' }}>Source Mappings</div>
          </div>
          <div className="stat-card" style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16, textAlign: 'center' }}>
            <span style={{ fontSize: 28, fontWeight: 900, color: '#f87171', display: 'block' }}>{correlations.correlation_findings}</span>
            <div style={{ fontSize: 11, textTransform: 'uppercase', color: '#8b949e' }}>Linked Findings</div>
          </div>
        </div>
      )}

      {/* Tree View */}
      <div className="card">
        <div style={{ fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Crosshair size={16} color="#fbbf24" />
          Attack Surface Tree
        </div>

        {Object.entries(grouped).sort().map(([source, eps]) => (
          <div key={source} style={{ marginBottom: 16 }}>
            <div
              onClick={() => toggle(source)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px',
                background: '#161b22', borderRadius: 8, cursor: 'pointer',
                border: '1px solid #30363d', marginBottom: 4,
              }}
            >
              {expanded[source] !== false ? <ChevronDown size={14} color="#8b949e" /> : <ChevronRight size={14} color="#8b949e" />}
              <Target size={14} color="#00d4ff" />
              <span style={{ fontWeight: 600, fontSize: 13, color: '#e6edf3', textTransform: 'capitalize' }}>{source}</span>
              <span style={{ fontSize: 11, color: '#8b949e', background: '#21262d', padding: '2px 8px', borderRadius: 4 }}>{eps.length}</span>
            </div>

            {expanded[source] !== false && (
              <div style={{ marginLeft: 20, borderLeft: '1px solid #21262d', paddingLeft: 12 }}>
                {eps.map(ep => (
                  <div key={ep.id} style={{ marginBottom: 4 }}>
                    {/* Endpoint */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0' }}>
                      <span className={`badge badge-${ep.methods.split(',')[0].toLowerCase()}`} style={{ fontSize: 10, minWidth: 40, textAlign: 'center' }}>
                        {ep.methods.split(',')[0]}
                      </span>
                      <span className="mono" style={{ fontSize: 12 }}>{ep.url}</span>
                      <span style={{ fontSize: 11, color: '#8b949e' }}>{ep.status}</span>
                      {ep.is_api && <span className="badge badge-api" style={{ fontSize: 9 }}>API</span>}
                    </div>

                    {/* Correlations for this endpoint */}
                    {ep.correlations.length > 0 && (
                      <div style={{ marginLeft: 48, marginBottom: 8 }}>
                        {ep.correlations.map((c, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '4px 0', fontSize: 12 }}>
                            <span style={{ color: '#8b949e' }}>└→</span>
                            <FileCode size={12} color="#a78bfa" style={{ marginTop: 2, flexShrink: 0 }} />
                            <div>
                              <span className="mono" style={{ color: '#a78bfa', fontSize: 11 }}>{c.source_file}</span>
                              <span className={`badge badge-${c.confidence >= 70 ? 'high' : c.confidence >= 40 ? 'medium' : 'low'}`}
                                style={{ marginLeft: 6, fontSize: 9 }}>
                                {c.confidence}% confidence
                              </span>
                              {c.finding_title && (
                                <div style={{ marginTop: 2, fontSize: 11 }}>
                                  <AlertTriangle size={10} color={SEVERITY_COLORS[c.finding_severity]} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                                  <span style={{ color: SEVERITY_COLORS[c.finding_severity] }}>{c.finding_title}</span>
                                </div>
                              )}
                              {/* Evidence signals */}
                              <div style={{ marginTop: 2 }}>
                                {c.evidence.filter(e => e.matched).map((e, j) => (
                                  <span key={j} style={{ color: '#4ade80', fontSize: 10, marginRight: 6 }}>✓ {e.signal_type}</span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
