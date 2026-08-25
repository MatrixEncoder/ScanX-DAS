import { useEffect, useState } from 'react'
import { getCrawls, getTargets, getReports, generateReport, downloadReport } from '../api/client'
import { FileText, Download, RefreshCw, Loader } from 'lucide-react'

export default function Reports() {
  const [crawls, setCrawls] = useState([])
  const [targets, setTargets] = useState([])
  const [reports, setReports] = useState({})
  const [generating, setGenerating] = useState({})
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [crawlsRes, targetsRes] = await Promise.all([getCrawls(), getTargets()])
      const completedCrawls = crawlsRes.data.filter(c => c.status === 'completed')
      setCrawls(crawlsRes.data)
      setTargets(targetsRes.data)
      const reportsMap = {}
      await Promise.all(completedCrawls.map(async c => {
        try {
          const r = await getReports(c.id)
          reportsMap[c.id] = r.data
        } catch {
          reportsMap[c.id] = []
        }
      }))
      setReports(reportsMap)
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleGenerate = async (crawlId) => {
    setGenerating(g => ({ ...g, [crawlId]: true }))
    try {
      await generateReport(crawlId)
      const r = await getReports(crawlId)
      setReports(prev => ({ ...prev, [crawlId]: r.data }))
    } catch (e) {
      alert(e?.response?.data?.detail || 'Report generation failed.')
    } finally {
      setGenerating(g => ({ ...g, [crawlId]: false }))
    }
  }

  const targetName = (tid) => targets.find(t => t.id === tid)?.name || 'Target #' + tid
  const hasReport = (crawlId, fmt) => (reports[crawlId] || []).some(r => r.format === fmt)
  const completedCrawls = crawls.filter(c => c.status === 'completed')

  return (
    <div>
      <div className="page-actions">
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileText size={20} color="#00d4ff" />
            <h1>Reports</h1>
          </div>
          <p>Generate and download endpoint discovery reports</p>
        </div>
        <button className="btn btn-ghost" onClick={load}><RefreshCw size={14} /> Refresh</button>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading...</span></div>
      ) : completedCrawls.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">📄</div>
            <h3>No Completed Crawls</h3>
            <p>Complete a crawl first, then generate a report.</p>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Crawl ID</th>
                <th>Target</th>
                <th>Endpoints</th>
                <th>Duration</th>
                <th>Report</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {completedCrawls.map(c => (
                <tr key={c.id}>
                  <td style={{ color: '#8b949e', fontSize: 12 }}>#{c.id}</td>
                  <td style={{ fontWeight: 600 }}>{targetName(c.target_id)}</td>
                  <td>{c.total_endpoints}</td>
                  <td style={{ fontSize: 12, color: '#8b949e' }}>{c.crawl_duration.toFixed(1)}s</td>
                  <td>
                    {hasReport(c.id, 'html')
                      ? <span className="badge badge-completed">HTML Ready</span>
                      : <span className="badge badge-created">No Report</span>}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button className="btn btn-primary btn-sm"
                        onClick={() => handleGenerate(c.id)}
                        disabled={generating[c.id]}>
                        {generating[c.id]
                          ? <><Loader size={13} style={{ animation: 'spin 1s linear infinite' }} /> Generating...</>
                          : <><RefreshCw size={13} /> {hasReport(c.id, 'html') ? 'Regenerate' : 'Generate'}</>}
                      </button>
                      {hasReport(c.id, 'html') && (
                        <a className="btn btn-ghost btn-sm"
                          href={downloadReport(c.id, 'html')} target="_blank" rel="noreferrer">
                          <Download size={13} /> HTML
                        </a>
                      )}
                    </div>
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
