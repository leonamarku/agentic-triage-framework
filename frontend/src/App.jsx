import { useState } from 'react'
import ProcessPage from './pages/ProcessPage'
import ComparePage from './pages/ComparePage'

const TABS = [
  { id: 'process', label: 'Process Ticket' },
  { id: 'compare', label: 'Compare Profiles' },
]

export default function App() {
  const [tab, setTab] = useState('process')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">

      {/* Top bar */}
      <header className="border-b border-gray-800 bg-gray-900/80 sticky top-0 z-10 backdrop-blur">
        <div className="max-w-6xl mx-auto px-3 sm:px-4 py-3 sm:py-4 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-sm sm:text-lg font-bold tracking-tight text-white truncate">
              Agentic Triage Framework
            </h1>
            <p className="text-[10px] sm:text-xs text-gray-500 mt-0.5 truncate">
              Risk-aware autonomy allocation · Phase 3 dashboard
            </p>
          </div>
          <span className="shrink-0 text-xs bg-indigo-900 text-indigo-300 px-2 py-1 rounded font-semibold">
            v0.3.0
          </span>
        </div>
      </header>

      {/* Tab navigation */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-3 sm:px-4">
          <nav className="flex gap-1">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex-1 sm:flex-none text-center px-2 sm:px-4 py-2.5 sm:py-3 text-xs sm:text-sm font-medium border-b-2 transition-colors ${
                  tab === t.id
                    ? 'border-indigo-500 text-indigo-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Page content */}
      <main className="max-w-6xl mx-auto px-3 sm:px-4 py-5 sm:py-8">
        {tab === 'process' && <ProcessPage />}
        {tab === 'compare' && <ComparePage />}
      </main>

    </div>
  )
}
