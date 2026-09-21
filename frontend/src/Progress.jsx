import { Check, Circle, LoaderCircle } from 'lucide-react'

const steps = [
  ['Plan', ['Planning']],
  ['Research', ['Researching', 'Reading sources']],
  ['Write', ['Writing', 'Revising']],
  ['Review', ['Reviewing', 'Formatting', 'Awaiting approval', 'Human review']],
  ['Output', ['Saving', 'Completed']]
]

export default function Progress({ run }) {
  let current = -1
  if (run) {
    for (const event of run.events) {
      const index = steps.findIndex((step) => step[1].includes(event.step))
      if (index >= 0) current = index
    }
  }
  const active = run?.status === 'running' || run?.status === 'queued'

  return (
    <section className="workflow" aria-label="Agent progress">
      <div className="workflow-heading">
        <span className="eyebrow">THE WORKFLOW</span>
        <span aria-live="polite">
          {run ? run.step : 'One goal. Five thoughtful steps.'}
        </span>
      </div>
      <div className="workflow-steps">
        {steps.map(([name], index) => {
          const done = index < current || run?.status === 'completed'
          const running = active && index === current
          return (
            <div
              className={
                'workflow-step ' + (done ? 'done' : index === current ? 'current' : '')
              }
              key={name}
            >
              <span>
                {done ? (
                  <Check size={15} />
                ) : running ? (
                  <LoaderCircle size={15} className="spin" />
                ) : (
                  <Circle size={11} />
                )}
              </span>
              <strong>{name}</strong>
            </div>
          )
        })}
      </div>
    </section>
  )
}
