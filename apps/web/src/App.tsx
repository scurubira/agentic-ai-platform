import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import {
  Activity, ArrowUpRight, Bot, Boxes, BrainCircuit, Check, ChevronRight,
  CircleAlert, Cpu, Database, Gauge, Menu, MessageSquareText, Network,
  PanelLeftClose, RefreshCw, Send, ServerCog, Settings2, Sparkles,
  TerminalSquare, Workflow, X, type LucideIcon,
} from 'lucide-react'
import './App.css'

type Section = 'overview' | 'playground' | 'models' | 'integrations'
type Model = { alias: string; name: string; provider: string; default: boolean }
type Overview = {
  environment: string
  agent: { name: string; routes: string[] }
  models: Model[]
  services: {
    inference: { backend: string }
    memory: { backend: string }
    observability: { backend: string; enabled: boolean; url: string }
    mcp: { servers: string[] }
  }
}
type Readiness = {
  status: string
  checks: {
    inference: { ok: boolean; physical_model?: string }
    database: { ok: boolean; backend: string }
    observability: { ok: boolean; enabled: boolean; backend: string }
  }
}
type Message = { role: 'user' | 'assistant'; content: string; meta?: string }

const emptyOverview: Overview = {
  environment: 'development', agent: { name: 'supervisor', routes: ['direct', 'rag', 'sql', 'tools'] }, models: [],
  services: { inference: { backend: 'indisponível' }, memory: { backend: 'indisponível' }, observability: { backend: 'langfuse', enabled: false, url: 'http://localhost:3000' }, mcp: { servers: [] } },
}
const nav: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: 'overview', label: 'Visão geral', icon: Gauge }, { id: 'playground', label: 'Playground', icon: MessageSquareText },
  { id: 'models', label: 'Modelos', icon: BrainCircuit }, { id: 'integrations', label: 'Integrações', icon: Network },
]
const tools = [
  { name: 'API Docs', detail: 'FastAPI / Swagger', href: 'http://localhost:8000/docs', icon: TerminalSquare },
  { name: 'LangGraph Studio', detail: 'Inspeção de grafos', href: 'https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024', icon: Workflow },
  { name: 'LangGraph API', detail: 'Runtime local :2024', href: 'http://localhost:2024/docs', icon: Boxes },
  { name: 'Langfuse', detail: 'Traces e avaliações', href: 'http://127.0.0.1:3000/project/agentic-ai-platform/traces', icon: Activity },
]

