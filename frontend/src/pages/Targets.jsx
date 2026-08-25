import { useEffect, useState } from 'react'
import { getTargets, createTarget, updateTarget, deleteTarget } from '../api/client'
import { Plus, Edit3, Trash2, Target, Link, Lock } from 'lucide-react'

const EMPTY_FORM = { name: '', base_url: '', auth_required: false, notes: '' }

function TargetModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(initial || EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.base_url.trim()) {
      setError('Name and URL are required.')
      return
    }
    setSaving(true)
    try {
      await onSave(form)
      onClose()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to save target.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>{initial?.id ? 'Edit Target' : 'Add Target'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Target Name *</label>
            <input className="form-input" placeholder="e.g. Company Web App"
              value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Base URL *</label>
            <input className="form-input" placeholder="https://example.com"
              value={form.base_url} onChange={e => setForm(f => ({ ...f, base_url: e.target.value }))} />
          </div>
          <div className="form-group">
            <label className="form-check-label">
              <input type="checkbox" className="form-checkbox"
                checked={form.auth_required}
                onChange={e => setForm(f => ({ ...f, auth_required: e.target.checked }))} />
              Authentication Required
            </label>
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea className="form-textarea" placeholder="Any additional notes…"
              value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
          </div>
          {error && <div style={{ color: '#f87171', fontSize: 13, marginBottom: 12 }}>{error}</div>}
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : (initial?.id ? 'Update Target' : 'Add Target')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Targets() {
  const [targets, setTargets] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)

  const load = async () => {
    try {
      const res = await getTargets()
      setTargets(res.data)
    } catch { setTargets([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleSave = async (form) => {
    if (editTarget?.id) {
      await updateTarget(editTarget.id, form)
    } else {
      await createTarget(form)
    }
    await load()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this target and all its scan data?')) return
    await deleteTarget(id)
    await load()
  }

  return (
    <div>
      <div className="page-actions">
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Target size={20} color="#00d4ff" />
            <h1>Target Management</h1>
          </div>
          <p>Register and manage web applications for security scanning</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setEditTarget(null); setShowModal(true) }}>
          <Plus size={16} />
          Add Target
        </button>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading targets…</span></div>
      ) : targets.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">🎯</div>
            <h3>No Targets Yet</h3>
            <p>Add your first target application to get started with security scanning.</p>
            <button className="btn btn-primary" style={{ marginTop: 20 }}
              onClick={() => { setEditTarget(null); setShowModal(true) }}>
              <Plus size={16} /> Add Your First Target
            </button>
          </div>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Base URL</th>
                <th>Auth</th>
                <th>Notes</th>
                <th>Added</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {targets.map(t => (
                <tr key={t.id}>
                  <td style={{ color: '#8b949e', fontSize: 12 }}>#{t.id}</td>
                  <td style={{ fontWeight: 600 }}>{t.name}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Link size={12} color="#8b949e" />
                      <span className="mono">{t.base_url}</span>
                    </div>
                  </td>
                  <td>
                    {t.auth_required
                      ? <span className="badge badge-Medium"><Lock size={10} style={{ marginRight: 4 }} />Required</span>
                      : <span className="badge badge-Info">None</span>}
                  </td>
                  <td style={{ color: '#8b949e', fontSize: 13, maxWidth: 200 }}>
                    {t.notes || <span style={{ opacity: 0.4 }}>—</span>}
                  </td>
                  <td style={{ color: '#8b949e', fontSize: 12 }}>
                    {new Date(t.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-ghost btn-sm"
                        onClick={() => { setEditTarget(t); setShowModal(true) }}>
                        <Edit3 size={13} /> Edit
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(t.id)}>
                        <Trash2 size={13} /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <TargetModal
          initial={editTarget}
          onSave={handleSave}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
