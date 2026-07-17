import { useState } from 'react'
import { compareProfiles } from '../api'
import CompareCard from '../components/CompareCard'
import RiskBadge from '../components/RiskBadge'
import AutonomyBadge from '../components/AutonomyBadge'

// Suggested ticket IDs for quick testing
const DEMO_TICKETS = [
  { id: '1000044793', label: 'Payment flag — divergence showcase' },
  { id: '1000041868', label: 'Routine low — should be autonomous' },
  { id: '1000001258', label: 'High GT, no flags' },
  { id: '1000027919', label: 'Security flag — hard override' },
  { id: '1000013820', label: 'Enterprise + FinTech' },
]

export default function ComparePage() {
  const [ticketId, setTicketId] = useState('')
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  async function handleCompare(e) {
    e.preventDefault()
    const id = ticketId.trim()
    if (!id) return
    setLoading(true)
    setError(null)
    setData(null)
    try {
      setData(await compareProfiles(id))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function loadDemo(id) {
    setTicketId(id)
  }

  const profiles = data ? Object.keys(data.results_by_profile) : []
  const diverged = data?.divergence_summary?.diverged

  return (
    <div className="space-y-6">

      {/* Controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-5 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-200">Compare Profiles</h2>
          <p className="text-xs text-gray-500 mt-1">
            Process the same ticket through all profiles simultaneously and see where decisions diverge.
          </p>
        </div>

        {/* Quick-select demos */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2">
            Quick-select demo ticket
          </p>
          <div className="flex flex-wrap gap-2">
            {DEMO_TICKETS.map(t => (
              <button
                key={t.id}
                onClick={() => loadDemo(t.id)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                  ticketId === t.id
                    ? 'border-indigo-500 bg-indigo-900 text-indigo-200'
                    : 'border-gray-700 bg-gray-800 text-gray-400 hover:text-gray-200 hover:border-gray-600'
                }`}
              >
                <span className="font-mono">{t.id}</span>
                <span className="ml-1.5 text-gray-500">— {t.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input + submit */}
        <form onSubmit={handleCompare} className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={ticketId}
            onChange={e => setTicketId(e.target.value)}
            placeholder="Ticket ID"
            className="flex-1 sm:max-w-xs bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
          <button
            type="submit"
            disabled={loading || !ticketId.trim()}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Spinner /> : null}
            Compare
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950 border border-red-800 rounded-xl p-4 text-red-300 text-sm">
          <span className="font-semibold">Error: </span>{error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center gap-3 text-gray-500 py-10">
          <Spinner className="w-5 h-5" />
          <span>Running ticket through all profiles…</span>
        </div>
      )}

      {/* Results */}
      {!loading && data && (
        <div className="space-y-5">

          {/* Ticket summary */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-5">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div>
                <p className="text-xs text-gray-500">Ticket</p>
                <p className="font-mono text-lg font-bold text-white">{data.ticket_id}</p>
              </div>
              {diverged ? (
                <span className="text-sm font-semibold text-amber-400 bg-amber-900/40 border border-amber-700 px-3 py-1 rounded-full">
                  ⚡ Profiles diverged
                </span>
              ) : (
                <span className="text-sm font-semibold text-gray-400 bg-gray-800 border border-gray-700 px-3 py-1 rounded-full">
                  ✓ All profiles agreed
                </span>
              )}
            </div>

            {/* Ticket meta */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-4">
              {[
                ['Industry',  data.ticket_summary?.industry],
                ['Tier',      data.ticket_summary?.customer_tier],
                ['Affected',  data.ticket_summary?.customers_affected],
                ['GT Priority', data.ticket_summary?.ground_truth_priority || '—'],
                ['Error Rate', `${data.ticket_summary?.error_rate_pct?.toFixed(1)}%`],
                ['Downtime',  `${data.ticket_summary?.downtime_min}min`],
                ['Pay Flag',  data.ticket_summary?.payment_impact_flag ? '⚠ Yes' : 'No'],
                ['Sec Flag',  data.ticket_summary?.security_incident_flag ? '⚠ Yes' : 'No'],
              ].map(([label, val]) => (
                <div key={label}>
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-gray-200 font-medium">{String(val)}</p>
                </div>
              ))}
            </div>

            {/* Decision summary table */}
            <div className="border-t border-gray-800 pt-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">
                Decision Comparison
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 uppercase tracking-wide">
                      <th className="text-left pb-2 pr-4">Profile</th>
                      <th className="text-left pb-2 pr-4">Risk</th>
                      <th className="text-left pb-2 pr-4">Score</th>
                      <th className="text-left pb-2 pr-4">Autonomy</th>
                      <th className="text-left pb-2">Escalation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {profiles.map(pid => {
                      const r = data.results_by_profile[pid]
                      return (
                        <tr key={pid}>
                          <td className="py-2 pr-4 font-mono text-indigo-400">{pid}</td>
                          <td className="py-2 pr-4"><RiskBadge level={r.risk_level} /></td>
                          <td className="py-2 pr-4 font-mono text-gray-300">{r.risk_score?.toFixed(3)}</td>
                          <td className="py-2 pr-4"><AutonomyBadge level={r.autonomy_level} /></td>
                          <td className="py-2">
                            <span className={r.escalation_required ? 'text-red-400 font-semibold' : 'text-emerald-400'}>
                              {r.escalation_required ? '⚠ YES' : '✓ No'}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Per-profile cards */}
          <div className={`grid gap-5 ${profiles.length === 3 ? 'lg:grid-cols-3' : 'sm:grid-cols-2'}`}>
            {profiles.map(pid => (
              <CompareCard
                key={pid}
                profileId={pid}
                result={data.results_by_profile[pid]}
              />
            ))}
          </div>

        </div>
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
