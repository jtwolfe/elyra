import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

function App() {
  const [userName, setUserName] = useState(() => {
    return window.localStorage.getItem('elyra.userName') ?? 'Jamie'
  })
  const projectId = 'core'
  const [messages, setMessages] = useState<
    {
      id: number
      role: 'user' | 'assistant'
      content: string
      thought?: string
      trace?: {
        knot?: {
          id: string
          primary_episode_id: string
          start_ts: string
          end_ts: string
          summary: string
        }
        deltas?: {
          id: string
          kind: string
          ts: string
          payload: unknown
        }[]
      }
    }[]
  >([])
  const [input, setInput] = useState('')
  const [showInternals, setShowInternals] = useState(false)
  const [rightTab, setRightTab] = useState<'turn' | 'inspect'>('turn')
  const [inspectSnapshot, setInspectSnapshot] = useState<any | null>(null)
  const [inspectError, setInspectError] = useState<string | null>(null)
  const [showResetModal, setShowResetModal] = useState(false)
  const [resetConfirm, setResetConfirm] = useState('')
  const [resetBusy, setResetBusy] = useState(false)
  const [resetError, setResetError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const nextIdRef = useRef(1)

  useEffect(() => {
    window.localStorage.setItem('elyra.userName', userName)
  }, [userName])

  useEffect(() => {
    const wsUrl = (() => {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const host = window.location.hostname
      const port = 8000
      return `${proto}://${host}:${port}/chat/${encodeURIComponent(
        userName.trim() || 'Jamie',
      )}/${projectId}`
    })()

    const socket = new WebSocket(wsUrl)
    wsRef.current = socket

    socket.onopen = () => {
      // WebSocket connection established.
      // We intentionally keep this silent in the UI.
      // eslint-disable-next-line no-console
      console.debug('Elyra WebSocket connected')
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'assistant_message') {
          setMessages((prev) => [
            ...prev,
            {
              id: nextIdRef.current++,
              role: 'assistant',
              content: data.content ?? '',
              thought: data.thought ?? '',
              trace: data.trace,
            },
          ])
        } else if (data.type === 'error') {
          setMessages((prev) => [
            ...prev,
            {
              id: nextIdRef.current++,
              role: 'assistant',
              content: data.content ?? 'Backend error',
              thought: '',
              trace: data.trace,
            },
          ])
        }
      } catch {
        // Ignore malformed messages for now.
      }
    }

    socket.onerror = () => {
      // Log connection issues to the console without polluting the chat.
      // eslint-disable-next-line no-console
      console.error('Connection error talking to Elyra backend.')
    }

    return () => {
      socket.close()
    }
  }, [userName])

  useEffect(() => {
    if (rightTab !== 'inspect') return

    let cancelled = false
    const host = window.location.hostname
    const port = 8000
    const baseUrl = `${window.location.protocol}//${host}:${port}`

    const tick = async () => {
      try {
        const res = await fetch(
          `${baseUrl}/inspect/${encodeURIComponent(
            userName.trim() || 'Jamie',
          )}/${projectId}/snapshot?deltas_limit=200&knots_limit=50`,
        )
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setInspectSnapshot(data)
          setInspectError(null)
        }
      } catch (e: any) {
        if (!cancelled) {
          setInspectError(e?.message ?? 'Failed to fetch inspector snapshot.')
        }
      }
    }

    tick()
    const id = window.setInterval(tick, 2000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [rightTab])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const text = input.trim()
    if (!text) return

    setMessages((prev) => [
      ...prev,
      { id: nextIdRef.current++, role: 'user', content: text },
    ])
    setInput('')

    const socket = wsRef.current
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ content: text }))
    }
  }

  const doResetAll = async () => {
    setResetBusy(true)
    setResetError(null)
    try {
      const host = window.location.hostname
      const port = 8000
      const baseUrl = `${window.location.protocol}//${host}:${port}`
      const res = await fetch(`${baseUrl}/admin/reset/all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: resetConfirm }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`)
      setMessages([])
      setInspectSnapshot(null)
      setResetConfirm('')
      setShowResetModal(false)
    } catch (e: any) {
      setResetError(e?.message ?? 'Reset failed.')
    } finally {
      setResetBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col">
      <header className="border-b border-slate-800 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Elyra</h1>
            <p className="text-xs text-slate-400">
              Living, memory-driven assistant – Braid v2 dev UI
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">User</label>
            <input
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              className="w-44 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
              placeholder="Your name"
            />
            <span className="text-xs text-slate-500">
              braid: <span className="text-slate-200">core</span>
            </span>
          </div>
        </div>
        <p className="text-xs text-slate-400">
          This is a dev UI; multi-user/multi-session comes later.
        </p>
      </header>

      <main className="flex-1 grid gap-4 p-4 md:grid-cols-[2fr,1fr]">
        <section className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/40">
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <p className="text-sm text-slate-500">
                Start a conversation to see Elyra&apos;s responses here.
              </p>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'ml-auto bg-sky-600 text-white'
                    : 'mr-auto bg-slate-800 text-slate-50'
                }`}
              >
                <p>{m.content}</p>
              </div>
            ))}
          </div>

          <form
            onSubmit={handleSubmit}
            className="border-t border-slate-800 px-4 py-3 flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Elyra something…"
              className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
            />
            <button
              type="submit"
              className="inline-flex items-center rounded-md bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
              disabled={!input.trim()}
            >
              Send
            </button>
          </form>
        </section>

        <aside className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/40">
          <div className="border-b border-slate-800 px-4 py-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-medium text-slate-100">
                Internal state
              </h2>
              <p className="text-xs text-slate-500">
                Thought summary + braid inspector (Braid v2).
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="px-2 py-1 text-xs rounded-md border border-red-700 text-red-200 hover:bg-red-950/40"
                onClick={() => setShowResetModal(true)}
              >
                Reset all
              </button>
              <div className="flex rounded-md border border-slate-700 overflow-hidden">
                <button
                  type="button"
                  className={`px-2 py-1 text-xs ${
                    rightTab === 'turn' ? 'bg-slate-800 text-slate-50' : 'bg-transparent text-slate-300'
                  }`}
                  onClick={() => setRightTab('turn')}
                >
                  Turn trace
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 text-xs ${
                    rightTab === 'inspect' ? 'bg-slate-800 text-slate-50' : 'bg-transparent text-slate-300'
                  }`}
                  onClick={() => setRightTab('inspect')}
                >
                  Inspector
                </button>
              </div>
              <label className="flex items-center gap-1 text-xs text-slate-400">
                <input
                  type="checkbox"
                  className="h-3 w-3 rounded border-slate-600 bg-slate-900"
                  checked={showInternals}
                  onChange={(e) => setShowInternals(e.target.checked)}
                />
                <span>Show deltas</span>
              </label>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
            {rightTab === 'turn' ? (
              messages.filter((m) => m.role === 'assistant' && m.thought).length === 0 ? (
                <p className="text-sm text-slate-500">
                  Elyra&apos;s internal thoughts will appear here after the first response.
                </p>
              ) : (
                <div className="space-y-3">
                  {messages
                    .filter((m) => m.role === 'assistant' && m.thought)
                    .map((m) => (
                      <div key={m.id} className="space-y-2">
                        <div>
                          <p className="font-semibold text-slate-200 mb-1">Thought</p>
                          <p className="whitespace-pre-line text-slate-300 text-sm">{m.thought}</p>
                        </div>
                        {m.trace?.knot && (
                          <div className="rounded-md border border-slate-800 bg-slate-950/60 p-2 space-y-1">
                            <p className="font-semibold text-slate-200 mb-1 text-xs">Knot</p>
                            <p className="text-slate-300">
                              <span className="text-slate-400">id:</span> {m.trace.knot.id}
                            </p>
                            <p className="text-slate-300">
                              <span className="text-slate-400">episode:</span> {m.trace.knot.primary_episode_id}
                            </p>
                            <p className="text-slate-300">
                              <span className="text-slate-400">summary:</span> {m.trace.knot.summary}
                            </p>
                          </div>
                        )}
                        {showInternals && (
                          <div className="space-y-2 rounded-md border border-slate-800 bg-slate-950/60 p-2">
                            <div>
                              <p className="font-semibold text-slate-200 mb-1 text-xs">Deltas (latest)</p>
                              <pre className="whitespace-pre-wrap text-slate-300">
                                {m.trace?.deltas && m.trace.deltas.length > 0
                                  ? JSON.stringify(m.trace.deltas, null, 2)
                                  : 'No deltas yet.'}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              )
            ) : (
              <div className="space-y-3">
                <div className="rounded-md border border-slate-800 bg-slate-950/60 p-2">
                  <p className="font-semibold text-slate-200 mb-1 text-xs">Inspector (live)</p>
                  <p className="text-slate-400">
                    braid: <span className="text-slate-200">{(userName.trim() || 'Jamie') + ':' + projectId}</span>
                  </p>
                  {inspectError && <p className="text-red-300 mt-2">error: {inspectError}</p>}
                </div>

                {inspectSnapshot ? (
                  <div className="space-y-3">
                    <div className="rounded-md border border-slate-800 bg-slate-950/60 p-2 space-y-1">
                      <p className="font-semibold text-slate-200 mb-1 text-xs">Summary</p>
                      <p className="text-slate-300">
                        <span className="text-slate-400">deltas:</span>{' '}
                        {Array.isArray(inspectSnapshot.deltas) ? inspectSnapshot.deltas.length : 0}
                        {'  '}
                        <span className="text-slate-400">knots:</span>{' '}
                        {Array.isArray(inspectSnapshot.knots) ? inspectSnapshot.knots.length : 0}
                        {'  '}
                        <span className="text-slate-400">episodes:</span>{' '}
                        {Array.isArray(inspectSnapshot.episodes) ? inspectSnapshot.episodes.length : 0}
                        {'  '}
                        <span className="text-slate-400">beads:</span>{' '}
                        {Array.isArray(inspectSnapshot.beads) ? inspectSnapshot.beads.length : 0}
                      </p>
                      <p className="text-slate-300">
                        <span className="text-slate-400">active episode:</span>{' '}
                        {inspectSnapshot.active_episode?.id ?? '(none)'}
                      </p>
                    </div>

                    <div className="rounded-md border border-slate-800 bg-slate-950/60 p-2">
                      <p className="font-semibold text-slate-200 mb-1 text-xs">Snapshot JSON</p>
                      <pre className="whitespace-pre-wrap text-slate-300">
                        {JSON.stringify(inspectSnapshot, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">Loading snapshot…</p>
                )}
              </div>
            )}
          </div>
        </aside>
      </main>

      {showResetModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-50">Reset all (dangerous)</h3>
            <p className="text-xs text-slate-400">
              This will wipe Neo4j + Qdrant data for all braids. Type <span className="text-slate-200">reset</span> to confirm.
            </p>
            <input
              type="text"
              value={resetConfirm}
              onChange={(e) => setResetConfirm(e.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500"
              placeholder="type reset"
            />
            {resetError && <p className="text-xs text-red-300">{resetError}</p>}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="px-3 py-2 text-xs rounded-md border border-slate-700 text-slate-200 hover:bg-slate-900"
                onClick={() => {
                  setShowResetModal(false)
                  setResetError(null)
                  setResetConfirm('')
                }}
                disabled={resetBusy}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 text-xs rounded-md bg-red-700 text-white hover:bg-red-600 disabled:opacity-50"
                onClick={doResetAll}
                disabled={resetBusy || resetConfirm !== 'reset'}
              >
                {resetBusy ? 'Resetting…' : 'Confirm reset'}
              </button>
            </div>
            <p className="text-[10px] text-slate-500">
              Note: backend must be started with <span className="text-slate-200">ELYRA_ENABLE_DANGEROUS_ADMIN=1</span>.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
