import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

// Lấy API_BASE runtime (docker) > build-time (vite) > fallback
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

export default function Edit() {
  const { id } = useParams()
  const nav = useNavigate()

  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [image_url, setImageUrl] = useState('')
  const [description, setDescription] = useState('')

  // load product data ban đầu
  useEffect(() => {
    ;(async () => {
      const res = await fetch(`${API}/products/${id}`)
      if (res.ok) {
        const p = await res.json()
        setName(p.name)
        setPrice(p.price)
        setImageUrl(p.image_url || '')
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

    const body = {
      name,
      price: Number(price),
      image_url,
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
      alert('Updated!')
      nav('/')
    } else if (res.status === 403) {
      alert('Forbidden: only owner can edit')
    } else {
      alert(await res.text())
    }
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
    <div style={{ maxWidth: 600, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>Edit Product #{id}</h1>
      <form onSubmit={save} style={{ display: 'grid', gap: 12 }}>
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
          placeholder="Image URL"
          value={image_url}
          onChange={e => setImageUrl(e.target.value)}
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="submit">Save</button>
          <button
            type="button"
            onClick={del}
            style={{ background: '#f66' }}
          >
            Delete
          </button>
        </div>
      </form>
    </div>
  )
}