export default function App() {
  const [section, setSection] = useState<Section>('overview')
  const [menu, setMenu] = useState(false)
  const [overview, setOverview] = useState(emptyOverview)
  const [ready, setReady] = useState<Readiness | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [updated, setUpdated] = useState<Date | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [inventory, health] = await Promise.all([fetch('/api/v1/platform/overview'), fetch('/ready')])
      if (!inventory.ok || !health.ok) throw new Error()
      setOverview(await inventory.json()); setReady(await health.json()); setError(false); setUpdated(new Date())
    } catch { setError(true); setReady(null) } finally { setLoading(false) }
  }
  useEffect(() => {
    let active = true
    Promise.all([fetch('/api/v1/platform/overview'), fetch('/ready')])
      .then(async ([inventory, health]) => {
        if (!inventory.ok || !health.ok) throw new Error()
        const [inventoryBody, healthBody] = await Promise.all([inventory.json(), health.json()])
        if (!active) return
        setOverview(inventoryBody); setReady(healthBody); setError(false); setUpdated(new Date())
      })
      .catch(() => { if (active) { setError(true); setReady(null) } })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  const go = (next: Section) => { setSection(next); setMenu(false) }

  return <div className="shell">
    <aside className={`sidebar ${menu ? 'open' : ''}`}>
      <div className="brand"><span className="brandMark"><Sparkles size={18} /></span><div><b>NEXUS</b><small>Agentic Control</small></div><button className="icon close" onClick={() => setMenu(false)} aria-label="Fechar menu"><PanelLeftClose /></button></div>
      <p className="navLabel">OPERAÇÕES</p>
      <nav>{nav.map(({ id, label, icon: Icon }) => <button className={section === id ? 'active' : ''} onClick={() => go(id)} key={id}><Icon /><span>{label}</span>{section === id && <ChevronRight className="arrow" />}</button>)}</nav>
      <div className="sideFoot"><div><i className={error ? 'bad' : ''} /><span><b>{overview.environment}</b><small>{error ? 'API desconectada' : 'API conectada'}</small></span></div><a href="http://localhost:8000/docs" target="_blank">Documentação <ArrowUpRight /></a></div>
    </aside>
    {menu && <button className="scrim" onClick={() => setMenu(false)} aria-label="Fechar menu" />}
    <main>
      <header><button className="icon menu" onClick={() => setMenu(true)} aria-label="Abrir menu"><Menu /></button><div className="crumb"><span>Agentic Platform</span><ChevronRight /><b>{nav.find(item => item.id === section)?.label}</b></div><div className="headerRight"><small>{updated ? `Atualizado ${updated.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}` : 'Sem sincronização'}</small><button className="icon" onClick={() => void load()} disabled={loading} title="Atualizar"><RefreshCw className={loading ? 'spin' : ''} /></button><span className="avatar">AS</span></div></header>
      <div className="content">
        {error && <div className="alert"><CircleAlert /><span><b>API fora de alcance.</b> Inicie o backend em localhost:8000.</span><button onClick={() => void load()}>Tentar novamente</button></div>}
        {section === 'overview' && <OverviewPage data={overview} ready={ready} loading={loading} go={go} />}
        {section === 'playground' && <Playground models={overview.models} available={!error} />}
        {section === 'models' && <Models models={overview.models} />}
        {section === 'integrations' && <Integrations data={overview} ready={ready} />}
      </div>
    </main>
  </div>
}

function Heading({ eyebrow, title, text, action }: { eyebrow: string; title: string; text: string; action?: ReactNode }) {
  return <div className="heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{text}</p></div>{action}</div>
}
function OverviewPage({ data, ready, loading, go }: { data: Overview; ready: Readiness | null; loading: boolean; go: (s: Section) => void }) {
  const operational = ready?.status === 'ready'
  const checks = ready ? Object.values(ready.checks).filter(item => item.ok).length : 0
  return <div className="page">
    <Heading eyebrow="COMMAND CENTER" title="Visão geral" text="Saúde, capacidade e rotas da sua plataforma em um só lugar." action={<button className="primary" onClick={() => go('playground')}><MessageSquareText /> Abrir playground</button>} />
    <section className="metrics">
      <Metric icon={Activity} label="Estado da plataforma" value={loading ? 'Verificando' : operational ? 'Operacional' : 'Degradado'} detail={operational ? 'Todos os checks passaram' : 'Verifique os serviços'} tone="green" />
      <Metric icon={BrainCircuit} label="Modelos registrados" value={String(data.models.length).padStart(2, '0')} detail={`${data.models.filter(m => m.default).length} padrão ativo`} tone="coral" />
      <Metric icon={Bot} label="Agente principal" value={data.agent.name} detail={`${data.agent.routes.length} rotas disponíveis`} tone="blue" />
      <Metric icon={ServerCog} label="Serviços prontos" value={`${checks}/${ready ? Object.keys(ready.checks).length : 2}`} detail={`Memória: ${data.services.memory.backend}`} tone="gray" />
    </section>
    <div className="overviewGrid">
      <section className="panel"><PanelHead eyebrow="SAÚDE DO SISTEMA" title="Serviços essenciais" extra={<span className={`health ${operational ? '' : 'warn'}`}><i />{operational ? 'Tudo operacional' : 'Atenção necessária'}</span>} /><div className="serviceList">
        <Service icon={Cpu} name="Inference Gateway" detail={data.services.inference.backend} ok={ready?.checks.inference.ok ?? false} />
        <Service icon={Database} name="Conversation Store" detail={data.services.memory.backend} ok={ready?.checks.database.ok ?? false} />
        <Service icon={Activity} name="Observabilidade" detail="langfuse" ok={ready?.checks.observability?.ok ?? false} optional />
        <Service icon={Network} name="MCP Gateway" detail={`${data.services.mcp.servers.length} servidores`} ok={data.services.mcp.servers.length > 0} optional />
      </div></section>
      <section className="panel"><PanelHead eyebrow="SUPERVISOR" title="Rotas de execução" extra={<Bot />} /><div className="routeMap"><div className="origin"><Sparkles />supervisor</div><i className="stem" /><div className="routes">{data.agent.routes.map((route, i) => <div className={i === 0 ? 'route activeRoute' : 'route'} key={route}><b>{route}</b><small>{i === 0 ? 'ativa' : 'preparada'}</small></div>)}</div></div></section>
    </div>
    <ToolSection />
  </div>
}
function Metric({ icon: Icon, label, value, detail, tone }: { icon: LucideIcon; label: string; value: string; detail: string; tone: string }) { return <article className="metric"><span className={`metricIcon ${tone}`}><Icon /></span><label>{label}</label><b>{value}</b><small>{detail}</small></article> }
function PanelHead({ eyebrow, title, extra }: { eyebrow: string; title: string; extra: ReactNode }) { return <div className="panelHead"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{extra}</div> }
function Service({ icon: Icon, name, detail, ok, optional }: { icon: LucideIcon; name: string; detail: string; ok: boolean; optional?: boolean }) { return <div className="service"><span className="serviceIcon"><Icon /></span><div><b>{name}</b><small>{detail}</small></div><em className={ok ? 'online' : ''}>{ok ? <><Check /> Online</> : optional ? 'Não configurado' : 'Indisponível'}</em></div> }
function ToolSection() { return <section className="tools"><div><span className="eyebrow">ACESSO RÁPIDO</span><h2>Ferramentas da plataforma</h2></div><div className="toolGrid">{tools.map(({ icon: Icon, ...tool }) => <a className="tool" href={tool.href} target="_blank" key={tool.name}><span><Icon /></span><div><b>{tool.name}</b><small>{tool.detail}</small></div><ArrowUpRight /></a>)}</div></section> }

function Playground({ models, available }: { models: Model[]; available: boolean }) {
  const [model, setModel] = useState('fast'); const [session, setSession] = useState<string>(); const [input, setInput] = useState(''); const [sending, setSending] = useState(false)
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', content: 'Olá. Sou o agente supervisor. Envie uma tarefa para testar o fluxo completo da plataforma.', meta: 'pronto para executar' }])
  useEffect(() => { const selected = models.find(item => item.default); if (selected) setModel(selected.alias) }, [models])
  async function send(event: FormEvent) {
    event.preventDefault(); const text = input.trim(); if (!text || sending) return
    setMessages(old => [...old, { role: 'user', content: text }]); setInput(''); setSending(true)
    try { const response = await fetch('/api/v1/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, model, session_id: session }) }); const body = await response.json(); if (!response.ok) throw new Error(body.detail); setSession(body.session_id); setMessages(old => [...old, { role: 'assistant', content: body.answer, meta: `${body.model} · ${body.latency_ms} ms` }]) }
    catch (reason) { setMessages(old => [...old, { role: 'assistant', content: reason instanceof Error ? reason.message : 'Falha ao acessar a API.', meta: 'erro de execução' }]) } finally { setSending(false) }
  }
  return <div className="page"><Heading eyebrow="AGENT LAB" title="Playground" text="Execute o supervisor e acompanhe modelo, sessão e latência em tempo real." /><div className="playGrid">
    <section className="chat"><div className="chatTop"><div><i className={available ? '' : 'bad'} /><b>Supervisor</b><small>{available ? 'conectado' : 'offline'}</small></div><button className="icon" onClick={() => { setMessages([]); setSession(undefined) }} title="Limpar conversa" aria-label="Limpar conversa"><X /></button></div><div className="messages">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}><span>{message.role === 'assistant' ? <Bot /> : 'AS'}</span><div><p>{message.content}</p>{message.meta && <small>{message.meta}</small>}</div></div>)}{sending && <div className="message"><span><Bot /></span><div className="typing">•••</div></div>}</div><form className="composer" onSubmit={send}><textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} maxLength={4000} placeholder="Envie uma tarefa para o supervisor..." /><div><small>{input.length}/4000</small><button disabled={!input.trim() || sending || !available} title="Enviar mensagem" aria-label="Enviar mensagem"><Send /></button></div></form></section>
    <aside className="runConfig"><PanelHead eyebrow="EXECUÇÃO" title="Configuração" extra={<Settings2 />} /><label>Modelo<select value={model} onChange={e => setModel(e.target.value)}>{models.length ? models.map(item => <option value={item.alias} key={item.alias}>{item.alias} · {item.name}</option>) : <option>fast</option>}</select></label><div className="readout"><span>Agente</span><b>supervisor</b></div><div className="readout"><span>Sessão</span><b>{session ? `${session.slice(0, 10)}…` : 'nova sessão'}</b></div><div className="flow"><span>Fluxo atual</span><div><b>START</b><i /><b>SUPERVISOR</b><i /><b>LLM</b><i /><b>END</b></div></div></aside>
  </div></div>
}
function Models({ models }: { models: Model[] }) { return <div className="page"><Heading eyebrow="MODEL REGISTRY" title="Modelos" text="Inventário de aliases e provedores disponíveis para os agentes." action={<a className="secondary" href="http://localhost:8000/docs" target="_blank"><TerminalSquare /> Abrir API</a>} /><section className="panel table"><div className="tableRow tableHead"><span>Alias</span><span>Modelo físico</span><span>Provedor</span><span>Estado</span></div>{models.length ? models.map(item => <div className="tableRow" key={item.alias}><span><i><BrainCircuit /></i><b>{item.alias}</b></span><code>{item.name}</code><em>{item.provider}</em><strong className={item.default ? 'default' : ''}>{item.default ? 'Padrão' : 'Disponível'}</strong></div>) : <div className="empty"><CircleAlert /><b>Registro indisponível</b><small>Conecte a API para listar os modelos.</small></div>}</section><div className="note"><Sparkles /><div><b>Aliases desacoplam agentes dos modelos físicos.</b><p>Troque o backend no registro sem alterar a lógica do supervisor.</p></div></div></div> }
function Integrations({ data, ready }: { data: Overview; ready: Readiness | null }) {
  const items = [{ name: 'LiteLLM', type: 'Inference gateway', detail: data.services.inference.backend, icon: Cpu, active: ready?.checks.inference.ok }, { name: 'PostgreSQL', type: 'State & memory', detail: data.services.memory.backend, icon: Database, active: ready?.checks.database.ok }, { name: 'Langfuse', type: 'Observabilidade', detail: ready?.checks.observability?.ok ? 'Autenticado pela plataforma' : data.services.observability.enabled ? 'Falha de autenticação' : 'Configuração opcional', icon: Activity, active: ready?.checks.observability?.ok }, { name: 'MCP', type: 'Tool gateway', detail: `${data.services.mcp.servers.length} servidores registrados`, icon: Network, active: data.services.mcp.servers.length > 0 }]
  return <div className="page"><Heading eyebrow="ECOSSISTEMA" title="Integrações" text="Conectores de inferência, persistência, ferramentas e observabilidade." /><div className="integrationGrid">{items.map(({ icon: Icon, ...item }) => <article className="integration" key={item.name}><span><Icon /></span><div><small>{item.type}</small><h2>{item.name}</h2><p>{item.detail}</p></div><em className={item.active ? 'on' : ''}>{item.active ? 'Ativa' : 'Inativa'}</em></article>)}</div><ToolSection /></div>
}