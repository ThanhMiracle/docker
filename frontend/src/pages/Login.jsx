import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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


const API_BASE = getApiBase()
const API = apiUrl(API_BASE)

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const nav = useNavigate()

  const login = async () => {
    const form = new URLSearchParams({ username: email, password })
    const r = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form
    })
    if (r.ok) {
      const data = await r.json()
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('is_admin', String(data.is_admin))
      localStorage.setItem('user_email', email.trim().toLowerCase())
      alert('Logged in!')
      nav('/')
    } else {
      alert(await r.text())
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
      <p className="eyebrow">Welcome back</p>
      <h1>Good to see you.</h1>
      <p>Sign in to continue shopping and manage your orders.</p>
      <div className="form-stack">
        <input
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button onClick={login}>Sign in</button>
      </div>
      <p className="auth-footer">New here? <Link to="/register">Create an account</Link></p>
      </section>
    </main>
  )
}
