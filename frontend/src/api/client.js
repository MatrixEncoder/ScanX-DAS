import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Targets ────────────────────────────────────────────────
export const getTargets = () => api.get('/targets/')
export const getTarget = (id) => api.get(`/targets/${id}`)
export const createTarget = (data) => api.post('/targets/', data)
export const updateTarget = (id, data) => api.put(`/targets/${id}`, data)
export const deleteTarget = (id) => api.delete(`/targets/${id}`)

// ── Crawls ─────────────────────────────────────────────────
export const getCrawls = () => api.get('/crawls/')
export const getCrawl = (id) => api.get(`/crawls/${id}`)
export const createCrawl = (data) => api.post('/crawls/', data)
export const cancelCrawl = (id) => api.post(`/crawls/${id}/cancel`)

// ── Endpoints ──────────────────────────────────────────────
export const getEndpoints = (params = {}) => api.get('/endpoints/', { params })
export const getEndpoint = (id) => api.get(`/endpoints/${id}`)
export const getDashboard = () => api.get('/endpoints/dashboard')
export const getEndpointStats = (crawlId) => api.get('/endpoints/stats', { params: { crawl_id: crawlId } })

// ── Reports ────────────────────────────────────────────────
export const generateReport = (crawlId) => api.post(`/reports/${crawlId}/generate`)
export const getReports = (crawlId) => api.get(`/reports/${crawlId}`)
export const downloadReport = (crawlId, format) =>
  `http://127.0.0.1:8000/reports/${crawlId}/download/${format}`

// ── GitHub Analysis ────────────────────────────────────────
export const getGithubAnalyses = () => api.get('/github/analyses')
export const getGithubAnalysis = (id) => api.get(`/github/analyses/${id}`)
export const startGithubAnalysis = (data) => api.post('/github/analyze', data)
export const getGithubFindings = (id, params = {}) => api.get(`/github/analyses/${id}/findings`, { params })
export const deleteGithubAnalysis = (id) => api.delete(`/github/analyses/${id}`)
export const generateGithubReport = (id) => api.post(`/github/analyses/${id}/report`)
export const downloadGithubReport = (id) => `http://127.0.0.1:8000/github/analyses/${id}/report/download`

// ── Assessments ────────────────────────────────────────────
export const getAssessments = () => api.get('/assessments/')
export const getAssessment = (id) => api.get(`/assessments/${id}`)
export const startWebRecon = (targetUrl) => api.post(`/assessments/web?target_url=${encodeURIComponent(targetUrl)}`)
export const startRepoScan = (data) => api.post('/assessments/repository', data)
export const startFullAssessment = (data) => api.post('/assessments/full', data)
export const getCorrelations = (id) => api.get(`/assessments/${id}/correlations`)
export const generateAssessmentReport = (id) => api.post(`/assessments/${id}/report`)
export const downloadAssessmentReport = (id) => `http://127.0.0.1:8000/assessments/${id}/report/download`
export const deleteAssessment = (id) => api.delete(`/assessments/${id}`)
