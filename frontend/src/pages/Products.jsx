import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

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

function getSignedInEmail() {
  const storedEmail = localStorage.getItem('user_email')
  if (storedEmail) return storedEmail

  try {
    const payload = localStorage.getItem('token')?.split('.')[1]
    return payload ? JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))).sub : ''
  } catch {
    return ''
  }
}

export default function Products() {
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(12)
  const [total, setTotal] = useState(0)
  const [message, setMessage] = useState('')
  const [selectedColors, setSelectedColors] = useState({})
  const signedInEmail = getSignedInEmail()
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  const addToCart = async (productId, selectedColor) => {
    const token = localStorage.getItem('token')
    if (!token) {
      setMessage('Please log in to add products to your cart.')
      return
    }
    const res = await fetch(`${API}/cart/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ product_id: productId, quantity: 1, selected_color: selectedColor || null })
    })
    if (res.ok) setMessage('Added to cart.')
    else setMessage((await res.json().catch(() => null))?.detail || 'Could not add product to cart.')
  }

  const load = async () => {
    const qs = new URLSearchParams({ q, skip, limit })
    const res = await fetch(`${API}/products/?${qs.toString()}`)
    if (!res.ok) {
      console.error('Failed to load products', res.status)
      return
    }
    const data = await res.json()
    setItems(data.items)
    setTotal(data.total)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, skip, limit])

  return (
    <main className="page">
      <div className="page-header"><div><p className="eyebrow">Thoughtfully selected</p><h1>Find something lovely.</h1></div><div className="account-summary">{signedInEmail ? <>Shopping as <strong>{signedInEmail}</strong></> : 'Sign in to save your cart and orders.'}</div></div>
      {message && <div className="notice">{message}</div>}

      <div className="toolbar">
        <input
          placeholder="Search..."
          value={q}
          onChange={e => {
            setQ(e.target.value)
            setSkip(0)
          }}
        />
        <select
          value={limit}
          onChange={e => {
            setLimit(Number(e.target.value))
            setSkip(0)
          }}
        >
          <option value={6}>6</option>
          <option value={12}>12</option>
          <option value={24}>24</option>
        </select>
        <div className="total-label">{total} products</div>
      </div>

      <div className="product-grid">
        {items.map(p => (
          <div
            key={p.id}
            className="product-card"
          >
            {(p.images?.[0] || p.image_url) && (
              <img
                src={p.images?.[0] || p.image_url}
                alt={p.name}
                style={{
                  width: '100%',
                  height: 150,
                  objectFit: 'cover',
                  borderRadius: 6
                }}
              />
            )}

            <div className="product-card__body">
            <div className="product-card__name">{p.name}</div>
            <div className="product-card__price">${Number(p.price).toFixed(2)}</div>

            {p.description && (
              <div className="product-card__description">
                {p.description}
              </div>
            )}

            {p.images?.length > 1 && <div className="product-thumbnails">{p.images.slice(1, 4).map((image, index) => <img key={image} src={image} alt={`${p.name} view ${index + 2}`} />)}{p.images.length > 4 && <span>+{p.images.length - 4}</span>}</div>}
            {p.colors?.length > 0 && <div className="colour-picker"><span>Colour</span><div className="colour-options">{p.colors.map(color => <button key={color} type="button" className={selectedColors[p.id] === color ? 'colour-option selected' : 'colour-option'} onClick={() => setSelectedColors({ ...selectedColors, [p.id]: color })}>{color}</button>)}</div></div>}

            <div className="product-card__actions">
              <button onClick={() => { if (p.colors?.length && !selectedColors[p.id]) { setMessage('Please choose a colour first.'); return } addToCart(p.id, selectedColors[p.id]) }}>Add to cart</button>
              {isAdmin && <Link to={`/edit/${p.id}`}>Edit</Link>}
            </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button
          disabled={skip <= 0}
          onClick={() => setSkip(Math.max(0, skip - limit))}
        >
          Prev
        </button>
        <button
          disabled={skip + limit >= total}
          onClick={() => setSkip(skip + limit)}
        >
          Next
        </button>
      </div>
    </main>
  )
}
