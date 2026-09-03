import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (typeof window !== 'undefined' && window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}

const API_BASE = getApiBase()
const API = apiUrl(API_BASE)

export default function ConfirmOrder() {
  const [params] = useSearchParams()
  const [message, setMessage] = useState('Confirming your order…')

  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      setMessage('This confirmation link is incomplete.')
      return
    }
    fetch(`${API}/orders/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    })
      .then(async response => {
        if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not confirm the order.')
        return response.json()
      })
      .then(order => setMessage(`Order #${order.id} is confirmed. Thank you for your purchase!`))
      .catch(error => setMessage(error.message))
  }, [params])

  return <div style={{ maxWidth: 600, margin: '60px auto', fontFamily: 'system-ui' }}><h1>Order confirmation</h1><p>{message}</p><Link to="/orders">View my orders</Link></div>
}
