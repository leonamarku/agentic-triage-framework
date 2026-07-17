import { useState, useEffect } from 'react'
import { processRandom, processTicket, fetchProfiles } from '../api'
import ResultCard from '../components/ResultCard'

export default function ProcessPage() {
  const [profiles, setProfiles]     = useState([])
  const [profileId, setProfileId]   = useState('')
  const [ticketId, setTicketId]     = useState('')
  const [result, setResult]         = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [lastAction, setLastAction] = useState(null)

  useEffect(() => {
    fetchProfiles()
      .then(ps => setProfiles(ps))
      .catch(() => {})
  }, [])

  async function run(fn, label) {
    setLoading(true)
    setError(null)
    setResult(null)
    setLastAction(label)
    try {
      const data = await fn()
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRandom = () =>
    run(() => processRandom(profileId || null), 'Random ticket')

  const handleTicket = (e) => {
    e.preventDefault()
    if (!ticketId.trim()) return
    run(
      () => processTicket(ticketId.trim(), profileId || null),
      `Ticket ${ticketId.trim()}`
    )
  }

  const selectedProfileName = profiles.find(p => p.id === profileId)?.name ?? 'Default'

  return (
    <div className="space-y-6">

      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-5 space-y-4">
        <h2 className="text-base font-semibold text-gray-200">Process a Ticket</h2>

        {/* Profile selector */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
            Company Profile
          </label>
          <select
            value={profileId}
            onChange={e => setProfileId(e.target.value)}
            className="w-full sm:w-64 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          >
            <option value="">Default (no profile)</option>
            {profiles.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          {/* Random button */}
          <button
            onClick={handleRandom}
            disabled={loading}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-semibold transition-colors"
          >
            {loading && lastAction === 'Random ticket' ? (
              <Spinner />
            ) : (
              <span>🎲</span>
            )}
            Random Ticket
          </button>

          {/* Specific ticket form */}
          <form onSubmit={handleTicket} className="flex gap-2 flex-1">
            <input
              type="text"
              value={ticketId}
              onChange={e => setTicketId(e.target.value)}
              placeholder="Enter ticket ID, e.g. 1000044793"
              className="flex-1 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
            <button
              type="submit"
              disabled={loading || !ticketId.trim()}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-semibold transition-colors"
            >
              {loading && lastAction !== 'Random ticket' ? <Spinner /> : 'Process'}
            </button>
          </form>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl p-4 text-red-300 text-sm">
          <span className="font-semibold">Error: </span>{error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center gap-3 text-gray-500 py-10">
          <Spinner className="w-5 h-5" />
          <span>Processing{profileId ? ` with ${selectedProfileName}` : ''}…</span>
        </div>
      )}

      {/* Result */}
      {!loading && result && (
        <ResultCard
          result={result}
          profileLabel={result.profile_used ? profiles.find(p => p.id === result.profile_used)?.name : null}
        />
      )}

    </div>
  )
}

function Spinner({ className = 'w-4 h-4' }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}
