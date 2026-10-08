import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

// Load the Vite ES module without changing the package's module settings.
const source = await readFile(new URL('../src/api.js', import.meta.url), 'utf8')
const { apiUrl } = await import(`data:text/javascript,${encodeURIComponent(source)}`)

test('missing API configuration uses the reverse proxy without crashing', () => {
  for (const value of [undefined, null, '', '  ', 123]) {
    assert.equal(apiUrl(value), '/api')
  }
})

test('relative proxy routes and explicit backend URLs are preserved', () => {
  for (const value of ['/api', 'http://localhost:8000', 'https://backend.example.com']) {
    assert.equal(apiUrl(value), value)
  }
})

test('surrounding whitespace is removed and hostnames retain legacy HTTP behavior', () => {
  assert.equal(apiUrl(' https://backend.example.com '), 'https://backend.example.com')
  assert.equal(apiUrl('localhost:8000'), 'http://localhost:8000')
})
