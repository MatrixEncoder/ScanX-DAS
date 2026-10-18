import { useEffect, useState } from 'react'
import { getEndpoints } from '../api/client'
import { MapPin } from 'lucide-react'

export default function Endpoints() {
  const [endpoints, setEndpoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [crawlId, setCrawlId] = useState('')

  useEffect(() => {
    const params = {}
    if (crawlId) params.crawl_id = parseInt(crawlId)
    if (sourceFilter) params.source = sourceFilter
    if (search) params.search = search
    getEndpoints(params)
      .then(r => setEndpoints(r.data))
      .catch(() => setEndpoints([]))
      .finally(() => setLoading(false))
  }, [crawlId, sourceFilter, search])

  const counts = {
    total: endpoints.length,
    api: endpoints.filter(e => e.is_api).length,
    login: endpoints.filter(e => e.has_login_form).length,
    link: endpoints.filter(e => e.source === 'link').length,
    form: endpoints.filter(e => e.source === 'form').length,
    js: endpoints.filter(e => e.source === 'js').length,
    wordlist: endpoints.filter(e => e.source === 'wordlist').length,
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <MapPin size={20} color="#00d4ff" />
          <h1>Discovered Endpoints</h1>
        </div>
        <p>Browse and filter all endpoints found during crawling</p>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        {['', 'link', 'form', 'js', 'wordlist'].map(src => (
          <button key={src} onClick={() => setSourceFilter(src)}
            className={`btn btn-sm ${sourceFilter === src ? 'btn-primary' : 'btn-ghost'}`}
            style={{ fontSize: 12 }}>
            {src === '' ? 'All (' + counts.total + ')' : src + ' (' + (counts[src] || 0) + ')'}
          </button>
        ))}
      </div>

      <div className="filter-bar">
        <input className="search-input" placeholder="Search by URL..."
          value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading endpoints...</span></div>
      ) : endpoints.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">📍</div>
            <h3>No Endpoints Found</h3>
            <p>Run a crawl to discover endpoints on your targets.</p>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <colgroup>
              <col style={{ width: 40 }} />
              <col style={{ width: '28%' }} />
              <col style={{ width: 90 }} />
              <col style={{ width: 65 }} />
              <col style={{ width: '20%' }} />
              <col style={{ width: '15%' }} />
              <col style={{ width: 85 }} />
              <col style={{ width: 95 }} />
            </colgroup>
            <thead>
              <tr>
                <th>#</th>
                <th>URL</th>
                <th>Methods</th>
                <th>Status</th>
                <th>Title</th>
                <th>Parameters</th>
                <th>Source</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {endpoints.map((ep, i) => (
                <tr key={ep.id}>
                  <td style={{ color: '#8b949e', fontSize: 12 }}>{i + 1}</td>
                  <td><span className="mono" style={{ maxWidth: 260, display: 'inline-block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', verticalAlign: 'bottom' }}>{ep.url}</span></td>
                  <td>
                    {ep.methods.split(',').map(m => (
                      <span key={m} className={'badge badge-' + m.toLowerCase()} style={{ marginRight: 4 }}>{m}</span>
                    ))}
                  </td>
                  <td>
                    <span className={'badge badge-' + (ep.status_code < 300 ? '2xx' : ep.status_code < 400 ? '3xx' : ep.status_code < 500 ? '4xx' : '5xx')}>
                      {ep.status_code}
                    </span>
                  </td>
                  <td style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>
                    {ep.title || '-'}
                  </td>
                  <td style={{ fontSize: 12, color: '#8b949e' }}>{ep.parameters || '-'}</td>
                  <td><span className={'source-badge source-' + ep.source}>{ep.source}</span></td>
                  <td>
                    {ep.is_api && <span className="badge badge-api" style={{ marginRight: 4 }}>API</span>}
                    {ep.has_login_form && <span className="badge badge-login">LOGIN</span>}
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
