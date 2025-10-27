import { useState } from 'react'

// --- Hàm lấy base URL ưu tiên runtime ---
function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.API_BASE) {
    return window.__ENV__.API_BASE
  }
  if (import.meta?.env?.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  return 'localhost:8000'
}

// Chuẩn hoá để đảm bảo có protocol
const API_BASE = getApiBase()
const API = API_BASE.startsWith('http://') || API_BASE.startsWith('https://')
  ? API_BASE
  : `http://${API_BASE}`

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const register = async () => {
    const r = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (r.ok) {
      alert('Registered! You can login now.')
    } else {
      alert(await r.text())
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: '60px auto', fontFamily: 'system-ui' }}>
      <h1>Register</h1>
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
        <button onClick={register}>Register</button>
      </div>
    </div>
  )
}
