import RiskBadge from './RiskBadge'
import AutonomyBadge from './AutonomyBadge'

function Field({ label, children }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1">{label}</p>
      <div className="text-sm text-gray-200">{children}</div>
    </div>
  )
}

function MetaPill({ label, value }) {
  return (
    <span className="inline-flex gap-1 text-xs bg-gray-800 rounded px-2 py-1">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-300 font-medium">{value}</span>
    </span>
  )
}

export default function ResultCard({ result, profileLabel }) {
  if (!result) return null

  const escalationColor = result.escalation_required
    ? 'text-red-400'
    : 'text-emerald-400'

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-6 space-y-5">

      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Ticket ID</p>
          <p className="font-mono text-lg font-bold text-white">{result.ticket_id}</p>
        </div>
        {profileLabel && (
          <span className="text-xs bg-indigo-900 text-indigo-300 px-2 py-1 rounded font-semibold">
            {profileLabel}
          </span>
        )}
      </div>

      {/* Ticket meta pills */}
      <div className="flex flex-wrap gap-2">
        <MetaPill label="Industry"   value={result.industry} />
        <MetaPill label="Tier"       value={result.customer_tier} />
        <MetaPill label="GT Priority" value={result.ground_truth_priority || '—'} />
        <MetaPill label="Profile"    value={result.profile_used || 'default'} />
        <MetaPill label="Mode"       value={result.processing_mode === 'full_llm' ? 'LLM' : 'Rule-based'} />
      </div>

      {/* Key decision row */}
      <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-4 gap-4">
        <Field label="Risk Level">
          <RiskBadge level={result.risk_level} />
        </Field>
        <Field label="Risk Score">
          <span className="font-mono text-base">{result.risk_score?.toFixed(3)}</span>
        </Field>
        <Field label="Autonomy">
          <AutonomyBadge level={result.autonomy_level} />
        </Field>
        <Field label="Confidence">
          <span className="font-mono text-base">{(result.confidence_score * 100).toFixed(0)}%</span>
        </Field>
      </div>

      {/* Escalation */}
      <Field label="Escalation">
        <span className={`font-semibold ${escalationColor}`}>
          {result.escalation_required ? '⚠ ESCALATED' : '✓ Not escalated'}
        </span>
        {result.escalation_reason && (
          <p className="text-gray-400 text-xs mt-1">{result.escalation_reason}</p>
        )}
      </Field>

      {/* Risk factors */}
      {result.risk_factors?.length > 0 && (
        <Field label="Risk Factors">
          <ul className="space-y-1 mt-1">
            {result.risk_factors.map((f, i) => (
              <li key={i} className="flex gap-2 text-gray-300 text-xs">
                <span className="text-gray-600 shrink-0">›</span>
                {f}
              </li>
            ))}
          </ul>
        </Field>
      )}

      {/* Reasoning */}
      <Field label="Agent Reasoning">
        <p className="text-gray-300 leading-relaxed">{result.reasoning}</p>
      </Field>

      {/* Generated output */}
      <Field label="Generated Output">
        <pre className="whitespace-pre-wrap font-sans text-gray-300 leading-relaxed bg-gray-800 rounded-lg p-4 text-xs">
          {result.generated_output}
        </pre>
      </Field>

      {/* Recommended action */}
      <Field label="Recommended Action">
        <p className="text-indigo-300 font-medium">{result.recommended_action}</p>
      </Field>

    </div>
  )
}
