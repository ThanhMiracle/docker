import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return 'http://localhost:8000'
}

const API = apiUrl(getApiBase())

export default function Profile() {
  const [profile, setProfile] = useState({ name: '', email: '', phone: '', delivery_address: '' })
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const nav = useNavigate()
  const token = localStorage.getItem('token')

  useEffect(() => {
    if (!token) { nav('/login'); return }
    let active = true
    fetch(`${API}/profile`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async response => {
        if (!response.ok) throw new Error('Could not load profile. Please sign in again or retry.')
        return response.json()
      })
      .then(data => { if (active) setProfile(current => ({ ...current, ...data })) })
      .catch(err => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, nav])

  const save = async event => {
    event.preventDefault()
    if (saving) return
    setError(''); setMessage('')
    const name = profile.name.trim()
    if (!name) { setError('Please enter your name.'); return }
    const details = { name }
    if (profile.phone?.trim()) details.phone = profile.phone.trim()
    if (profile.delivery_address?.trim()) details.delivery_address = profile.delivery_address.trim()
    setSaving(true)
    try {
      const response = await fetch(`${API}/profile`, { method: 'PUT', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(details) })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        const detail = data?.detail
        throw new Error(Array.isArray(detail)
          ? detail.map(issue => `${issue.loc?.at(-1) || 'Field'}: ${issue.msg}`).join('. ')
          : typeof detail === 'string' ? detail : 'Could not save profile. Please try again.')
      }
      setProfile(data)
      setMessage('Profile saved. Checkout will use these details.')
    } catch (err) {
      setError(err.message || 'Could not save profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return <main className="form-page">
    <section className="form-card">
      <p className="eyebrow">Your account</p><h1>Profile</h1>
      <p className="muted">{profile.email}</p>
      {error && <div className="notice" role="alert">{error}</div>}
      {message && <div className="notice" role="status">{message}</div>}
      {loading ? <p className="muted">Loading profile…</p> : <form className="form-stack" onSubmit={save}>
        <label htmlFor="profile-name">Full name</label>
        <input id="profile-name" autoComplete="name" required maxLength={120} value={profile.name} onChange={event => setProfile({ ...profile, name: event.target.value })} disabled={saving} />
        <label htmlFor="profile-phone">Phone number (optional)</label>
        <input id="profile-phone" type="tel" autoComplete="tel" minLength={3} maxLength={40} placeholder="Phone number" value={profile.phone || ''} onChange={event => setProfile({ ...profile, phone: event.target.value })} disabled={saving} />
        <label htmlFor="profile-address">Default delivery address (optional)</label>
        <textarea id="profile-address" autoComplete="street-address" minLength={5} maxLength={500} rows={4} placeholder="Default delivery address" value={profile.delivery_address || ''} onChange={event => setProfile({ ...profile, delivery_address: event.target.value })} disabled={saving} />
        <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
      </form>}
    </section>
  </main>
}
