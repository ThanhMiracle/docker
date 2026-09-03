import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}

const API_BASE = getApiBase()
const API = apiUrl(API_BASE)

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [message, setMessage] = useState('')
  const [editingOrder, setEditingOrder] = useState(null)
  const [delivery, setDelivery] = useState({ phone: '', delivery_address: '' })
  const nav = useNavigate()
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  const cancelOrder = async orderId => {
    if (!window.confirm(`Cancel order #${orderId}?`)) return
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API}/orders/${orderId}/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not cancel the order')
      const cancelled = await response.json()
      setOrders(current => current.map(order => order.id === cancelled.id ? cancelled : order))
      setMessage(`Order #${orderId} has been cancelled.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  const startEditingDelivery = order => {
    setEditingOrder(order.id)
    setDelivery({ phone: order.phone, delivery_address: order.delivery_address })
  }

  const saveDelivery = async orderId => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API}/orders/${orderId}/delivery`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: delivery.phone.trim(), delivery_address: delivery.delivery_address.trim() })
      })
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not update delivery details')
      const updated = await response.json()
      setOrders(current => current.map(order => order.id === updated.id ? updated : order))
      setEditingOrder(null)
      setMessage(`Delivery details for order #${orderId} have been updated.`)
    } catch (error) {
      setMessage(error.message)
    }
  }

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      nav('/login')
      return
    }
    fetch(`${API}${isAdmin ? '/orders' : '/orders/mine'}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async response => {
        if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not load orders')
        return response.json()
      })
      .then(setOrders)
      .catch(error => setMessage(error.message))
  }, [nav])

  const nextOrderStatus = {
    confirmed: { status: 'preparing', label: 'Start preparing' },
    preparing: { status: 'shipping', label: 'Mark as shipping' },
    shipping: { status: 'delivered', label: 'Mark delivered' }
  }

  const advanceOrderStatus = async (orderId, next) => {
    if (!window.confirm(`${next.label} for order #${orderId}?`)) return
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API}/orders/${orderId}/status`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: next.status })
      })
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not update the order status')
      const updated = await response.json()
      setOrders(current => current.map(order => order.id === updated.id ? updated : order))
      setMessage(`Order #${orderId} is now ${updated.status}.`)
    } catch (error) { setMessage(error.message) }
  }

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>{isAdmin ? 'Order Management' : 'My Orders'}</h1>
      {message && <div style={{ marginBottom: 16, padding: 10, background: '#fff3f3', borderRadius: 6 }}>{message}</div>}
      {orders.length === 0 ? <p>No orders yet. <Link to="/">Start shopping</Link></p> : (
        <div style={{ display: 'grid', gap: 16 }}>
          {orders.map(order => (
            <article key={order.id} style={{ border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <div><strong>Order #{order.id}</strong><div className={`order-status order-status--${order.status}`}>{order.status.replace('_', ' ')}</div></div>
                <strong>${Number(order.total).toFixed(2)}</strong>
              </div>
              <div style={{ fontSize: 13, opacity: 0.75, marginTop: 4 }}>{new Date(order.created_at).toLocaleString()}</div>
              {editingOrder === order.id ? (
                <div className="delivery-editor">
                  <label>Phone number<input value={delivery.phone} onChange={event => setDelivery({ ...delivery, phone: event.target.value })} /></label>
                  <label>Delivery address<textarea rows="3" value={delivery.delivery_address} onChange={event => setDelivery({ ...delivery, delivery_address: event.target.value })} /></label>
                  <div><button onClick={() => saveDelivery(order.id)}>Save delivery details</button><button className="text-button" onClick={() => setEditingOrder(null)}>Cancel</button></div>
                </div>
              ) : <p style={{ marginBottom: 8 }}><strong>Delivery:</strong> {order.customer_name} · {order.phone}<br />{order.delivery_address}</p>}
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {order.items.map(item => <li key={`${order.id}-${item.product_id}-${item.selected_color || ''}`}>{item.product_name}{item.selected_color ? ` (${item.selected_color})` : ''} × {item.quantity} — ${(item.unit_price * item.quantity).toFixed(2)}</li>)}
              </ul>
              {!isAdmin && (order.status === 'pending_confirmation' || order.status === 'confirmed') && (
                <div className="order-actions"><button className="text-button" onClick={() => startEditingDelivery(order)}>Edit delivery</button><button className="cancel-order" onClick={() => cancelOrder(order.id)}>Cancel order</button></div>
              )}
              {isAdmin && nextOrderStatus[order.status] && <div className="order-actions"><button onClick={() => advanceOrderStatus(order.id, nextOrderStatus[order.status])}>{nextOrderStatus[order.status].label}</button></div>}
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
