export function apiUrl(apiBase) {
  // Missing runtime/build configuration must not crash the app at import time.
  // Compose and the local reverse proxy expose the backend at /api.
  const base = typeof apiBase === 'string' && apiBase.trim() ? apiBase.trim() : '/api'
  if (base.startsWith('/')) return base
  if (base.startsWith('http://') || base.startsWith('https://')) return base
  return `http://${base}`
}
