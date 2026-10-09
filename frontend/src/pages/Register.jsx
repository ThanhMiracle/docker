import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiUrl } from '../api'

// --- Hàm lấy base URL ưu tiên runtime ---
function getApiBase() {
  // 1. runtime injection qua env.js
  if (
    typeof window !== 'undefined' &&
    window.__ENV__ &&
    typeof window.__ENV__.API_BASE === 'string' &&
    window.__ENV__.API_BASE.trim() !== ''
  ) {
    return window.__ENV__.API_BASE;
  }

  // 2. build-time fallback từ Vite lúc npm run build
  if (
    import.meta &&
    import.meta.env &&
    typeof import.meta.env.VITE_API_BASE === 'string' &&
    import.meta.env.VITE_API_BASE.trim() !== ''
  ) {
    return import.meta.env.VITE_API_BASE;
  }

  // 3. last resort cho dev local
  //return 'http://localhost:8000';
}


// Chuẩn hoá để đảm bảo có protocol
const API_BASE = getApiBase()
const API = apiUrl(API_BASE)

export default function Register() {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const register = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setMessage('')
    setError('')
    try {
      const r = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) {
        const detail = typeof data.detail === 'string'
          ? data.detail
          : 'Please check your registration details and try again.'
        throw new Error(detail)
      }
      setMessage(data.message || 'Check your email to confirm registration. Your account will be created after confirmation.')
      setPassword('')
    } catch (error) {
      setError(error.message || 'Could not complete registration. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
      <p className="eyebrow">Start shopping</p>
      <h1>Create your account.</h1>
      <p>Save your cart and keep track of every order in one place.</p>
      <form className="form-stack" onSubmit={register}>
        <input
          placeholder="Full name"
          required
          maxLength={120}
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <input
          placeholder="Email"
          type="email"
          required
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <input
          placeholder="Password"
          type="password"
          required
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button type="submit" disabled={submitting}>{submitting ? 'Sending confirmation...' : 'Create account'}</button>
      </form>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      <p className="auth-footer">Already registered? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  )
}
