export const REVIEW_ACCEPT = 'image/jpeg,image/png,image/webp,image/gif,video/mp4,video/webm'
const TYPES = new Set(REVIEW_ACCEPT.split(','))
const MB = 1024 * 1024

export function validateReviewFiles(files) {
  if (files.length > 6) return 'Attach up to 6 photos or videos.'
  let total = 0
  for (const file of files) {
    if (!TYPES.has(file.type)) return 'Use JPEG, PNG, WebP, GIF, MP4 or WebM files.'
    if (!file.size) return 'Attachments must not be empty.'
    if (file.size > (file.type.startsWith('video/') ? 30 : 5) * MB) return 'Photos must be at most 5 MB; videos at most 30 MB.'
    total += file.size
  }
  if (total > 40 * MB) return 'Attachments must total at most 40 MB.'
  return ''
}

export function reviewFormData(orderId, rating, comment, files) {
  const form = new FormData()
  form.append('order_id', String(orderId))
  form.append('rating', String(rating))
  form.append('comment', comment.trim())
  files.forEach(file => form.append('files', file))
  return form
}

export async function reviewResponse(response) {
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Could not complete the review request. Please try again.')
  return data
}
