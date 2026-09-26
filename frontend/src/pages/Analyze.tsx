// OWNER: Palash. Drag-drop + camera capture + sample gallery + progress steps.
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Analyze() {
  const nav = useNavigate()
  async function onFile(f?: File) {
    if (!f) return
    const r = await api.analyze(f)
    nav(`/case/${r.case_id}`)
  }
  return (
    <section>
      <h1 className="text-xl font-semibold">Explainable manipulation screening for KYC identity photos</h1>
      <input className="mt-4" type="file" accept="image/*" capture="user" onChange={e => onFile(e.target.files?.[0])} />
    </section>
  )
}
