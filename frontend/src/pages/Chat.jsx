import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiUrl } from '../api'
import { chatSocketUrl, uploadChatImage } from '../chat'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}
const API_BASE = getApiBase()
const API = apiUrl(API_BASE)

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [conversations, setConversations] = useState([])
  const [body, setBody] = useState('')
  const [file, setFile] = useState(null)
  const [customerId, setCustomerId] = useState(null)
  const [error, setError] = useState('')
  const fileInput = useRef(null)
  const nav = useNavigate()
  const token = localStorage.getItem('token')
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  const headers = { Authorization: `Bearer ${token}` }
  const load = async () => {
    const response = await fetch(`${API}/chat/messages`, { headers })
    if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not load messages')
    setMessages(await response.json())
  }
  const loadConversations = async () => {
    if (!isAdmin) return
    const response = await fetch(`${API}/chat/conversations`, { headers })
    if (!response.ok) throw new Error('Could not load customer conversations')
    const data = await response.json()
    setConversations(data)
    setCustomerId(current => current || data[0]?.customer_id || null)
  }
  const markRead = async id => {
    const suffix = isAdmin ? `?customer_id=${id}` : ''
    const response = await fetch(`${API}/chat/read${suffix}`, { method: 'POST', headers })
    if (!response.ok) throw new Error('Could not mark messages as read')
    window.dispatchEvent(new Event('chat-read'))
  }

  useEffect(() => {
    if (!token) { nav('/login'); return }
    load().catch(message => setError(message.message))
    loadConversations().catch(message => setError(message.message))
  }, [token, nav]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!token || (isAdmin && !customerId)) return
    markRead(customerId).then(loadConversations).catch(() => {})
  }, [token, customerId, isAdmin]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!token) return
    const socket = new WebSocket(chatSocketUrl(API_BASE, token))
    socket.onmessage = event => {
      const payload = JSON.parse(event.data)
      if (payload.type !== 'chat_message') return
      setMessages(current => current.some(message => message.id === payload.message.id) ? current : [...current, payload.message])
      if (!isAdmin || payload.message.customer_id === customerId) markRead(payload.message.customer_id).catch(() => {})
      if (isAdmin) loadConversations().catch(() => {})
      window.dispatchEvent(new Event('chat-event'))
    }
    return () => socket.close()
  }, [token, isAdmin, customerId]) // eslint-disable-line react-hooks/exhaustive-deps

  const send = async event => {
    event.preventDefault()
    if (!body.trim() && !file) return
    try {
      const attachment_url = file ? await uploadChatImage(API, token, file) : null
      const response = await fetch(`${API}/chat/messages`, {
        method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: body.trim(), attachment_url, customer_id: isAdmin ? Number(customerId) || null : null })
      })
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not send message')
      const message = await response.json()
      setMessages(current => current.some(item => item.id === message.id) ? current : [...current, message])
      setBody(''); setFile(null); if (fileInput.current) fileInput.current.value = ''
      setError(''); await loadConversations()
    } catch (message) { setError(message.message) }
  }

  const activeConversation = conversations.find(item => item.customer_id === customerId)
  const thread = messages.filter(message => !isAdmin || message.customer_id === customerId)
  const bubble = message => <article className={message.sender_id === message.customer_id ? 'thread-bubble customer' : 'thread-bubble admin'} key={message.id}>{message.body && <p>{message.body}</p>}{message.attachment_url && <img className="chat-image" src={message.attachment_url} alt="Chat attachment" />}<small>{!isAdmin && (message.sender_id === message.customer_id ? 'You · ' : 'Support · ')}{new Date(message.created_at).toLocaleString()}</small></article>
  const composer = <form className="thread-composer" onSubmit={send}><textarea rows="2" disabled={isAdmin && !customerId} placeholder={isAdmin ? 'Reply to this customer…' : 'Write a message…'} value={body} onChange={event => setBody(event.target.value)} /><label className="attach-button" title="Attach image">📎<input ref={fileInput} type="file" accept="image/*" disabled={isAdmin && !customerId} onChange={event => setFile(event.target.files?.[0] || null)} /></label><button disabled={isAdmin && !customerId} type="submit">Send</button>{file && <small className="attachment-name">{file.name}</small>}</form>

  if (!isAdmin) return <main className="inbox-page"><section className="inbox customer-inbox"><aside className="conversation-list shop-profile"><div className="shop-avatar">M</div><div><p className="eyebrow">Customer support</p><h2>Moss &amp; Market</h2><p className="muted">Ask about products, orders, or delivery.</p></div><div className="support-status"><span />Live support</div></aside><section className="conversation-thread"><header><p className="eyebrow">Messenger</p><h2>Chat with the shop</h2></header>{error && <div className="notice">{error}</div>}<div className="thread-messages">{messages.length ? messages.map(bubble) : <div className="empty-thread"><div className="shop-avatar">M</div><h3>Start a conversation</h3><p>Send us a message and our support team will reply here.</p></div>}</div>{composer}</section></section></main>

  return <main className="inbox-page"><section className="inbox"><aside className="conversation-list"><div><p className="eyebrow">Customer support</p><h2>Inbox</h2></div>{conversations.map(conversation => <button type="button" className={customerId === conversation.customer_id ? 'conversation active' : 'conversation'} key={conversation.customer_id} onClick={() => setCustomerId(conversation.customer_id)}><strong>{conversation.customer_email}{conversation.unread_count > 0 && <b className="unread-badge">{conversation.unread_count}</b>}</strong><span>{conversation.last_message || 'Image attachment'}</span><small>{new Date(conversation.last_message_at).toLocaleString()}</small></button>)}</aside><section className="conversation-thread"><header><p className="eyebrow">Conversation</p><h2>{activeConversation?.customer_email || 'Choose a customer'}</h2></header>{error && <div className="notice">{error}</div>}<div className="thread-messages">{thread.map(bubble)}</div>{composer}</section></section></main>
}
