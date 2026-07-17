const RISK_STYLES = {
  0: 'bg-gray-700 text-gray-200',
  1: 'bg-blue-900 text-blue-200',
  2: 'bg-yellow-900 text-yellow-200',
  3: 'bg-orange-900 text-orange-200',
  4: 'bg-red-900 text-red-200',
}

const RISK_LABELS = {
  0: 'Minimal',
  1: 'Low',
  2: 'Moderate',
  3: 'High',
  4: 'Critical',
}

export default function RiskBadge({ level }) {
  const style = RISK_STYLES[level] ?? RISK_STYLES[0]
  const label = RISK_LABELS[level] ?? 'Unknown'
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${style}`}>
      <span className="text-xs font-bold">{level}/4</span>
      {label}
    </span>
  )
}
