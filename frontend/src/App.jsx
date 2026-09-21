import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  ArrowUpRight,
  BookOpen,
  CircleHelp,
  Feather,
  History,
  Plus,
  Radio,
  X
} from 'lucide-react'
import { apiRequest } from './api'
import GoalForm, { sampleGoal } from './GoalForm'
import NewsletterPreview from './NewsletterPreview'
import Progress from './Progress'
import {
  loadRuns,
  newNewsletter,
  openRun,
  refreshRun,
  sendDecision,
  startRun
} from './store'

export default function App() {
  const dispatch = useDispatch()
  const { current, runs, loading, submitting, error } = useSelector(
    (state) => state.newsletters
  )
  const [goal, setGoal] = useState(sampleGoal)
  const [mode, setMode] = useState('autonomous')
  const [health, setHealth] = useState(null)
  const [help, setHelp] = useState(false)
  const running = current?.status === 'running' || current?.status === 'queued'
  const anyRunning =
    running || runs.some((run) => ['running', 'queued'].includes(run.status))
  const completed = runs.filter((run) => run.status === 'completed').length

  useEffect(() => {
    dispatch(loadRuns())
    const saved = localStorage.getItem('newsletter-run')
    if (saved) dispatch(openRun(saved))
    apiRequest('/health')
      .then(setHealth)
      .catch(() => setHealth({ configured: false }))
  }, [dispatch])

  useEffect(() => {
    if (!current) return
    localStorage.setItem('newsletter-run', current.id)
    setGoal(current.goal)
    setMode(current.mode)
    dispatch(loadRuns())
  }, [current?.id, current?.status, dispatch])

  useEffect(() => {
    if (!anyRunning) return
    let stopped = false
    let timer
    async function poll() {
      if (current?.id) await dispatch(refreshRun(current.id))
      await dispatch(loadRuns())
      if (!stopped) timer = setTimeout(poll, 1800)
    }
    timer = setTimeout(poll, 1800)
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [current?.id, anyRunning, dispatch])

  function startNew() {
    dispatch(newNewsletter())
    localStorage.removeItem('newsletter-run')
    setGoal(sampleGoal)
    setMode('autonomous')
  }

  async function submit(event) {
    event.preventDefault()
    if (anyRunning || submitting) return
    dispatch(startRun({ goal: goal.trim(), mode }))
  }

  async function decide(data) {
    try {
      await dispatch(sendDecision(data)).unwrap()
      return true
    } catch {
      return false
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="The Agent Edit home">
          <span className="brand-mark">
            <Feather size={23} />
          </span>
          <span>
            The Agent Edit<span className="brand-subtitle">NEWSLETTER STUDIO</span>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">W</span>
          <div>
            <strong>My workspace</strong>
            <small>A little more signal.</small>
          </div>
          <span className="workspace-dot" />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <button
          className={'nav-item ' + (!current ? 'active' : '')}
          onClick={startNew}
          disabled={submitting}
        >
          <BookOpen size={18} />
          Newsletter studio
          <ArrowUpRight size={14} />
        </button>
        <div className="history-heading">
          <span className="nav-label">RECENT ISSUES</span>
          <button
            onClick={() => dispatch(loadRuns())}
            title="Refresh recent issues"
            aria-label="Refresh recent issues"
          >
            <History size={14} />
          </button>
        </div>
        <div className="history-list">
          {!runs.length && (
            <div className="history-empty">
              <History size={20} />
              <p>Your story starts here.</p>
              <small>Created issues will live in this space.</small>
            </div>
          )}
          {runs.slice(0, 12).map((run) => (
            <button
              key={run.id}
              className={'history-item ' + (current?.id === run.id ? 'selected' : '')}
              onClick={() => dispatch(openRun(run.id))}
              disabled={submitting}
            >
              <span className={'history-dot ' + run.status} />
              <span>
                <strong>{run.goal}</strong>
                <small>
                  {new Date(run.created_at).toLocaleDateString([], {
                    month: 'short',
                    day: 'numeric'
                  })}{' '}
                  · {run.status.replaceAll('_', ' ')}
                </small>
              </span>
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span>✳</span>
            <h3>
              Less noise.
              <br />
              More worth reading.
            </h3>
            <p>Your agent researches, writes, and checks every issue.</p>
          </div>
          <button className="help-button" onClick={() => setHelp(true)}>
            <CircleHelp size={16} />
            How it works
            <ArrowUpRight size={14} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>Newsletter studio</strong>
          </div>
          <span className={'connection ' + (health?.configured ? 'connected' : '')}>
            <span />
            {health === null
              ? 'Connecting…'
              : health.configured
                ? 'Gemini configured'
                : 'Check backend / API key'}
          </span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span />
                YOUR AUTONOMOUS EDITOR
              </div>
              <h1>Good stories. On autopilot.</h1>
              <p>Turn what you’re curious about into a newsletter worth sharing.</p>
            </div>
            <button className="secondary-button" onClick={startNew} disabled={submitting}>
              <Plus size={16} />
              New issue
            </button>
          </div>
          <div className="overview">
            <span>
              <Radio size={15} />
              <strong>Live news research</strong>
            </span>
            <span>
              <span className="mini-spark">✳</span>AI writing + editorial review
            </span>
            <span>
              <BookOpen size={15} />
              <strong>{completed}</strong> {completed === 1 ? 'issue' : 'issues'} created
            </span>
          </div>
          {(error || current?.error) && (
            <div className="error-message" role="alert">
              {error || current.error}
            </div>
          )}
          <div className="studio-layout">
            <div className="left-column">
              <GoalForm
                goal={goal}
                setGoal={setGoal}
                mode={mode}
                setMode={setMode}
                onSubmit={submit}
                disabled={anyRunning || submitting || loading || !health?.configured}
                submitting={submitting && !current}
              />
              <Progress run={current} />
              <div className="editor-note">
                <span>✳</span>
                <p>
                  <strong>A second pair of eyes, built in.</strong>Your agent critiques
                  its own draft and revises it before you see the final issue.
                </p>
              </div>
            </div>
            <NewsletterPreview
              key={current?.id || 'new'}
              run={current}
              loading={loading}
              submitting={submitting}
              onDecision={decide}
            />
          </div>
          <footer className="page-footer">
            <span>Made for curious minds.</span>
            <span>
              Powered by Gemini & LangGraph<span className="footer-dot">·</span>Local
              workspace
            </span>
          </footer>
        </main>
      </div>
      {help && (
        <div className="modal-backdrop" onClick={() => setHelp(false)}>
          <section
            className="help-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="help-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              aria-label="Close help"
              onClick={() => setHelp(false)}
              autoFocus
            >
              <X size={19} />
            </button>
            <span className="eyebrow">MEET YOUR EDITOR</span>
            <h2 id="help-title">One goal, a complete issue.</h2>
            <ol>
              <li>
                <strong>Plan.</strong> The agent turns your goal into news searches.
              </li>
              <li>
                <strong>Research.</strong> It chooses 5–7 recent stories and reads
                available article text.
              </li>
              <li>
                <strong>Write.</strong> Gemini creates summaries with source links.
              </li>
              <li>
                <strong>Review.</strong> The agent checks the draft and revises it when
                needed.
              </li>
              <li>
                <strong>Output.</strong> Save HTML, Markdown, and a simulated email
                receipt.
              </li>
            </ol>
            <p>
              Human-in-the-Loop mode pauses before saving. You can approve, request
              changes, or cancel. This app runs when you start an issue; it does not
              schedule weekly runs or send real emails.
            </p>
            <button className="primary-button" onClick={() => setHelp(false)}>
              Got it
              <CheckIcon />
            </button>
          </section>
        </div>
      )}
    </div>
  )
}

function CheckIcon() {
  return <span aria-hidden="true">✓</span>
}
