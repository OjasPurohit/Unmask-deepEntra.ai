// OWNER: Ojas. Backend URL (localStorage unmask_api) + test connection.
import { useState } from 'react'
import { api, BASE, setBase } from '../api'

export default function Settings() {
  const [url, setUrl] = useState(BASE)
  const [status, setStatus] = useState('')
  return (
    <section className="max-w-md space-y-3">
      <h1 className="text-xl font-semibold">Settings</h1>
      <input className="w-full rounded border border-line bg-card px-3 py-2" placeholder="http://192.168.x.x:8000"
        value={url} onChange={e => setUrl(e.target.value)} />
      <div className="flex gap-2">
        <button className="rounded bg-accent px-3 py-1 text-black" onClick={() => setBase(url)}>Save</button>
        <button className="rounded border border-line px-3 py-1" onClick={() => { setBase(null); setUrl(BASE) }}>Reset</button>
        <button className="rounded border border-line px-3 py-1" onClick={() =>
          api.health().then(h => setStatus(`OK · models_loaded=${h.models_loaded} · ${h.device}`), e => setStatus(String(e)))}>
          Test connection
        </button>
      </div>
      <p className="text-sm text-slate-400">{status}</p>
    </section>
  )
}
