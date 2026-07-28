// ---- Tabs ----
const tabBar = document.getElementById('tab-bar')
tabBar.addEventListener('click', (e) => {
  const btn = e.target.closest('.tab-btn')
  if (!btn) return
  document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'))
  document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'))
  btn.classList.add('active')
  document.getElementById(`panel-${btn.dataset.tab}`).classList.add('active')

  if (btn.dataset.tab === 'docs') loadDocs()
  if (btn.dataset.tab === 'trace') loadTrace()
})

// ---- Chat (tab: Agente Orquestador) ----
const chatLog = document.getElementById('chat-log')
const chatForm = document.getElementById('chat-form')
const chatInput = document.getElementById('chat-input')
const submitBtn = chatForm.querySelector('.chat-submit')
const exampleList = document.getElementById('example-list')

const sessionId = crypto.randomUUID()

const AGENT_LABELS = {
  consultar_ventas_mad_market: 'sql_agent',
  analizar_accion: 'stock_agent',
  buscar_en_documentos: 'rag',
}

function appendMessage(role, text, { agentBadge, fiscalIssues } = {}) {
  const el = document.createElement('div')
  el.className = `chat-msg ${role}`

  if (agentBadge) {
    const badge = document.createElement('span')
    badge.className = 'agent-badge'
    badge.textContent = agentBadge
    el.appendChild(badge)
    el.appendChild(document.createElement('br'))
  }

  el.appendChild(document.createTextNode(text))

  if (fiscalIssues && fiscalIssues.length > 0) {
    const warn = document.createElement('span')
    warn.className = 'fiscal-warning'
    warn.textContent = `⚠ Fiscalizador: ${fiscalIssues.join('; ')}`
    el.appendChild(warn)
  }

  chatLog.appendChild(el)
  chatLog.scrollTop = chatLog.scrollHeight
  return el
}

async function sendMessage(message) {
  appendMessage('user', message)
  submitBtn.disabled = true
  const thinking = appendMessage('assistant', 'Pensando...')

  try {
    const res = await fetch('/api/agent/invoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const data = await res.json()
    thinking.remove()

    if (data.blocked) {
      appendMessage('error', data.reply)
      return
    }

    const badge = data.tool_calls?.length
      ? data.tool_calls.map((t) => AGENT_LABELS[t] || t).join(' + ')
      : null

    appendMessage('assistant', data.reply, { agentBadge: badge, fiscalIssues: data.fiscal_issues })
  } catch (err) {
    thinking.remove()
    appendMessage('error', `No pude contactar al orquestador: ${err.message}`)
  } finally {
    submitBtn.disabled = false
  }
}

chatForm.addEventListener('submit', (e) => {
  e.preventDefault()
  const value = chatInput.value.trim()
  if (!value) return
  chatInput.value = ''
  sendMessage(value)
})

exampleList.addEventListener('click', (e) => {
  const li = e.target.closest('li[data-q]')
  if (!li) return
  chatInput.value = li.dataset.q
  chatInput.focus()
})

appendMessage('assistant', 'Hola, soy el orquestador de SOULDREAM Agent. Pregúntame por mad_market, acciones bursátiles, o adopción de IA en pymes chilenas.')

// ---- Agentes (tab: Agentes) ----
const AGENTS_STATIC = [
  {
    name: 'sql_agent',
    tool: 'consultar_ventas_mad_market',
    desc: 'Text-to-SQL vía MCP sobre SQLite (solo lectura). Clientes, productos, pedidos de mad_market.',
  },
  {
    name: 'stock_agent',
    tool: 'analizar_accion',
    desc: 'Investigación bursátil: Yahoo Finance + análisis generado por LLM. No es asesoría financiera.',
  },
  {
    name: 'rag (búsqueda semántica)',
    tool: 'buscar_en_documentos',
    desc: 'KNN sobre Chroma, corpus real de adopción de IA en pymes chilenas (CENIA, Defontana, CORFO...).',
  },
]

function renderAgentsGrid() {
  const grid = document.getElementById('agents-grid')
  grid.innerHTML = AGENTS_STATIC.map(
    (a) => `<div class="agent-card">
      <span class="agent-name">${a.name}</span>
      <span class="agent-tool">${a.tool}()</span>
      <span class="agent-desc">${a.desc}</span>
      <div class="agent-status"><span class="agent-dot"></span><span>Disponible</span></div>
    </div>`
  ).join('')
}
renderAgentsGrid()

// ---- Documentos (tab: Documentos) ----
async function loadDocs() {
  const list = document.getElementById('docs-list')
  try {
    const res = await fetch('/api/docs')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data.documents?.length) {
      list.innerHTML = '<p class="body-muted">No hay documentos indexados todavía.</p>'
      return
    }
    list.innerHTML = data.documents
      .map((d) => `<div class="doc-card"><span class="doc-name">${d.fuente}</span><span class="doc-count">${d.chunks} chunk(s)</span></div>`)
      .join('')
  } catch (err) {
    list.innerHTML = `<p class="body-muted">No se pudo cargar el listado de documentos (${err.message}).</p>`
  }
}

// ---- Trazabilidad (tab: Trazabilidad) ----
async function loadTrace() {
  const tbody = document.getElementById('trace-tbody')
  tbody.innerHTML = '<tr><td colspan="5" class="body-muted">Cargando…</td></tr>'
  try {
    const res = await fetch('/api/trace?limit=30')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data.interactions?.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="body-muted">Sin interacciones registradas todavía.</td></tr>'
      return
    }
    tbody.innerHTML = data.interactions
      .map(
        (i) => `<tr>
          <td>${new Date(i.timestamp).toLocaleTimeString('es-CL')}</td>
          <td>${i.query.slice(0, 60)}${i.query.length > 60 ? '…' : ''}</td>
          <td>${i.agent || '—'}</td>
          <td>${Math.round(i.latency_ms)} ms</td>
          <td>${i.fiscal_issues ? '⚠' : '✓'}</td>
        </tr>`
      )
      .join('')
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="body-muted">No se pudo cargar la trazabilidad (${err.message}).</td></tr>`
  }
}

document.getElementById('trace-refresh').addEventListener('click', loadTrace)
