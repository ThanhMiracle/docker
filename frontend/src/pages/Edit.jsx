import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiUrl } from '../api'

// Lấy API_BASE runtime (docker) > build-time (vite) > fallback
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

export default function Edit() {
  const { id } = useParams()
  const nav = useNavigate()

  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [stock, setStock] = useState('0')
  const [images, setImages] = useState([])
  const [newFiles, setNewFiles] = useState([])
  const [imageUrl, setImageUrl] = useState('')
  const [description, setDescription] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  // load product data ban đầu
  useEffect(() => {
    ;(async () => {
      const res = await fetch(`${API}/products/${id}`)
      if (res.ok) {
        const p = await res.json()
        setName(p.name)
        setPrice(p.price)
        setStock(String(p.stock ?? 0))
        setImages(p.images?.length ? p.images : (p.image_url ? [p.image_url] : []))
        setDescription(p.description || '')
      } else {
        console.error('Failed to fetch product', res.status)
      }
    })()
  }, [id])

  const save = async e => {
    e.preventDefault()

    const token = localStorage.getItem('token')
    if (!token) {
      alert('Please login first')
      return
    }

    setSaving(true)
    setMessage('')
    try {
      const uploadedImages = []
      for (const file of newFiles) {
        const form = new FormData()
        form.append('file', file)
        const upload = await fetch(`${API}/files/upload`, {
          method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form
        })
        if (!upload.ok) throw new Error((await upload.json().catch(() => null))?.detail || `Could not upload ${file.name}`)
        uploadedImages.push((await upload.json()).url)
      }

      const allImages = [...images, ...uploadedImages]
      const body = {
      name,
      price: Number(price),
      stock: Number(stock),
      image_url: allImages[0] || null,
      images: allImages,
      description
      }

      const res = await fetch(`${API}/products/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      })

      if (res.ok) {
        nav('/')
      } else if (res.status === 403) {
        setMessage('Forbidden: only an admin can edit products.')
      } else {
        setMessage((await res.json().catch(() => null))?.detail || 'Could not update product.')
      }
    } catch (error) {
      setMessage(error.message)
    } finally {
      setSaving(false)
    }
  }

  const addImageUrl = () => {
    const url = imageUrl.trim()
    if (url && !images.includes(url)) setImages(current => [...current, url])
    setImageUrl('')
  }

  const del = async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      alert('Please login first')
      return
    }

    if (!confirm('Delete this product?')) return

    const res = await fetch(`${API}/products/${id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (res.ok) {
      alert('Deleted')
      nav('/')
    } else if (res.status === 403) {
      alert('Forbidden: only owner can delete')
    } else {
      alert(await res.text())
    }
  }

  return (
    <main className="form-page">
      <section className="form-card">
      <p className="eyebrow">Admin studio</p>
      <h1>Edit product</h1>
      {message && <div className="notice">{message}</div>}
      <form onSubmit={save} className="form-stack">
        <input
          placeholder="Name"
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <input placeholder="Stock quantity" type="number" min="0" value={stock} onChange={e => setStock(e.target.value)} />
        <input
          placeholder="Price"
          type="number"
          step="0.01"
          value={price}
          onChange={e => setPrice(e.target.value)}
        />
        <div className="image-editor">
          <label>Product images</label>
          <p className="muted">The first image is the main product image. Remove and add images to replace it.</p>
          {images.length > 0 && <div className="image-editor-grid">{images.map((image, index) => <figure key={image}><img src={image} alt={`Product image ${index + 1}`} /><figcaption>{index === 0 ? 'Main image' : `Image ${index + 1}`}<button type="button" onClick={() => setImages(current => current.filter(value => value !== image))}>Remove</button></figcaption></figure>)}</div>}
          <input type="file" accept="image/*" multiple onChange={e => setNewFiles([...e.target.files])} />
          {newFiles.length > 0 && <small>{newFiles.length} new image{newFiles.length === 1 ? '' : 's'} will be uploaded when you save.</small>}
          <div className="image-url-row"><input placeholder="Add image URL" value={imageUrl} onChange={e => setImageUrl(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addImageUrl() } }} /><button type="button" onClick={addImageUrl}>Add URL</button></div>
        </div>
        <textarea
          placeholder="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          <button
            type="button"
            onClick={del}
            style={{ background: '#f66' }}
          >
            Delete
          </button>
        </div>
      </form>
      </section>
    </main>
  )
}
