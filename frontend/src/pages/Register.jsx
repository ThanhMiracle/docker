import { useState } from 'react'

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
