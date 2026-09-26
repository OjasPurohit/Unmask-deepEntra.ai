// OWNER: Palash. KYC Verification Evidence Report.
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, apiUrl } from '../api'
import type { AnalysisResult } from '../types'

export default function Report() {
  const { id = '' } = useParams()
  const [r, setR] = useState<AnalysisResult>()
  useEffect(() => { api.getCase(id).then(setR) }, [id])
  if (!r) return <p>Loading…</p>
  return (
    <section>
      <h1 className="text-xl font-semibold">KYC Verification Evidence Report</h1>
      <p className="mt-2">{r.band} · {(r.fused_score * 100).toFixed(0)}% · {r.headline}</p>
      <img className="mt-4 max-w-full" src={apiUrl(r.overlay)} alt="heatmap overlay" />
      <p className="mt-4 text-sm text-slate-400">{r.disclaimer}</p>
    </section>
  )
}
