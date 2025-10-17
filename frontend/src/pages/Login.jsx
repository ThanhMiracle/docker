import { useState } from 'react'
const API = import.meta.env.VITE_API_BASE || 'http://${VITE_API_BASE}'
export default function Login() {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('')
  const login = async () => {
    const form = new URLSearchParams({ username: email, password })
    const r = await fetch(`${API}/auth/login`, { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: form })
    if(r.ok){ const data = await r.json(); localStorage.setItem('token', data.access_token); alert('Logged in!') } else alert(await r.text())
  }
  return (<div style={{maxWidth:420, margin:'60px auto', fontFamily:'system-ui'}}>
    <h1>Login</h1>
    <div style={{display:'grid', gap:12}}>
      <input placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)}/>
      <input placeholder="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)}/>
      <button onClick={login}>Login</button>
    </div>
  </div>)
}
