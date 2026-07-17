/**
 * API client — all calls go through the Vite proxy at /api → http://localhost:8000
 * Never reference localhost:8000 directly in components.
 *
 * In production (e.g. a static build deployed to Render), there is no Vite dev
 * proxy, so the relative '/api' path would hit the static host instead of the
 * backend. Set VITE_API_BASE at build time (e.g. VITE_API_BASE=https://your-backend.onrender.com)
 * to point requests at the deployed backend. Falls back to the local dev proxy path if unset.
 */

const BASE = import.meta.env.VITE_API_BASE || '/api'

async function post(path) {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

/** Process a random ticket, optionally with a specific profile. */
export function processRandom(profileId = null) {
  const qs = profileId ? `?profile_id=${profileId}` : ''
  return post(`/tickets/process/random${qs}`)
}

/** Process a specific ticket by ID with an optional profile. */
export function processTicket(ticketId, profileId = null) {
  const qs = profileId ? `?profile_id=${profileId}` : ''
  return post(`/tickets/${ticketId}/process${qs}`)
}

/** Run the same ticket through all profiles and return a comparison. */
export function compareProfiles(ticketId) {
  return post(`/tickets/process/compare/${ticketId}`)
}

/** Fetch all available company profiles. */
export function fetchProfiles() {
  return get('/profiles')
}
