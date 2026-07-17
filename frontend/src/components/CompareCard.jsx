import RiskBadge from './RiskBadge'
import AutonomyBadge from './AutonomyBadge'

/**
 * Compact card showing one profile's result inside the Compare view.
 */
export default function CompareCard({ profileId, result }) {
  if (!result) return null

  const PROFILE_LABELS = {
    default:     'Default',
    fintech:     'FinTech',
    saas_startup: 'SaaS Startup',
  }

  const PROFILE_ACCENT = {
    default:     'border-gray-700 bg-gray-900',
    fintech:     'border-blue-800 bg-blue-950',
    saas_startup: 'border-emerald-800 bg-emerald-950',
  }

  const label  = PROFILE_LABELS[profileId] ?? profileId
  const accent = PROFILE_ACCENT[profileId] ?? PROFILE_ACCENT.default

  const escalationColor = result.escalation_required
    ? 'text-red-400'
    : 'text-emerald-400'

  return (
    <div className={`border rounded-xl p-4 sm:p-5 space-y-4 ${accent}`}>

      {/* Profile header */}
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-base text-white">{label}</h3>
        <span className="text-xs text-gray-500 font-mono">{profileId}</span>
      </div>

      {/* Decision */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500 uppercase tracking-wide">Risk</span>
          <RiskBadge level={result.risk_level} />
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500 uppercase tracking-wide">Autonomy</span>
          <AutonomyBadge level={result.autonomy_level} />
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500 uppercase tracking-wide">Score</span>
          <span className="font-mono text-sm text-gray-300">{result.risk_score?.toFixed(3)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500 uppercase tracking-wide">Confidence</span>
          <span className="font-mono text-sm text-gray-300">{(result.confidence_score * 100).toFixed(0)}%</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500 uppercase tracking-wide">Escalation</span>
          <span className={`text-sm font-semibold ${escalationColor}`}>
            {result.escalation_required ? '⚠ YES' : '✓ No'}
          </span>
        </div>
      </div>

      {/* Escalation reason */}
      {result.escalation_reason && (
        <p className="text-xs text-gray-400 border-t border-gray-800 pt-3 leading-relaxed">
          {result.escalation_reason}
        </p>
      )}

      {/* Top risk factors */}
      {result.risk_factors?.length > 0 && (
        <div className="border-t border-gray-800 pt-3 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2">
            Risk Factors
          </p>
          {result.risk_factors.slice(0, 3).map((f, i) => (
            <p key={i} className="text-xs text-gray-400 flex gap-1.5">
              <span className="text-gray-600 shrink-0">›</span>{f}
            </p>
          ))}
        </div>
      )}

      {/* Reasoning */}
      <div className="border-t border-gray-800 pt-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2">
          Reasoning
        </p>
        <p className="text-xs text-gray-400 leading-relaxed line-clamp-6">
          {result.reasoning}
        </p>
      </div>

      {/* Generated output */}
      <div className="border-t border-gray-800 pt-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-2">
          Generated Output
        </p>
        <pre className="whitespace-pre-wrap font-sans text-xs text-gray-400 leading-relaxed bg-black/30 rounded-lg p-3 max-h-48 overflow-y-auto">
          {result.generated_output}
        </pre>
      </div>

    </div>
  )
}
