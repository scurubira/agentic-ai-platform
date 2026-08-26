import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import {
  Activity, ArrowUpRight, Bot, Boxes, BrainCircuit, Check, ChevronRight,
  CircleAlert, Cpu, Database, Gauge, Menu, MessageSquareText, Network,
  PanelLeftClose, Play, RefreshCw, Send, ServerCog, Settings2, ShieldCheck, Sparkles,
  TerminalSquare, TestTube2, Trash2, Workflow, X, type LucideIcon,
} from 'lucide-react'
import './App.css'

type Section = 'overview' | 'playground' | 'models' | 'integrations' | 'governance'
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
type EvalDefinition = { id: string; name: string; description: string; expected_keywords: string[]; min_score: number }
type Guardrail = { id: string; name: string; rule_type: 'blocked_terms' | 'required_terms' | 'max_length'; stage: 'input' | 'output' | 'both'; action: 'block' | 'warn'; terms: string[]; max_length: number | null; enabled: boolean }
type GovernanceSnapshot = { evals: EvalDefinition[]; guardrails: Guardrail[] }

const emptyOverview: Overview = {
  environment: 'development', agent: { name: 'supervisor', routes: ['direct', 'rag', 'sql', 'tools'] }, models: [],
  services: { inference: { backend: 'indisponível' }, memory: { backend: 'indisponível' }, observability: { backend: 'langfuse', enabled: false, url: 'http://localhost:3000' }, mcp: { servers: [] } },
}
const nav: { id: Section; label: string; icon: LucideIcon }[] = [
  { id: 'overview', label: 'Visão geral', icon: Gauge }, { id: 'playground', label: 'Playground', icon: MessageSquareText },
  { id: 'models', label: 'Modelos', icon: BrainCircuit }, { id: 'integrations', label: 'Integrações', icon: Network },
  { id: 'governance', label: 'Governança', icon: ShieldCheck },
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
      <div className="brand"><span className="brandMark">B</span><div><b>BENS<span>TECH</span></b><small>Agentic Platform</small></div><button className="icon close" onClick={() => setMenu(false)} aria-label="Fechar menu"><PanelLeftClose /></button></div>
      <p className="navLabel">OPERAÇÕES</p>
      <nav>{nav.map(({ id, label, icon: Icon }) => <button className={section === id ? 'active' : ''} onClick={() => go(id)} key={id}><Icon /><span>{label}</span>{section === id && <ChevronRight className="arrow" />}</button>)}</nav>
      <div className="sideFoot"><div><i className={error ? 'bad' : ''} /><span><b>{overview.environment}</b><small>{error ? 'API desconectada' : 'API conectada'}</small></span></div><a href="http://localhost:8000/docs" target="_blank">Documentação <ArrowUpRight /></a></div>
    </aside>
    {menu && <button className="scrim" onClick={() => setMenu(false)} aria-label="Fechar menu" />}
    <main>
      <header><button className="icon menu" onClick={() => setMenu(true)} aria-label="Abrir menu"><Menu /></button><div className="crumb"><span>BensTech OS</span><ChevronRight /><b>{nav.find(item => item.id === section)?.label}</b></div><div className="headerRight"><small>{updated ? `SYNC ${updated.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}` : 'AGUARDANDO SYNC'}</small><button className="icon" onClick={() => void load()} disabled={loading} title="Atualizar"><RefreshCw className={loading ? 'spin' : ''} /></button><span className="avatar">BT</span></div></header>
      <div className="content">
        {error && <div className="alert"><CircleAlert /><span><b>API fora de alcance.</b> Inicie o backend em localhost:8000.</span><button onClick={() => void load()}>Tentar novamente</button></div>}
        {section === 'overview' && <OverviewPage data={overview} ready={ready} loading={loading} go={go} />}
        {section === 'playground' && <Playground models={overview.models} available={!error} />}
        {section === 'models' && <Models models={overview.models} />}
        {section === 'integrations' && <Integrations data={overview} ready={ready} />}
        {section === 'governance' && <Governance available={!error} />}
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
  const [model, setModel] = useState('fast'); const [session, setSession] = useState<string>(); const [input, setInput] = useState(''); const [sending, setSending] = useState(false); const [runError, setRunError] = useState<string>()
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', content: 'Olá. Sou o agente supervisor. Envie uma tarefa para testar o fluxo completo da plataforma.', meta: 'pronto para executar' }])
  useEffect(() => { const selected = models.find(item => item.default); if (selected) setModel(selected.alias) }, [models])
  async function send(event: FormEvent) {
    event.preventDefault(); const text = input.trim(); if (!text || sending) return
    setMessages(old => [...old, { role: 'user', content: text }]); setInput(''); setSending(true); setRunError(undefined)
    try { const response = await fetch('/api/v1/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, model, session_id: session }) }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || `Falha HTTP ${response.status}`); setSession(body.session_id); setMessages(old => [...old, { role: 'assistant', content: body.answer, meta: `${body.model} · ${body.latency_ms} ms` }]) }
    catch (reason) { const detail = reason instanceof Error ? reason.message : 'Falha ao acessar a API.'; setRunError(detail); setMessages(old => [...old, { role: 'assistant', content: detail, meta: 'erro de execução' }]) } finally { setSending(false) }
  }
  return <div className="page"><Heading eyebrow="AGENT LAB" title="Playground" text="Execute o supervisor e acompanhe modelo, sessão e latência em tempo real." /><div className="playGrid">
    <section className="chat"><div className="chatTop"><div><i className={available ? '' : 'bad'} /><b>Supervisor</b><small>{available ? 'node online' : 'node offline'}</small></div><button className="icon" onClick={() => { setMessages([]); setSession(undefined); setRunError(undefined) }} title="Limpar conversa" aria-label="Limpar conversa"><X /></button></div>{runError && <div className="runError"><CircleAlert />{runError}</div>}<div className="messages">{messages.map((message, index) => <div className={`message ${message.role}`} key={index}><span>{message.role === 'assistant' ? <Bot /> : 'BT'}</span><div><p>{message.content}</p>{message.meta && <small>{message.meta}</small>}</div></div>)}{sending && <div className="message"><span><Bot /></span><div className="typing">PROCESSANDO</div></div>}</div><form className="composer" onSubmit={send}><textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} maxLength={4000} placeholder="Digite uma instrução para o supervisor..." /><div><small>{input.length}/4000 · ENTER PARA EXECUTAR</small><button disabled={!input.trim() || sending || !available} title="Enviar mensagem" aria-label="Enviar mensagem"><Send /></button></div></form></section>
    <aside className="runConfig"><PanelHead eyebrow="EXECUÇÃO" title="Configuração" extra={<Settings2 />} /><label>Modelo<select value={model} onChange={e => setModel(e.target.value)}>{models.length ? models.map(item => <option value={item.alias} key={item.alias}>{item.alias} · {item.name}</option>) : <option>fast</option>}</select></label><div className="readout"><span>Agente</span><b>supervisor</b></div><div className="readout"><span>Sessão</span><b>{session ? `${session.slice(0, 10)}…` : 'nova sessão'}</b></div><div className="flow"><span>Fluxo atual</span><div><b>START</b><i /><b>SUPERVISOR</b><i /><b>LLM</b><i /><b>END</b></div></div></aside>
  </div></div>
}
function Models({ models }: { models: Model[] }) { return <div className="page"><Heading eyebrow="MODEL REGISTRY" title="Modelos" text="Inventário de aliases e provedores disponíveis para os agentes." action={<a className="secondary" href="http://localhost:8000/docs" target="_blank"><TerminalSquare /> Abrir API</a>} /><section className="panel table"><div className="tableRow tableHead"><span>Alias</span><span>Modelo físico</span><span>Provedor</span><span>Estado</span></div>{models.length ? models.map(item => <div className="tableRow" key={item.alias}><span><i><BrainCircuit /></i><b>{item.alias}</b></span><code>{item.name}</code><em>{item.provider}</em><strong className={item.default ? 'default' : ''}>{item.default ? 'Padrão' : 'Disponível'}</strong></div>) : <div className="empty"><CircleAlert /><b>Registro indisponível</b><small>Conecte a API para listar os modelos.</small></div>}</section><div className="note"><Sparkles /><div><b>Aliases desacoplam agentes dos modelos físicos.</b><p>Troque o backend no registro sem alterar a lógica do supervisor.</p></div></div></div> }
function Integrations({ data, ready }: { data: Overview; ready: Readiness | null }) {
  const items = [{ name: 'LiteLLM', type: 'Inference gateway', detail: data.services.inference.backend, icon: Cpu, active: ready?.checks.inference.ok }, { name: 'PostgreSQL', type: 'State & memory', detail: data.services.memory.backend, icon: Database, active: ready?.checks.database.ok }, { name: 'Langfuse', type: 'Observabilidade', detail: ready?.checks.observability?.ok ? 'Autenticado pela plataforma' : data.services.observability.enabled ? 'Falha de autenticação' : 'Configuração opcional', icon: Activity, active: ready?.checks.observability?.ok }, { name: 'MCP', type: 'Tool gateway', detail: `${data.services.mcp.servers.length} servidores registrados`, icon: Network, active: data.services.mcp.servers.length > 0 }]
  return <div className="page"><Heading eyebrow="ECOSSISTEMA" title="Integrações" text="Conectores de inferência, persistência, ferramentas e observabilidade." /><div className="integrationGrid">{items.map(({ icon: Icon, ...item }) => <article className="integration" key={item.name}><span><Icon /></span><div><small>{item.type}</small><h2>{item.name}</h2><p>{item.detail}</p></div><em className={item.active ? 'on' : ''}>{item.active ? 'Ativa' : 'Inativa'}</em></article>)}</div><ToolSection /></div>
}

function Governance({ available }: { available: boolean }) {
  const [tab, setTab] = useState<'evals' | 'guardrails'>('evals')
  const [data, setData] = useState<GovernanceSnapshot>({ evals: [], guardrails: [] })
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string }>()
  const [evalName, setEvalName] = useState(''); const [evalDescription, setEvalDescription] = useState(''); const [keywords, setKeywords] = useState(''); const [minScore, setMinScore] = useState('1')
  const [selectedEval, setSelectedEval] = useState(''); const [evalAnswer, setEvalAnswer] = useState(''); const [evalResult, setEvalResult] = useState<{ passed: boolean; correctness: number; groundedness: number }>()
  const [guardName, setGuardName] = useState(''); const [ruleType, setRuleType] = useState<Guardrail['rule_type']>('blocked_terms'); const [stage, setStage] = useState<Guardrail['stage']>('input'); const [action, setAction] = useState<Guardrail['action']>('block'); const [guardValue, setGuardValue] = useState('')
  const [testStage, setTestStage] = useState<'input' | 'output'>('input'); const [testText, setTestText] = useState(''); const [testResult, setTestResult] = useState<{ allowed: boolean; violations: { name: string; action: string; detail: string }[] }>()

  async function request(path: string, options?: RequestInit) {
    const response = await fetch(path, options); const body = response.status === 204 ? undefined : await response.json()
    if (!response.ok) throw new Error(body?.detail || `Falha HTTP ${response.status}`)
    return body
  }
  async function loadGovernance() {
    try { setData(await request('/api/v1/governance')); setNotice(undefined) }
    catch (reason) { setNotice({ kind: 'error', text: reason instanceof Error ? reason.message : 'Não foi possível carregar a governança.' }) }
  }
  useEffect(() => { if (available) void loadGovernance() }, [available])
  async function execute(task: () => Promise<void>, success: string) {
    setBusy(true); setNotice(undefined)
    try { await task(); setNotice({ kind: 'ok', text: success }) }
    catch (reason) { setNotice({ kind: 'error', text: reason instanceof Error ? reason.message : 'Operação não concluída.' }) }
    finally { setBusy(false) }
  }
  function createEval(event: FormEvent) {
    event.preventDefault(); void execute(async () => {
      await request('/api/v1/governance/evals', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: evalName, description: evalDescription, expected_keywords: keywords.split(',').map(item => item.trim()).filter(Boolean), min_score: Number(minScore) }) })
      setEvalName(''); setEvalDescription(''); setKeywords(''); await loadGovernance()
    }, 'Eval salvo e pronto para execução.')
  }
  function createGuardrail(event: FormEvent) {
    event.preventDefault(); void execute(async () => {
      await request('/api/v1/governance/guardrails', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: guardName, rule_type: ruleType, stage, action, terms: ruleType === 'max_length' ? [] : guardValue.split(',').map(item => item.trim()).filter(Boolean), max_length: ruleType === 'max_length' ? Number(guardValue) : null, enabled: true }) })
      setGuardName(''); setGuardValue(''); await loadGovernance()
    }, 'Guardrail ativado na plataforma.')
  }
  function runEval(event: FormEvent) {
    event.preventDefault(); if (!selectedEval) return
    void execute(async () => { setEvalResult(await request(`/api/v1/governance/evals/${selectedEval}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ answer: evalAnswer, latency_ms: 0 }) })) }, 'Execução concluída.')
  }
  function testGuardrails(event: FormEvent) {
    event.preventDefault(); void execute(async () => { setTestResult(await request('/api/v1/governance/guardrails/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: testText, stage: testStage }) })) }, 'Teste concluído.')
  }
  function remove(kind: 'evals' | 'guardrails', id: string) { void execute(async () => { await request(`/api/v1/governance/${kind}/${id}`, { method: 'DELETE' }); await loadGovernance() }, 'Definição removida.') }
  function toggle(item: Guardrail) { void execute(async () => { await request(`/api/v1/governance/guardrails/${item.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !item.enabled }) }); await loadGovernance() }, item.enabled ? 'Guardrail pausado.' : 'Guardrail ativado.') }

  return <div className="page governancePage">
    <Heading eyebrow="TRUST CENTER" title="Governança" text="Construa, execute e opere avaliações e políticas de proteção sem sair da plataforma." />
    <div className="governanceStats"><Metric icon={TestTube2} label="Evals configurados" value={String(data.evals.length).padStart(2, '0')} detail="critérios executáveis" tone="blue" /><Metric icon={ShieldCheck} label="Guardrails ativos" value={String(data.guardrails.filter(item => item.enabled).length).padStart(2, '0')} detail={`${data.guardrails.length} regras cadastradas`} tone="green" /></div>
    <div className="governanceTabs" role="tablist"><button className={tab === 'evals' ? 'active' : ''} onClick={() => setTab('evals')}><TestTube2 /> Evals</button><button className={tab === 'guardrails' ? 'active' : ''} onClick={() => setTab('guardrails')}><ShieldCheck /> Guardrails</button></div>
    {notice && <div className={`governanceNotice ${notice.kind}`}><span>{notice.kind === 'ok' ? <Check /> : <CircleAlert />}</span>{notice.text}</div>}
    {tab === 'evals' ? <div className="builderGrid">
      <form className="builder panel" onSubmit={createEval}><PanelHead eyebrow="NOVO CRITÉRIO" title="Construir eval" extra={<TestTube2 />} /><div className="formBody"><label>Nome<input value={evalName} onChange={event => setEvalName(event.target.value)} required placeholder="Ex.: Cobertura da resposta" /></label><label>Descrição<textarea value={evalDescription} onChange={event => setEvalDescription(event.target.value)} placeholder="Objetivo deste critério" /></label><label>Palavras esperadas<input value={keywords} onChange={event => setKeywords(event.target.value)} required placeholder="MCP, LangGraph, gateway" /><small>Separe múltiplos termos por vírgula.</small></label><label>Score mínimo<select value={minScore} onChange={event => setMinScore(event.target.value)}><option value="1">100%</option><option value="0.75">75%</option><option value="0.5">50%</option><option value="0.25">25%</option></select></label><button className="primary" disabled={busy}><Check /> Salvar eval</button></div></form>
      <form className="builder panel" onSubmit={runEval}><PanelHead eyebrow="LABORATÓRIO" title="Executar resposta" extra={<Play />} /><div className="formBody"><label>Eval<select value={selectedEval} onChange={event => { setSelectedEval(event.target.value); setEvalResult(undefined) }} required><option value="">Selecione um critério</option>{data.evals.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Resposta avaliada<textarea className="testArea" value={evalAnswer} onChange={event => setEvalAnswer(event.target.value)} required placeholder="Cole ou escreva a resposta do agente..." /></label><button className="secondary" disabled={busy || !selectedEval}><Play /> Executar eval</button>{evalResult && <Result allowed={evalResult.passed} title={evalResult.passed ? 'Critério aprovado' : 'Critério reprovado'} detail={`Correctness ${Math.round(evalResult.correctness * 100)}% · Groundedness ${Math.round(evalResult.groundedness * 100)}%`} />}</div></form>
    </div> : <div className="builderGrid">
      <form className="builder panel" onSubmit={createGuardrail}><PanelHead eyebrow="NOVA POLÍTICA" title="Construir guardrail" extra={<ShieldCheck />} /><div className="formBody splitFields"><label className="wide">Nome<input value={guardName} onChange={event => setGuardName(event.target.value)} required placeholder="Ex.: Bloquear dados sensíveis" /></label><label>Tipo<select value={ruleType} onChange={event => setRuleType(event.target.value as Guardrail['rule_type'])}><option value="blocked_terms">Bloquear termos</option><option value="required_terms">Exigir termos</option><option value="max_length">Limitar tamanho</option></select></label><label>Aplicar em<select value={stage} onChange={event => setStage(event.target.value as Guardrail['stage'])}><option value="input">Entrada</option><option value="output">Saída</option><option value="both">Entrada e saída</option></select></label><label>Ação<select value={action} onChange={event => setAction(event.target.value as Guardrail['action'])}><option value="block">Bloquear</option><option value="warn">Alertar</option></select></label><label>{ruleType === 'max_length' ? 'Máximo de caracteres' : 'Termos'}<input type={ruleType === 'max_length' ? 'number' : 'text'} min={ruleType === 'max_length' ? 1 : undefined} value={guardValue} onChange={event => setGuardValue(event.target.value)} required placeholder={ruleType === 'max_length' ? '4000' : 'senha, token, segredo'} /></label><button className="primary wide" disabled={busy}><ShieldCheck /> Criar e ativar</button></div></form>
      <form className="builder panel" onSubmit={testGuardrails}><PanelHead eyebrow="POLICY LAB" title="Testar políticas" extra={<Play />} /><div className="formBody"><label>Estágio<select value={testStage} onChange={event => setTestStage(event.target.value as 'input' | 'output')}><option value="input">Entrada do usuário</option><option value="output">Saída do agente</option></select></label><label>Conteúdo<textarea className="testArea" value={testText} onChange={event => setTestText(event.target.value)} required placeholder="Digite um conteúdo para testar contra regras ativas..." /></label><button className="secondary" disabled={busy}><Play /> Testar guardrails</button>{testResult && <Result allowed={testResult.allowed} title={testResult.allowed ? 'Conteúdo permitido' : 'Conteúdo bloqueado'} detail={testResult.violations.length ? testResult.violations.map(item => `${item.name}: ${item.detail}`).join(' · ') : 'Nenhuma violação encontrada.'} />}</div></form>
    </div>}
    <section className="definitionList"><div className="definitionTitle"><div><span className="eyebrow">INVENTÁRIO</span><h2>{tab === 'evals' ? 'Critérios registrados' : 'Políticas registradas'}</h2></div><span>{tab === 'evals' ? data.evals.length : data.guardrails.length} definições</span></div>{tab === 'evals' ? data.evals.map(item => <article className="definition" key={item.id}><span><TestTube2 /></span><div><b>{item.name}</b><p>{item.description || 'Sem descrição'}</p><small>{item.expected_keywords.join(' · ')} · mínimo {Math.round(item.min_score * 100)}%</small></div><button className="icon danger" onClick={() => remove('evals', item.id)} title="Excluir eval"><Trash2 /></button></article>) : data.guardrails.map(item => <article className={`definition ${item.enabled ? '' : 'disabled'}`} key={item.id}><span><ShieldCheck /></span><div><b>{item.name}</b><p>{item.rule_type === 'max_length' ? `Máximo ${item.max_length} caracteres` : item.terms.join(' · ')}</p><small>{item.stage} · {item.action}</small></div><button className={`statusToggle ${item.enabled ? 'on' : ''}`} onClick={() => toggle(item)}>{item.enabled ? 'Ativo' : 'Pausado'}</button><button className="icon danger" onClick={() => remove('guardrails', item.id)} title="Excluir guardrail"><Trash2 /></button></article>)}{(tab === 'evals' ? data.evals : data.guardrails).length === 0 && <div className="empty"><Boxes /><b>Nenhuma definição criada</b><small>Use o construtor acima para começar.</small></div>}</section>
  </div>
}

function Result({ allowed, title, detail }: { allowed: boolean; title: string; detail: string }) { return <div className={`policyResult ${allowed ? 'pass' : 'fail'}`}><span>{allowed ? <Check /> : <CircleAlert />}</span><div><b>{title}</b><p>{detail}</p></div></div> }