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
    <main className="auth-page">
      <section className="auth-card">
      <p className="eyebrow">Start shopping</p>
      <h1>Create your account.</h1>
      <p>Save your cart and keep track of every order in one place.</p>
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
        <button onClick={register}>Create account</button>
      </div>
      <p className="auth-footer">Already registered? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  )
}
