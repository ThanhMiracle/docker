import { useState } from 'react'

// Hàm lấy API base URL theo ưu tiên:
// 1. window.__ENV__.API_BASE (runtime trong container, do docker-entrypoint.sh inject)
// 2. import.meta.env.VITE_API_BASE (lúc dev bằng Vite)
// 3. fallback cuối cùng: http://localhost:8000
function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.API_BASE) {
    return window.__ENV__.API_BASE
  }
  if (import.meta?.env?.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE
  }
  return 'localhost:8000'
}

// Ghép URL chuẩn có http://
const API_BASE = getApiBase()
const API = API_BASE.startsWith('http://') || API_BASE.startsWith('https://')
  ? API_BASE
  : `http://${API_BASE}`

export default function Create() {
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [file, setFile] = useState(null)
  const [description, setDescription] = useState('')

  const submit = async e => {
    e.preventDefault()

    const token = localStorage.getItem('token')
    if (!token) {
      alert('Please login first')
      return
    }

    let image_url = ''

    // 1. Upload file nếu có
    if (file) {
      const fd = new FormData()
      fd.append('file', file)

      const up = await fetch(`${API}/files/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: fd
      })

      if (!up.ok) {
        alert('Upload failed')
        return
      }

      const u = await up.json()
      image_url = u.url
    }

    // 2. Gửi dữ liệu sản phẩm
    const body = {
      name,
      price: Number(price),
      image_url,
      description
    }

    const res = await fetch(`${API}/products/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body)
    })

    if (res.ok) {
      alert('Created!')
      setName('')
      setPrice('')
      setFile(null)
      setDescription('')
    } else {
      alert(await res.text())
    }
  }

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>Add Product</h1>
      <form onSubmit={submit} style={{ display: 'grid', gap: 12 }}>
        <input
          placeholder="Name"
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <input
          placeholder="Price"
          type="number"
          step="0.01"
          value={price}
          onChange={e => setPrice(e.target.value)}
        />
        <input
          type="file"
          accept="image/*"
          onChange={e => setFile(e.target.files?.[0] || null)}
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        <button type="submit">Create</button>
      </form>
    </div>
  )
}
