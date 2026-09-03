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
  const nav = useNavigate()
  const token = localStorage.getItem('token')

  useEffect(() => {
    if (!token) { nav('/login'); return }
    fetch(`${API}/profile`, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => response.json())
      .then(data => setProfile(current => ({ ...current, ...data })))
      .catch(() => setMessage('Could not load profile.'))
  }, [token, nav])

  const save = async event => {
    event.preventDefault()
    const response = await fetch(`${API}/profile`, { method: 'PUT', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: profile.phone, delivery_address: profile.delivery_address }) })
    const data = await response.json().catch(() => null)
    if (!response.ok) { setMessage(data?.detail || 'Could not save profile.'); return }
    setProfile(data)
    setMessage('Profile saved. Checkout will use these details.')
  }

  return <main className="form-page"><section className="form-card"><p className="eyebrow">Your account</p><h1>Profile</h1><p className="muted">{profile.name} · {profile.email}</p>{message && <div className="notice">{message}</div>}<form className="form-stack" onSubmit={save}><input required minLength="3" placeholder="Phone number" value={profile.phone || ''} onChange={event => setProfile({ ...profile, phone: event.target.value })} /><textarea required minLength="5" rows="4" placeholder="Default delivery address" value={profile.delivery_address || ''} onChange={event => setProfile({ ...profile, delivery_address: event.target.value })} /><button type="submit">Save profile</button></form></section></main>
}
