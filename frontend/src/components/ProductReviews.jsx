import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { REVIEW_ACCEPT, reviewFormData, reviewResponse, validateReviewFiles } from '../reviews'

export default function ProductReviews({ productId, api }) {
  const token = localStorage.getItem('token')
  const isAdmin = localStorage.getItem('is_admin') === 'true'
  const [page, setPage] = useState({ items: [], total: 0, average_rating: null })
  const [orders, setOrders] = useState(null)
  const [orderId, setOrderId] = useState('')
  const [rating, setRating] = useState('5')
  const [comment, setComment] = useState('')
  const [files, setFiles] = useState([])
  const [previews, setPreviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [moreBusy, setMoreBusy] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const section = useRef(null)

  const loadReviews = async (skip = 0, signal) => {
    const data = await reviewResponse(await fetch(`${api}/products/${productId}/reviews?skip=${skip}&limit=10`, { signal }))
    setPage(current => ({ ...data, items: skip ? [...current.items, ...data.items] : data.items }))
  }
  const loadEligibility = async signal => {
    const data = await reviewResponse(await fetch(`${api}/products/${productId}/review-eligibility`, {
      signal, headers: { Authorization: `Bearer ${token}` }
    }))
    setOrders(data.eligible_orders)
    setOrderId(current => data.eligible_orders.some(order => String(order.order_id) === current)
      ? current : String(data.eligible_orders[0]?.order_id || ''))
  }

  useEffect(() => {
    const controller = new AbortController()
    const tasks = [loadReviews(0, controller.signal)]
    if (token && !isAdmin) tasks.push(loadEligibility(controller.signal))
    Promise.all(tasks).catch(err => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    if (window.location.hash === '#reviews') section.current?.scrollIntoView({ block: 'start' })
    return () => controller.abort()
  }, [productId, api, token, isAdmin])

  useEffect(() => {
    const next = files.map(file => ({ file, url: URL.createObjectURL(file) }))
    setPreviews(next)
    return () => next.forEach(preview => URL.revokeObjectURL(preview.url))
  }, [files])

  const addFiles = event => {
    const next = [...files, ...event.target.files]
    const problem = validateReviewFiles(next)
    if (problem) setError(problem)
    else { setFiles(next); setError('') }
    event.target.value = ''
  }
  const submit = async event => {
    event.preventDefault()
    if (busy) return
    const problem = validateReviewFiles(files)
    if (problem || !comment.trim() || !orderId) { setError(problem || 'Choose a delivered order and write your review.'); return }
    setBusy(true); setError(''); setMessage('')
    try {
      await reviewResponse(await fetch(`${api}/products/${productId}/reviews`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` },
        body: reviewFormData(orderId, rating, comment, files)
      }))
      setComment(''); setFiles([]); setRating('5')
      setMessage('Thank you! Your review has been published.')
      await Promise.all([loadReviews(), loadEligibility()])
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  const loadMore = async () => {
    setMoreBusy(true)
    try { await loadReviews(page.items.length) }
    catch (err) { setError(err.message) }
    finally { setMoreBusy(false) }
  }

  return <section id="reviews" ref={section} className="product-reviews" aria-labelledby="reviews-heading">
    <div className="reviews-header">
      <div><p className="eyebrow">From our customers</p><h2 id="reviews-heading">Reviews &amp; unboxing</h2></div>
      {page.total > 0 && <div className="review-summary"><strong>{Number(page.average_rating).toFixed(1)} / 5</strong><span>{page.total} verified {page.total === 1 ? 'review' : 'reviews'}</span></div>}
    </div>
    {error && <div className="notice review-error" role="alert">{error}</div>}
    {message && <div className="notice" role="status">{message}</div>}
    {token && !isAdmin && orders?.length > 0 && <form className="review-form" onSubmit={submit}>
      <h3>How was your product?</h3>
      <p className="muted">Share your experience, photos and unboxing videos with other shoppers.</p>
      <fieldset disabled={busy}>
        <div className="review-form-row">
          <label>Delivered order<select aria-label="Delivered order" value={orderId} onChange={event => setOrderId(event.target.value)} required>
            {orders.map(order => <option key={order.order_id} value={order.order_id}>Order #{order.order_id} · {new Date(order.created_at).toLocaleDateString()}</option>)}
          </select></label>
          <label>Rating<select aria-label="Rating" value={rating} onChange={event => setRating(event.target.value)} required>
            {[5, 4, 3, 2, 1].map(value => <option key={value} value={value}>{'★'.repeat(value)} — {value} {value === 1 ? 'star' : 'stars'}</option>)}
          </select></label>
        </div>
        <label>Your review<textarea rows="4" maxLength="3000" value={comment} onChange={event => setComment(event.target.value)} placeholder="Tell us about the quality, fit or your first impressions…" required /></label>
        <label>Photos &amp; unboxing videos <span className="muted">(optional)</span><input type="file" accept={REVIEW_ACCEPT} multiple onChange={addFiles} /></label>
        <small className="muted">Up to 6 files. Photos: 5 MB each. MP4 / WebM videos: 30 MB each. Total: 40 MB.</small>
        {previews.length > 0 && <div className="review-media review-previews">{previews.map(({ file, url }, index) => <figure key={url}>
          {file.type.startsWith('video/') ? <video src={url} controls preload="metadata" playsInline /> : <img src={url} alt={`Selected review photo ${index + 1}`} />}
          <figcaption><span>{file.name}</span><button type="button" className="text-button" onClick={() => setFiles(current => current.filter((_, position) => position !== index))}>Remove</button></figcaption>
        </figure>)}</div>}
        <button type="submit">{busy ? 'Publishing review…' : 'Publish review'}</button>
      </fieldset>
    </form>}
    {!loading && !isAdmin && (!token ? <p className="muted"><Link to="/login">Sign in</Link> to review a product from your delivered orders.</p>
      : orders?.length === 0 && <p className="muted">You can review each product once per delivered order. <Link to="/orders">Check My Orders</Link></p>)}
    {loading ? <p className="muted">Loading reviews…</p> : page.items.length === 0 ? <p className="muted">No reviews yet. Share your experience after delivery.</p>
      : <div className="review-list">{page.items.map(review => <article key={review.id} className="review-card">
        <div className="review-card-header"><div><strong>{review.author_name}</strong><span className="verified-purchase">Verified purchase</span></div><time dateTime={review.created_at}>{new Date(review.created_at).toLocaleDateString()}</time></div>
        <p className="review-stars" aria-label={`${review.rating} out of 5 stars`}>{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</p>
        <p className="review-comment">{review.comment}</p>
        {review.media.length > 0 && <div className="review-media">{review.media.map((media, index) => <figure key={media.url}>
          {media.kind === 'video' ? <video src={media.url} controls preload="metadata" playsInline aria-label={`Unboxing video ${index + 1} by ${review.author_name}`} />
            : <a href={media.url} target="_blank" rel="noopener noreferrer"><img src={media.url} alt={`Review photo ${index + 1} by ${review.author_name}`} loading="lazy" /></a>}
        </figure>)}</div>}
      </article>)}</div>}
    {page.items.length < page.total && <button className="text-button" type="button" disabled={moreBusy} onClick={loadMore}>{moreBusy ? 'Loading…' : 'Load more reviews'}</button>}
  </section>
}
