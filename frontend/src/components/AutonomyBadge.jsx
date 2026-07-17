const STYLES = {
  autonomous:     'bg-emerald-900 text-emerald-200',
  agent_assisted: 'bg-yellow-900 text-yellow-200',
  human_required: 'bg-red-900 text-red-200',
}

const LABELS = {
  autonomous:     '✓ Autonomous',
  agent_assisted: '⚡ Agent Assisted',
  human_required: '⚠ Human Required',
}

export default function AutonomyBadge({ level }) {
  const style = STYLES[level] ?? STYLES.human_required
  const label = LABELS[level] ?? level
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${style}`}>
      {label}
    </span>
  )
}
