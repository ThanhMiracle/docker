import { apiUrl } from './api'

export function chatSocketUrl(apiBase, token) {
  const api = apiUrl(apiBase)
  const base = api.startsWith('/')
    ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${api}`
    : api.replace(/^http/, 'ws')
  return `${base}/chat/ws?token=${encodeURIComponent(token)}`
}

export async function uploadChatImage(api, token, file) {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${api}/chat/files/upload`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form
  })
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || 'Could not upload image')
  return (await response.json()).url
}
