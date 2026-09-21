import { ArrowUpRight, Bot, Check, LoaderCircle, UserRound } from 'lucide-react'

export const sampleGoal =
  'Create a weekly newsletter on latest AI agent news and send it to our subscribers.'

export default function GoalForm({
  goal,
  setGoal,
  mode,
  setMode,
  onSubmit,
  disabled,
  submitting
}) {
  return (
    <section className="panel goal-panel">
      <div className="section-title">
        <span className="number">01</span>
        <h2>Give your agent a goal</h2>
      </div>
      <p className="section-description">
        You set the direction. Your agent does the research and writing.
      </p>
      <form onSubmit={onSubmit}>
        <label className="field-label" htmlFor="goal">
          What should this issue cover?
        </label>
        <textarea
          id="goal"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          maxLength={2000}
          minLength={10}
          required
          rows={5}
          disabled={disabled}
          placeholder="Create a weekly newsletter about…"
        />
        <div className="input-help">
          <span>Plain English is all you need</span>
          <span>{goal.length}/2000</span>
        </div>
        <button
          type="button"
          className="sample-button"
          disabled={disabled}
          onClick={() => setGoal(sampleGoal)}
        >
          <span>↗</span> Try the AI agent news prompt
        </button>
        <fieldset disabled={disabled}>
          <legend className="field-label">Choose how your agent works</legend>
          <label className={'mode-option ' + (mode === 'autonomous' ? 'selected' : '')}>
            <input
              type="radio"
              name="mode"
              value="autonomous"
              checked={mode === 'autonomous'}
              onChange={() => setMode('autonomous')}
            />
            <Bot size={20} />
            <span>
              <strong>Fully Autonomous</strong>
              <small>Research, review, and save in one go.</small>
            </span>
            <span className="radio-mark">
              {mode === 'autonomous' && <Check size={12} />}
            </span>
          </label>
          <label className={'mode-option ' + (mode === 'human' ? 'selected' : '')}>
            <input
              type="radio"
              name="mode"
              value="human"
              checked={mode === 'human'}
              onChange={() => setMode('human')}
            />
            <UserRound size={20} />
            <span>
              <strong>Human-in-the-Loop</strong>
              <small>Review the draft before it is saved.</small>
            </span>
            <span className="radio-mark">{mode === 'human' && <Check size={12} />}</span>
          </label>
        </fieldset>
        <div className="run-facts">
          <span>Past 7 days</span>
          <i /> <span>5–7 stories</span>
          <i />
          <span>Source links</span>
        </div>
        <button
          className="primary-button generate-button"
          disabled={disabled || goal.trim().length < 10}
        >
          {submitting ? (
            <LoaderCircle size={18} className="spin" />
          ) : (
            <span className="button-spark">✳</span>
          )}
          {submitting ? 'Starting your agent…' : 'Create newsletter'}
          <ArrowUpRight size={18} />
        </button>
        <p className="form-footnote">Delivery is simulated. No emails are sent.</p>
      </form>
    </section>
  )
}
