import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}

const API_BASE = getApiBase()
const API = API_BASE.startsWith('http://') || API_BASE.startsWith('https://') ? API_BASE : `http://${API_BASE}`

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [message, setMessage] = useState('')
  const nav = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      nav('/login')
      return
    }
    fetch(`${API}/orders/mine`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async response => {
        if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not load orders')
        return response.json()
      })
      .then(setOrders)
      .catch(error => setMessage(error.message))
  }, [nav])

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>My Orders</h1>
      {message && <div style={{ marginBottom: 16, padding: 10, background: '#fff3f3', borderRadius: 6 }}>{message}</div>}
      {orders.length === 0 ? <p>No orders yet. <Link to="/">Start shopping</Link></p> : (
        <div style={{ display: 'grid', gap: 16 }}>
          {orders.map(order => (
            <article key={order.id} style={{ border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <strong>Order #{order.id}</strong>
                <strong>${Number(order.total).toFixed(2)}</strong>
              </div>
              <div style={{ fontSize: 13, opacity: 0.75, marginTop: 4 }}>{new Date(order.created_at).toLocaleString()}</div>
              <p style={{ marginBottom: 8 }}><strong>Delivery:</strong> {order.customer_name} · {order.phone}<br />{order.delivery_address}</p>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {order.items.map(item => <li key={`${order.id}-${item.product_id}`}>{item.product_name} × {item.quantity} — ${(item.unit_price * item.quantity).toFixed(2)}</li>)}
              </ul>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
