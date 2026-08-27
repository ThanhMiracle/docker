import { useState } from 'react'
import { apiUrl } from '../api'

// Hàm lấy API base URL theo ưu tiên:
// 1. window.__ENV__.API_BASE (runtime trong container, do docker-entrypoint.sh inject)
// 2. import.meta.env.VITE_API_BASE (lúc dev bằng Vite)
// 3. fallback cuối cùng: http://localhost:8000
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


// Ghép URL chuẩn có http://
const API_BASE = getApiBase()
const API = apiUrl(API_BASE)

export default function Create() {
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [files, setFiles] = useState([])
  const [colors, setColors] = useState([])
  const [colorInput, setColorInput] = useState('')
  const [description, setDescription] = useState('')

  const submit = async e => {
    e.preventDefault()

    const token = localStorage.getItem('token')
    if (!token) {
      alert('Please login first')
      return
    }

    const images = []

    // 1. Upload file nếu có
    for (const file of files) {
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
      images.push(u.url)
    }

    // 2. Gửi dữ liệu sản phẩm
    const body = {
      name,
      price: Number(price),
      image_url: images[0] || '',
      images,
      colors,
      description,
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
      setFiles([])
      setColors([])
      setColorInput('')
      setDescription('')
    } else {
      alert(await res.text())
    }
  }

  return (
    <main className="form-page">
      <section className="form-card">
      <p className="eyebrow">Admin studio</p>
      <h1>Add a product</h1>
      <form onSubmit={submit} className="form-stack">
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
          multiple
          accept="image/*"
          onChange={e => setFiles([...e.target.files])}
        />
        <div className="colour-builder">
          <label>Available colours</label>
          <div className="colour-add-row">
            <input placeholder="e.g. Red" value={colorInput} onChange={e => setColorInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); const colour = colorInput.trim(); if (colour && !colors.includes(colour)) { setColors([...colors, colour]); setColorInput('') } } }} />
            <button type="button" onClick={() => { const colour = colorInput.trim(); if (colour && !colors.includes(colour)) { setColors([...colors, colour]); setColorInput('') } }}>Add colour</button>
          </div>
          {colors.length > 0 && <div className="colour-options">{colors.map(colour => <span className="admin-colour-chip" key={colour}>{colour}<button type="button" aria-label={`Remove ${colour}`} onClick={() => setColors(colors.filter(value => value !== colour))}>×</button></span>)}</div>}
        </div>
        <textarea
          placeholder="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        <button type="submit">Publish product</button>
      </form>
      </section>
    </main>
  )
}
