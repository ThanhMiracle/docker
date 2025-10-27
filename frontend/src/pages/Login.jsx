import { useState } from 'react'

// --- Hàm lấy base URL ưu tiên runtime ---
function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.API_BASE) {
    return window.__ENV__.API_BASE
  }
  if (import.meta?.env?.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  //return 'localhost:8000'
}

const API_BASE = getApiBase()
const API = API_BASE.startsWith('http://') || API_BASE.startsWith('https://')
  ? API_BASE
  : `http://${API_BASE}`

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

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
      alert('Logged in!')
    } else {
      alert(await r.text())
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '60px auto', fontFamily: 'system-ui' }}>
      <h1>Login</h1>
      <div style={{ display: 'grid', gap: 12 }}>
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
        <button onClick={login}>Login</button>
      </div>
    </div>
  )
}
