import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return 'http://localhost:8000'
}

const API = apiUrl(getApiBase())

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [conversations, setConversations] = useState([])
  const [body, setBody] = useState('')
  const [customerId, setCustomerId] = useState(null)
  const [error, setError] = useState('')
  const nav = useNavigate()
  const token = localStorage.getItem('token')
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  const load = async () => {
    const response = await fetch(`${API}/chat/messages`, { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not load messages')
    setMessages(await response.json())
  }
  const loadConversations = async () => {
    if (!isAdmin) return
    const response = await fetch(`${API}/chat/conversations`, { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new Error('Could not load customer conversations')
    const data = await response.json()
    setConversations(data)
    if (!customerId && data[0]) setCustomerId(data[0].customer_id)
  }

  useEffect(() => {
    if (!token) { nav('/login'); return }
    load().catch(message => setError(message.message))
    loadConversations().catch(message => setError(message.message))
    const timer = setInterval(() => load().catch(() => {}), 10000)
    return () => clearInterval(timer)
  }, [token, nav]) // eslint-disable-line react-hooks/exhaustive-deps

  const send = async event => {
    event.preventDefault()
    if (!body.trim()) return
    try {
      const response = await fetch(`${API}/chat/messages`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ body, customer_id: isAdmin ? Number(customerId) || null : null })
      })
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not send message')
      setBody('')
      await load()
      await loadConversations()
    } catch (message) { setError(message.message) }
  }

  const activeConversation = conversations.find(item => item.customer_id === customerId)
  const thread = messages.filter(message => !isAdmin || message.customer_id === customerId)

  if (!isAdmin) return <main className="inbox-page"><section className="inbox customer-inbox"><aside className="conversation-list shop-profile"><div className="shop-avatar">M</div><div><p className="eyebrow">Customer support</p><h2>Moss &amp; Market</h2><p className="muted">Ask about products, orders, or delivery.</p></div><div className="support-status"><span />Support team · Active</div></aside><section className="conversation-thread"><header><p className="eyebrow">Messenger</p><h2>Chat with the shop</h2></header>{error && <div className="notice">{error}</div>}<div className="thread-messages">{messages.length ? messages.map(message => <article className={message.sender_id === message.customer_id ? 'thread-bubble admin' : 'thread-bubble customer'} key={message.id}><p>{message.body}</p><small>{message.sender_id === message.customer_id ? 'You · ' : 'Support · '}{new Date(message.created_at).toLocaleString()}</small></article>) : <div className="empty-thread"><div className="shop-avatar">M</div><h3>Start a conversation</h3><p>Send us a message and our support team will reply here.</p></div>}</div><form className="thread-composer" onSubmit={send}><textarea rows="2" placeholder="Write a message…" value={body} onChange={event => setBody(event.target.value)} /><button type="submit">Send</button></form></section></section></main>

  return <main className="inbox-page"><section className="inbox"><aside className="conversation-list"><div><p className="eyebrow">Customer support</p><h2>Inbox</h2></div>{conversations.map(conversation => <button type="button" className={customerId === conversation.customer_id ? 'conversation active' : 'conversation'} key={conversation.customer_id} onClick={() => setCustomerId(conversation.customer_id)}><strong>{conversation.customer_email}</strong><span>{conversation.last_message}</span><small>{new Date(conversation.last_message_at).toLocaleString()}</small></button>)}</aside><section className="conversation-thread"><header><p className="eyebrow">Conversation</p><h2>{activeConversation?.customer_email || 'Choose a customer'}</h2></header>{error && <div className="notice">{error}</div>}<div className="thread-messages">{thread.map(message => <article className={message.sender_id === message.customer_id ? 'thread-bubble customer' : 'thread-bubble admin'} key={message.id}><p>{message.body}</p><small>{new Date(message.created_at).toLocaleString()}</small></article>)}</div><form className="thread-composer" onSubmit={send}><textarea rows="2" disabled={!customerId} placeholder="Reply to this customer…" value={body} onChange={event => setBody(event.target.value)} /><button disabled={!customerId} type="submit">Send</button></form></section></section></main>
}
