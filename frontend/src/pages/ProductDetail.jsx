import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}

const API = apiUrl(getApiBase())

export default function ProductDetail() {
  const { id } = useParams()
  const [product, setProduct] = useState(null)
  const [related, setRelated] = useState([])
  const [activeImage, setActiveImage] = useState('')
  const [selectedColor, setSelectedColor] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [message, setMessage] = useState('')
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  useEffect(() => {
    fetch(`${API}/products/${id}`).then(async response => {
      if (!response.ok) throw new Error('Product not found')
      return response.json()
    }).then(data => {
      setProduct(data)
      const images = data.images?.length ? data.images : (data.image_url ? [data.image_url] : [])
      setActiveImage(images[0] || '')
    }).catch(error => setMessage(error.message))

    fetch(`${API}/products/?limit=8`).then(response => response.ok ? response.json() : null)
      .then(data => setRelated((data?.items || []).filter(item => String(item.id) !== String(id)).slice(0, 4)))
      .catch(() => {})
  }, [id])

  const addToCart = async () => {
    const token = localStorage.getItem('token')
    if (!token) { setMessage('Please log in to add this product to your cart.'); return }
    if (product.colors?.length && !selectedColor) { setMessage('Please choose a colour.'); return }
    const response = await fetch(`${API}/cart/items`, {
      method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: product.id, quantity, selected_color: selectedColor || null })
    })
    if (response.ok) setMessage(`Added ${quantity} item${quantity === 1 ? '' : 's'} to your cart.`)
    else setMessage((await response.json().catch(() => null))?.detail || 'Could not add this product to your cart.')
  }

  if (message && !product) return <main className="page"><div className="notice">{message} <Link to="/">Return to shop</Link></div></main>
  if (!product) return <main className="page"><p className="muted">Loading product…</p></main>

  const images = product.images?.length ? product.images : (product.image_url ? [product.image_url] : [])
  return <main className="page product-detail-page">
    <Link className="back-link" to="/">← Back to shop</Link>
    {message && <div className="notice">{message}</div>}
    <section className="product-detail">
      <div className="product-gallery">
        <div className="product-main-image">{activeImage ? <img src={activeImage} alt={product.name} /> : <span>No image available</span>}</div>
        {images.length > 1 && <div className="product-gallery-thumbs">{images.map((image, index) => <button type="button" aria-label={`View image ${index + 1}`} className={activeImage === image ? 'active' : ''} key={image} onClick={() => setActiveImage(image)}><img src={image} alt={`${product.name} view ${index + 1}`} /></button>)}</div>}
      </div>
      <section className="product-detail-info">
        <p className="eyebrow">Moss &amp; Market</p>
        <h1>{product.name}</h1>
        <p className="detail-price">${Number(product.price).toFixed(2)}</p>
        <p className={product.stock > 0 ? 'stock-status in-stock' : 'stock-status out-of-stock'}>{product.stock > 0 ? `${product.stock} available` : 'Out of stock'}</p>
        {product.description && <p className="detail-description">{product.description}</p>}
        {product.colors?.length > 0 && <div className="detail-colours"><strong>Choose a colour</strong><div className="colour-options">{product.colors.map(color => <button type="button" key={color} className={selectedColor === color ? 'colour-option selected' : 'colour-option'} onClick={() => setSelectedColor(color)}>{color}</button>)}</div></div>}
        <div className="purchase-row"><label>Quantity<input type="number" min="1" max={product.stock} value={quantity} onChange={event => setQuantity(Math.max(1, Math.min(product.stock || 1, Number(event.target.value) || 1)))} /></label><button disabled={product.stock < 1} onClick={addToCart}>{product.stock > 0 ? 'Add to cart' : 'Out of stock'}</button>{isAdmin && <Link to={`/edit/${product.id}`}>Edit product</Link>}</div>
      </section>
    </section>
    {related.length > 0 && <section className="related-products"><div><p className="eyebrow">You may also like</p><h2>More from the shop</h2></div><div className="related-grid">{related.map(item => <Link className="related-card" key={item.id} to={`/products/${item.id}`}>{(item.images?.[0] || item.image_url) && <img src={item.images?.[0] || item.image_url} alt={item.name} />}<span>{item.name}</span><strong>${Number(item.price).toFixed(2)}</strong></Link>)}</div></section>}
  </main>
}
