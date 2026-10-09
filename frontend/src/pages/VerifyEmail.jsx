import React, { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiUrl } from '../api'

function getApiBase() {
  if (
    typeof window !== 'undefined' &&
    window.__ENV__ &&
    typeof window.__ENV__.API_BASE === 'string' &&
    window.__ENV__.API_BASE.trim() !== ''
  ) {
    return window.__ENV__.API_BASE
  }

  if (
    import.meta &&
    import.meta.env &&
    typeof import.meta.env.VITE_API_BASE === 'string' &&
    import.meta.env.VITE_API_BASE.trim() !== ''
  ) {
    return import.meta.env.VITE_API_BASE
  }

  return 'http://localhost:8000'
}

const API_BASE = getApiBase()

const API = apiUrl(API_BASE)

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const [message, setMessage] = useState('Verifying your email...')
  const [success, setSuccess] = useState(false)
  const verificationRequest = useRef(null)

  useEffect(() => {
    const token = searchParams.get('token')
    let active = true
    setSuccess(false)
    setMessage('Verifying your email...')

    if (!token) {
      setMessage('Verification token is missing.')
      return
    }

    const verifyEmail = async () => {
      const response = await fetch(`${API}/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      })
      const data = await response.json().catch(() => ({
        detail: 'Could not reach the verification service. Open the app through the Nginx address.'
      }))
      if (!response.ok) {
        throw new Error(data.detail || 'Email verification failed')
      }
      return data
    }

    // Reuse the request when StrictMode runs the effect twice. Confirmation
    // creates an account and consumes the link, so it must be sent only once.
    if (verificationRequest.current?.token !== token) {
      verificationRequest.current = { token, promise: verifyEmail() }
    }
    verificationRequest.current.promise.then(() => {
      if (active) {
        setSuccess(true)
        setMessage('Your email has been verified and your account is ready. You can now log in.')
      }
    }).catch(error => {
      if (active) setMessage(error.message)
    })
    return () => { active = false }
  }, [searchParams])

  return (
    <div
      style={{
        maxWidth: 600,
        margin: '60px auto',
        padding: 24,
        fontFamily: 'system-ui, sans-serif'
      }}
    >
      <h2>Email Verification</h2>

      <p>{message}</p>

      {success && (
        <p>
          <Link to="/login">Go to Login</Link>
        </p>
      )}
    </div>
  )
}
