export function apiUrl(apiBase) {
  if (apiBase.startsWith('/')) return apiBase
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) return apiBase
  return `http://${apiBase}`
}
