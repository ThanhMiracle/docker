import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../api'
import { chatSocketUrl, uploadChatImage } from '../chat'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}
const API = apiUrl(getApiBase())

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [body, setBody] = useState('')
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const fileInput = useRef(null)
  const token = localStorage.getItem('token')
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  const load = async () => {
    const response = await fetch(`${API}/chat/messages`, { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new Error('Could not load chat')
    setMessages(await response.json())
  }
  const markRead = async () => {
    await fetch(`${API}/chat/read`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
    window.dispatchEvent(new Event('chat-read'))
  }

  useEffect(() => {
    if (!token || isAdmin || !open) return
    load().then(markRead).catch(() => setError('Could not load messages.'))
  }, [open, token, isAdmin]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!token || isAdmin) return
    const socket = new WebSocket(chatSocketUrl(getApiBase(), token))
    socket.onmessage = event => {
      const payload = JSON.parse(event.data)
      if (payload.type !== 'chat_message') return
      setMessages(current => current.some(message => message.id === payload.message.id) ? current : [...current, payload.message])
      if (open) markRead().catch(() => {})
      window.dispatchEvent(new Event('chat-event'))
    }
    return () => socket.close()
  }, [token, isAdmin, open]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!token || isAdmin) return null
  const send = async event => {
    event.preventDefault()
    if (!body.trim() && !file) return
    try {
      const attachment_url = file ? await uploadChatImage(API, token, file) : null
      const response = await fetch(`${API}/chat/messages`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: body.trim(), attachment_url })
      })
      if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not send message.')
      const message = await response.json()
      setMessages(current => current.some(item => item.id === message.id) ? current : [...current, message])
      setBody(''); setFile(null); if (fileInput.current) fileInput.current.value = ''
      setError('')
    } catch (message) { setError(message.message) }
  }

  return <aside className={`messenger ${open ? 'messenger--open' : ''}`}>
    {open && <section className="messenger-window"><header><div><strong>Shop support</strong><span>Live support</span></div><button type="button" aria-label="Close chat" onClick={() => setOpen(false)}>×</button></header><div className="messenger-messages">{messages.length ? messages.map(message => <div key={message.id} className={message.sender_id === message.customer_id ? 'bubble bubble--customer' : 'bubble bubble--admin'}>{message.body && <span>{message.body}</span>}{message.attachment_url && <img className="chat-image" src={message.attachment_url} alt="Chat attachment" />}</div>) : <p>Hi! How can we help you today?</p>}</div>{error && <small className="messenger-error">{error}</small>}<form onSubmit={send}><input placeholder="Type a message…" value={body} onChange={event => setBody(event.target.value)} /><label className="attach-button" title="Attach image">📎<input ref={fileInput} type="file" accept="image/*" onChange={event => setFile(event.target.files?.[0] || null)} /></label><button type="submit">Send</button></form>{file && <small className="attachment-name">{file.name}</small>}</section>}
    <button className="messenger-launcher" type="button" onClick={() => setOpen(!open)} aria-label="Open support chat">{open ? '×' : '💬'}</button>
  </aside>
}
