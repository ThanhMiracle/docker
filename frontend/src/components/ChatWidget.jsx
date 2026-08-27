import { useEffect, useState } from 'react'
import { apiUrl } from '../api'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return 'http://localhost:8000'
}

const API = apiUrl(getApiBase())

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const token = localStorage.getItem('token')
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  const load = async () => {
    const response = await fetch(`${API}/chat/messages`, { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new Error('Could not load chat')
    setMessages(await response.json())
  }

  useEffect(() => {
    if (!token || isAdmin || !open) return
    load().catch(() => setError('Could not load messages.'))
    const timer = setInterval(() => load().catch(() => {}), 10000)
    return () => clearInterval(timer)
  }, [open, token, isAdmin]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!token || isAdmin) return null

  const send = async event => {
    event.preventDefault()
    if (!body.trim()) return
    try {
      const response = await fetch(`${API}/chat/messages`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ body })
      })
      if (!response.ok) throw new Error('Could not send message.')
      setBody('')
      setError('')
      await load()
    } catch (message) { setError(message.message) }
  }

  return <aside className={`messenger ${open ? 'messenger--open' : ''}`}>
    {open && <section className="messenger-window"><header><div><strong>Shop support</strong><span>We usually reply soon</span></div><button type="button" aria-label="Close chat" onClick={() => setOpen(false)}>×</button></header><div className="messenger-messages">{messages.length ? messages.map(message => <div key={message.id} className={message.sender_id === message.customer_id ? 'bubble bubble--customer' : 'bubble bubble--admin'}>{message.body}</div>) : <p>Hi! How can we help you today?</p>}</div>{error && <small className="messenger-error">{error}</small>}<form onSubmit={send}><input placeholder="Type a message…" value={body} onChange={event => setBody(event.target.value)} /><button type="submit">Send</button></form></section>}
    <button className="messenger-launcher" type="button" onClick={() => setOpen(!open)} aria-label="Open support chat">{open ? '×' : '💬'}</button>
  </aside>
}
