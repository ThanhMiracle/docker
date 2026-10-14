import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = await readFile(new URL('../src/reviews.js', import.meta.url), 'utf8')
const { validateReviewFiles, reviewFormData } = await import(`data:text/javascript,${encodeURIComponent(source)}`)
const MB = 1024 * 1024

test('valid photos and videos are accepted within the shared limits', () => {
  assert.equal(validateReviewFiles([{ type: 'image/png', size: 5 * MB }, { type: 'video/mp4', size: 30 * MB }]), '')
  assert.equal(validateReviewFiles([]), '')
})

test('attachment count, format and per-file and total sizes are enforced', () => {
  for (const files of [
    Array(7).fill({ type: 'image/png', size: 1 }),
    [{ type: 'image/svg+xml', size: 10 }], [{ type: 'image/png', size: 0 }],
    [{ type: 'image/png', size: 5 * MB + 1 }], [{ type: 'video/mp4', size: 30 * MB + 1 }],
    [{ type: 'video/mp4', size: 25 * MB }, { type: 'video/webm', size: 20 * MB }]
  ]) assert.ok(validateReviewFiles(files))
})

test('review submission includes order, rating, trimmed comment and actual file bytes', () => {
  const photo = new File(['photo'], 'photo.png', { type: 'image/png' })
  const video = new File(['video'], 'unboxing.mp4', { type: 'video/mp4' })
  const data = reviewFormData(12, 4, '  Lovely product  ', [photo, video])
  assert.equal(data.get('order_id'), '12')
  assert.equal(data.get('rating'), '4')
  assert.equal(data.get('comment'), 'Lovely product')
  assert.deepEqual(data.getAll('files').map(file => file.name), ['photo.png', 'unboxing.mp4'])
})
