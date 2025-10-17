import { useState } from 'react'
const API = import.meta.env.VITE_API_BASE || 'http://${VITE_API_BASE}'
export default function Register() {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('')
  const register = async () => {
    const r = await fetch(`${API}/auth/register`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password}) })
    if (r.ok) { alert('Registered! You can login now.'); } else { alert(await r.text()); }
  }
  return (<div style={{maxWidth:420, margin:'60px auto', fontFamily:'system-ui'}}>
    <h1>Register</h1>
    <div style={{display:'grid', gap:12}}>
      <input placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)}/>
      <input placeholder="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)}/>
      <button onClick={register}>Register</button>
    </div>
  </div>)
}
