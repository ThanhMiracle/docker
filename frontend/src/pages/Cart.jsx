import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}

const API_BASE = getApiBase()
const API = API_BASE.startsWith('http://') || API_BASE.startsWith('https://') ? API_BASE : `http://${API_BASE}`

export default function Cart() {
  const [cart, setCart] = useState({ items: [], total: 0 })
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [checkoutDetails, setCheckoutDetails] = useState({ customer_name: '', phone: '', delivery_address: '' })
  const nav = useNavigate()
  const token = localStorage.getItem('token')

  const request = async (url, options = {}) => {
    const response = await fetch(`${API}${url}`, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers }
    })
    if (!response.ok) {
      const detail = (await response.json().catch(() => null))?.detail
      const errorMessage = Array.isArray(detail)
        ? detail.map(error => `${error.loc?.at(-1) || 'Field'}: ${error.msg}`).join('. ')
        : detail
      throw new Error(errorMessage || 'Something went wrong')
    }
    return response.json()
  }

  const load = async () => {
    if (!token) {
      nav('/login')
      return
    }
    try {
      setCart(await request('/cart'))
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const changeQuantity = async (productId, quantity, selectedColor) => {
    try {
      const color = selectedColor ? `?selected_color=${encodeURIComponent(selectedColor)}` : ''
      if (quantity < 1) setCart(await request(`/cart/items/${productId}${color}`, { method: 'DELETE' }))
      else setCart(await request(`/cart/items/${productId}`, { method: 'PUT', body: JSON.stringify({ quantity, selected_color: selectedColor || null }) }))
    } catch (error) { setMessage(error.message) }
  }

  const checkout = async () => {
    const details = {
      customer_name: checkoutDetails.customer_name.trim(),
      phone: checkoutDetails.phone.trim(),
      delivery_address: checkoutDetails.delivery_address.trim()
    }
    if (!details.customer_name || !details.phone || !details.delivery_address) {
      setMessage('Please enter your name, phone number, and delivery address.')
      return
    }
    if (details.phone.length < 3) {
      setMessage('Please enter a valid phone number (at least 3 characters).')
      return
    }
    if (details.delivery_address.length < 5) {
      setMessage('Please enter a delivery address of at least 5 characters.')
      return
    }
    try {
      const order = await request('/cart/checkout', {
        method: 'POST',
        body: JSON.stringify(details)
      })
      setMessage(`Order #${order.id} is waiting for email confirmation. Check your account email to finish placing it.`)
    } catch (error) { setMessage(error.message) }
  }

  if (loading) return <div style={{ maxWidth: 900, margin: '40px auto' }}>Loading cart…</div>

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>Your Cart</h1>
      {message && <div style={{ marginBottom: 16, padding: 10, background: '#f3f8ff', borderRadius: 6 }}>{message}</div>}
      {cart.items.length === 0 ? (
        <p>Your cart is empty. <Link to="/">Browse products</Link></p>
      ) : (
        <>
          <div style={{ display: 'grid', gap: 12 }}>
            {cart.items.map(item => (
              <div key={item.product_id} style={{ display: 'flex', gap: 16, alignItems: 'center', border: '1px solid #eee', padding: 12, borderRadius: 8 }}>
                {item.product.image_url && <img src={item.product.image_url} alt="" style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 6 }} />}
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{item.product.name}</div>
                  <div>${Number(item.product.price).toFixed(2)} each</div>
                  {item.selected_color && <div>Colour: {item.selected_color}</div>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button onClick={() => changeQuantity(item.product_id, item.quantity - 1, item.selected_color)}>−</button>
                  <span>{item.quantity}</span>
                  <button onClick={() => changeQuantity(item.product_id, item.quantity + 1, item.selected_color)}>+</button>
                </div>
                <strong>${(item.product.price * item.quantity).toFixed(2)}</strong>
                <button onClick={() => changeQuantity(item.product_id, 0, item.selected_color)}>Remove</button>
              </div>
            ))}
          </div>
          <section style={{ marginTop: 28, borderTop: '1px solid #eee', paddingTop: 20 }}>
            <h2 style={{ fontSize: 20 }}>Delivery information</h2>
            <div style={{ display: 'grid', gap: 10, maxWidth: 520 }}>
              <input
                required
                placeholder="Full name"
                value={checkoutDetails.customer_name}
                onChange={e => setCheckoutDetails({ ...checkoutDetails, customer_name: e.target.value })}
              />
              <input
                required
                minLength="3"
                placeholder="Phone number"
                value={checkoutDetails.phone}
                onChange={e => setCheckoutDetails({ ...checkoutDetails, phone: e.target.value })}
              />
              <textarea
                required
                minLength="5"
                rows="3"
                placeholder="Delivery address"
                value={checkoutDetails.delivery_address}
                onChange={e => setCheckoutDetails({ ...checkoutDetails, delivery_address: e.target.value })}
              />
            </div>
          </section>
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16, marginTop: 24 }}>
            <strong>Total: ${Number(cart.total).toFixed(2)}</strong>
            <button onClick={checkout}>Place order</button>
          </div>
        </>
      )}
    </div>
  )
}
