import { useState } from 'react'
import {
  Check,
  Download,
  ExternalLink,
  FileText,
  LoaderCircle,
  Newspaper,
  Search,
  ShieldCheck
} from 'lucide-react'

export default function NewsletterPreview({ run, loading, submitting, onDecision }) {
  const [tab, setTab] = useState('preview')
  const [feedback, setFeedback] = useState('')
  const active = run?.status === 'running' || run?.status === 'queued'
  const waiting = run?.status === 'awaiting_approval'
  const completed = run?.status === 'completed'

  async function decide(action) {
    const success = await onDecision({ action, feedback })
    if (success) setFeedback('')
  }

  return (
    <section className="panel preview-panel">
      <header className="preview-header">
        <div className="section-title">
          <span className="number">02</span>
          <h2>Your next great issue</h2>
        </div>
        <span className={'status-badge ' + (run?.status || '')}>
          <span />
          {completed
            ? 'Ready to read'
            : waiting
              ? 'Your review'
              : active
                ? 'In progress'
                : run?.status === 'failed'
                  ? 'Stopped'
                  : run?.status === 'cancelled'
                    ? 'Cancelled'
                    : 'Draft preview'}
        </span>
      </header>
      <div className="preview-tabs" role="tablist" aria-label="Newsletter views">
        <button
          role="tab"
          aria-selected={tab === 'preview'}
          onClick={() => setTab('preview')}
          className={tab === 'preview' ? 'active' : ''}
        >
          <Newspaper size={15} />
          Newsletter
        </button>
        <button
          role="tab"
          aria-selected={tab === 'sources'}
          onClick={() => setTab('sources')}
          className={tab === 'sources' ? 'active' : ''}
        >
          <Search size={15} />
          Sources <small>{run?.sources.length || 0}</small>
        </button>
        <button
          role="tab"
          aria-selected={tab === 'activity'}
          onClick={() => setTab('activity')}
          className={tab === 'activity' ? 'active' : ''}
        >
          <ShieldCheck size={15} />
          Agent activity
        </button>
      </div>
      <div className="preview-body" role="tabpanel" aria-label={tab}>
        {loading ? (
          <div className="empty-preview">
            <LoaderCircle className="spin" />
            <h3>Opening your issue…</h3>
          </div>
        ) : tab === 'preview' ? (
          run?.html ? (
            <iframe
              title="Newsletter preview"
              srcDoc={run.html}
              sandbox="allow-popups allow-popups-to-escape-sandbox"
            />
          ) : (
            <div className="empty-preview">
              <div className="paper-art" aria-hidden="true">
                <div className="paper-label">THE AGENT EDIT</div>
                <div className="paper-line dark" />
                <div className="paper-line short" />
                <div className="paper-box" />
                <div className="paper-line" />
                <div className="paper-line" />
                <div className="paper-line short" />
                <span className="paper-seal">✳</span>
              </div>
              <span className="eyebrow">
                {active
                  ? 'YOUR AGENT IS ON IT'
                  : run?.status === 'failed'
                    ? 'THIS RUN NEEDS ATTENTION'
                    : 'A LITTLE DIRECTION. A GREAT READ.'}
              </span>
              <h3>
                {active
                  ? 'Good stories take a little digging.'
                  : run?.status === 'failed'
                    ? 'Let’s give it another try.'
                    : 'From a simple goal\nto a newsletter worth opening.'}
              </h3>
              <p>
                {active
                  ? 'Follow the research and review in Agent activity. Your newsletter will appear here after it passes review.'
                  : run?.status === 'failed'
                    ? run.error
                    : 'Tell your agent what matters. It will find the stories, connect the dots, and bring you a polished draft.'}
              </p>
              {!run && (
                <div className="empty-tags">
                  <span>
                    <Check size={12} />
                    Researched
                  </span>
                  <span>
                    <Check size={12} />
                    Source-linked
                  </span>
                  <span>
                    <Check size={12} />
                    Self-reviewed
                  </span>
                </div>
              )}
            </div>
          )
        ) : tab === 'sources' ? (
          <div className="sources-list">
            <div className="tab-intro">
              <h3>The reporting behind your issue</h3>
              <p>
                Sources dated within the seven days before this run. Evidence labels show
                what the agent could read.
              </p>
            </div>
            {!run?.sources.length && (
              <p className="muted">Sources will appear after research is complete.</p>
            )}
            {run?.sources.map((source, index) => (
              <article className="source-card" key={source.id}>
                <span className="source-number">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <div>
                  <div className="source-meta">
                    {source.publisher} · {source.published_at.slice(0, 10)}
                  </div>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title}
                    <ExternalLink size={13} />
                  </a>
                  <p>{source.excerpt}</p>
                  <span className="evidence-label">{source.evidence}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="activity-list">
            <div className="tab-intro">
              <h3>A look at the agent’s work</h3>
              <p>Tool calls, editorial checks, and your feedback, in order.</p>
            </div>
            {run?.plan && (
              <div className="plan-summary">
                <strong>{run.plan.topic}</strong>
                <p>For {run.plan.audience}</p>
              </div>
            )}
            {!run?.events.length && (
              <p className="muted">Start a newsletter to see your agent in action.</p>
            )}
            {run?.events.map((event, index) => (
              <div className="activity-item" key={index}>
                <span className="activity-dot" />
                <div>
                  <div className="activity-title">
                    <strong>{event.step}</strong>
                    <time>
                      {new Date(event.time).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </time>
                  </div>
                  <p>{event.message}</p>
                  {event.tool && <small className="tool-label">{event.tool}</small>}
                </div>
              </div>
            ))}
            {run?.reviews.map((review, index) => (
              <div
                className={'review-card ' + (review.passed ? 'passed' : '')}
                key={index}
              >
                <strong>
                  <ShieldCheck size={15} />
                  Review {index + 1} · {review.passed ? 'Passed' : 'Changes requested'}
                </strong>
                <p>{review.summary}</p>
                {review.issues.length > 0 && (
                  <ul>
                    {review.issues.map((issue, number) => (
                      <li key={number}>{issue}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      {waiting && (
        <div className="approval-panel">
          <h3>
            <ShieldCheck size={17} />
            Your draft is ready for review
          </h3>
          <p>
            Approve it to save the simulated delivery, or ask the agent to make changes.
          </p>
          <label htmlFor="feedback" className="field-label">
            Changes you would like
          </label>
          <textarea
            id="feedback"
            rows={2}
            maxLength={1500}
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            placeholder="For example: make the summaries shorter."
            disabled={submitting}
          />
          <div className="approval-actions">
            <button
              className="text-button"
              disabled={submitting}
              onClick={() => decide('cancel')}
            >
              Cancel draft
            </button>
            <button
              className="secondary-button"
              disabled={submitting || !feedback.trim()}
              onClick={() => decide('revise')}
            >
              Request changes
            </button>
            <button
              className="primary-button"
              disabled={submitting}
              onClick={() => decide('approve')}
            >
              <Check size={15} />
              Approve & save
            </button>
          </div>
        </div>
      )}
      <footer className="preview-footer">
        <span>
          <FileText size={14} />
          {completed
            ? 'Saved locally · delivery simulated'
            : waiting
              ? 'Nothing is sent without your approval'
              : 'HTML + Markdown output'}
        </span>
        {completed && (
          <div className="downloads">
            {run.files.map((file) => (
              <a key={file} href={'/api/runs/' + run.id + '/files/' + file} download>
                <Download size={13} />
                {file.endsWith('.html')
                  ? 'HTML'
                  : file.endsWith('.md')
                    ? 'Markdown'
                    : 'Receipt'}
              </a>
            ))}
          </div>
        )}
      </footer>
    </section>
  )
}
