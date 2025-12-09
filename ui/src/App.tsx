import { FormEvent, useEffect, useRef, useState } from 'react'
import './App.css'

function App() {
  const [messages, setMessages] = useState<
    {
      id: number
      role: 'user' | 'assistant'
      content: string
      thought?: string
      trace?: {
        tools_used?: string[]
        scratchpad?: string
        planned_tools?: { name: string; args: unknown }[]
        tool_results?: { name: string; args: unknown; result: unknown }[]
      }
    }[]
  >([])
  const [input, setInput] = useState('')
  const [showInternals, setShowInternals] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const nextIdRef = useRef(1)

  useEffect(() => {
    const wsUrl = (() => {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const host = window.location.hostname
      const port = 8000
      return `${proto}://${host}:${port}/chat/demo-user/demo-project`
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
  }, [])

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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex flex-col">
      <header className="border-b border-slate-800 px-4 py-3">
        <h1 className="text-lg font-semibold tracking-tight">Elyra</h1>
        <p className="text-xs text-slate-400">
          Living, memory-driven assistant – Phase 1 text-only MVP
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
                Thought from HippocampalSim plus basic trace info.
              </p>
            </div>
            <label className="flex items-center gap-1 text-xs text-slate-400">
              <input
                type="checkbox"
                className="h-3 w-3 rounded border-slate-600 bg-slate-900"
                checked={showInternals}
                onChange={(e) => setShowInternals(e.target.checked)}
              />
              <span>Show internals</span>
            </label>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
            {messages.filter((m) => m.role === 'assistant' && m.thought).length ===
            0 ? (
                <p className="text-sm text-slate-500">
                  Elyra&apos;s internal thoughts will appear here after the first
                  response.
                </p>
            ) : (
              <div className="space-y-3">
                {messages
                  .filter((m) => m.role === 'assistant' && m.thought)
                  .map((m) => (
                    <div key={m.id} className="space-y-2">
                      <div>
                        <p className="font-semibold text-slate-200 mb-1">
                          Thought
                        </p>
                        <p className="whitespace-pre-line text-slate-300 text-sm">
                          {m.thought}
                        </p>
                      </div>
                      {showInternals && (
                        <div className="space-y-2 rounded-md border border-slate-800 bg-slate-950/60 p-2">
                          <div>
                            <p className="font-semibold text-slate-200 mb-1 text-xs">
                              Tools used
                            </p>
                            <p className="text-slate-300">
                              {m.trace?.tools_used &&
                              m.trace.tools_used.length > 0
                                ? m.trace.tools_used.join(', ')
                                : 'None this turn'}
                            </p>
                          </div>
                          <div>
                            <p className="font-semibold text-slate-200 mb-1 text-xs">
                              Scratchpad
                            </p>
                            <pre className="whitespace-pre-wrap text-slate-300">
                              {m.trace?.scratchpad ||
                                'No scratchpad notes yet.'}
                            </pre>
                          </div>
                          <div>
                            <p className="font-semibold text-slate-200 mb-1 text-xs">
                              Planned tools
                            </p>
                            <pre className="whitespace-pre-wrap text-slate-300">
                              {m.trace?.planned_tools &&
                              m.trace.planned_tools.length > 0
                                ? JSON.stringify(
                                    m.trace.planned_tools,
                                    null,
                                    2,
                                  )
                                : 'No tools planned this turn.'}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>
        </aside>
      </main>
    </div>
  )
}

export default App
