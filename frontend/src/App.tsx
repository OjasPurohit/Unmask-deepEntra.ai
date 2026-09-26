import { NavLink, Route, Routes } from 'react-router-dom'
import Analyze from './pages/Analyze'
import Report from './pages/Report'
import Evaluation from './pages/Evaluation'
import ReviewQueue from './pages/Review'
import Settings from './pages/Settings'

const links = [
  ['/', 'Analyze'],
  ['/review', 'Review queue'],
  ['/evaluation', 'Evaluation'],
  ['/settings', 'Settings'],
] as const

export default function App() {
  return (
    <div className="min-h-screen">
      <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-card px-4 py-3">
        <span className="font-bold text-accent">Unmask</span>
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end
            className={({ isActive }) => `text-sm ${isActive ? 'text-accent' : 'text-slate-300 hover:text-white'}`}>
            {label}
          </NavLink>
        ))}
        <span className="ml-auto rounded-full border border-line px-2 py-0.5 text-xs text-slate-400">
          Human-in-the-loop · Probabilistic
        </span>
      </nav>
      <main className="mx-auto max-w-6xl p-4">
        <Routes>
          <Route path="/" element={<Analyze />} />
          <Route path="/case/:id" element={<Report />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
