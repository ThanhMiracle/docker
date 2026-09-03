import { useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { apiUrl } from '../api'

const INACTIVITY_LIMIT_MS = 10 * 60 * 1000
const ACTIVITY_KEY = 'shop_last_activity_at'

function getApiBase() {
  if (window.__ENV__?.API_BASE?.trim()) return window.__ENV__.API_BASE
  if (import.meta.env?.VITE_API_BASE?.trim()) return import.meta.env.VITE_API_BASE
  return ''
}

const API = apiUrl(getApiBase())

export default function SessionTimeout() {
  const nav = useNavigate()
  const location = useLocation()
  const timer = useRef(null)

  useEffect(() => {
    if (!localStorage.getItem('token')) return undefined

    const logoutForInactivity = () => {
      const token = localStorage.getItem('token')
      if (!token) return
      // Best-effort server logout; browser access is removed even if offline.
      fetch(`${API}/auth/logout`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } }).catch(() => {})
      localStorage.removeItem('token')
      localStorage.removeItem('is_admin')
      localStorage.removeItem('user_email')
      localStorage.removeItem(ACTIVITY_KEY)
      nav('/login?reason=inactive', { replace: true })
    }
    const scheduleLogout = () => {
      window.clearTimeout(timer.current)
      const lastActivity = Number(localStorage.getItem(ACTIVITY_KEY)) || Date.now()
      timer.current = window.setTimeout(logoutForInactivity, Math.max(0, INACTIVITY_LIMIT_MS - (Date.now() - lastActivity)))
    }
    const recordActivity = () => {
      localStorage.setItem(ACTIVITY_KEY, String(Date.now()))
      scheduleLogout()
    }
    const syncActivity = event => {
      if (event.key === ACTIVITY_KEY && event.newValue) scheduleLogout()
      if (event.key === 'token' && !event.newValue) nav('/login', { replace: true })
    }

    const events = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart']
    events.forEach(event => window.addEventListener(event, recordActivity, { passive: true }))
    window.addEventListener('storage', syncActivity)
    recordActivity()
    return () => {
      window.clearTimeout(timer.current)
      events.forEach(event => window.removeEventListener(event, recordActivity))
      window.removeEventListener('storage', syncActivity)
    }
  }, [nav, location.key])

  return null
}
