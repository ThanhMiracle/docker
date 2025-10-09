import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export default function Products() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(12)
  const [total, setTotal] = useState(0)
  const load = async () => {
    const res = await fetch(`${API}/products/?` + new URLSearchParams({ q, skip, limit }))
    const data = await res.json(); setItems(data.items); setTotal(data.total)
  }
  useEffect(() => { load() }, [q, skip, limit])
  return (<div style={{maxWidth:1000, margin:'40px auto', fontFamily:'system-ui'}}>
    <h1>Products</h1>
    <div style={{display:'flex', gap:8, marginBottom:12}}>
      <input placeholder="Search..." value={q} onChange={e=>{setQ(e.target.value); setSkip(0)}}/>
      <select value={limit} onChange={e=>{setLimit(Number(e.target.value)); setSkip(0)}}>
        <option value={6}>6</option><option value={12}>12</option><option value={24}>24</option>
      </select><div style={{marginLeft:'auto'}}>Total: {total}</div>
    </div>
    <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(220px,1fr))', gap:16}}>
      {items.map(p => (<div key={p.id} style={{border:'1px solid #eee', borderRadius:8, padding:12}}>
        {p.image_url && (
          <img src={p.image_url} alt={p.name} style={{width:'100%', height:150, objectFit:'cover', borderRadius:6}} />
                )}
        <div style={{fontWeight:600, marginTop:8}}>{p.name}</div>
        <div>${Number(p.price).toFixed(2)}</div>
        {p.description && <div style={{fontSize:12, opacity:.8}}>{p.description}</div>}
        <div style={{marginTop:8}}><Link to={`/edit/${p.id}`}>Edit</Link></div>
      </div>))}
    </div>
    <div style={{display:'flex', gap:8, marginTop:16}}>
      <button disabled={skip<=0} onClick={()=>setSkip(Math.max(0, skip-limit))}>Prev</button>
      <button disabled={skip+limit>=total} onClick={()=>setSkip(skip+limit)}>Next</button>
    </div>
  </div>)
}
