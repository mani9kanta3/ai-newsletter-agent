# The Agent Edit

A newsletter agent built for the AI Developer Assignment. Give it a plain English goal and it researches recent news, writes a newsletter, critiques the draft, revises it when needed, and saves a simulated delivery.

## Run the project

The project uses Python 3.12 and Node.js 20.19 or newer.

1. Open PowerShell in this folder.
2. Run `powershell -ExecutionPolicy Bypass -File setup.ps1` for first-time setup.
3. Add your Gemini API key to `.env`:

```env
GOOGLE_API_KEY=your_key_here
```

4. Run `powershell -ExecutionPolicy Bypass -File start.ps1`, or double-click `start.bat`.
5. Open http://127.0.0.1:8000 in your browser.

The API key stays on the backend. Never commit `.env` or share it. `.env.example` is safe to share. The default model is `gemini-3.1-flash-lite`. An optional `GEMINI_MODEL` setting changes the model. Gemini 3 models use low thinking level; Gemini 2.5 models use a 1024-token thinking budget. The model must support structured JSON output and be available to your account.

If Google reports the model as overloaded (HTTP 5xx), each call retries after 2, 4 and 8 seconds, then switches to `GEMINI_FALLBACK_MODEL` (default `gemini-2.5-flash`). Quota (429) and key errors stop immediately, because retrying cannot fix them.

## Use the app

Enter a goal such as:

> Create a weekly newsletter on latest AI agent news and send it to our subscribers.

Choose a mode:

- **Fully Autonomous:** the agent researches, writes, reviews, and saves the newsletter.
- **Human-in-the-Loop:** the agent pauses after its editorial review. Approve the draft, request changes with feedback, or cancel it. Each revised draft goes through another AI review before returning to you.

The Sources tab shows publishers, dates, links, and whether the agent read article text or used a search excerpt. Agent activity shows tool calls, progress messages, review verdicts, and feedback. These are concise execution records, not the model's private reasoning.

Completed issues provide HTML, Markdown, and receipt downloads. Recent issues remain available after restarting the server. Approval pauses are saved in SQLite and also survive restarts.

## Agent flow

```text
Goal → Plan → Search and read sources → Write → Review
                                         ↑       |
                                         └─ Revise if needed
                                                 |
                                           Format preview
                                                 |
                                   Autonomous or human approval
                                                 |
                                      Save simulated delivery
```

The LangGraph graph calls a Gemini planner, public news search, source selector, article reader, summarizer, critic, HTML generator, and file delivery tool. These are plain Python functions to keep the code easy to follow.

The planner creates search queries from the goal. The research step selects 5–7 articles from the preceding seven days, removes repeated titles and URLs, checks dates, and reads available article text. Thin unreadable sources are skipped and replaced with the next unused search results, so a few paywalled picks do not stop the run. The writing step uses only gathered evidence. The critic checks the result and can send it back for up to two automatic revisions. A draft that still fails review stops without saving delivery files.

## One-function usage

From this project's Python environment:

```python
from backend.agent import run_newsletter_agent

result = run_newsletter_agent(
    'Create a weekly newsletter on latest AI agent news and send it to our subscribers.'
)
print(result['status'])
```

Or run from PowerShell:

```powershell
.\.venv\Scripts\python.exe run_agent.py
```

The function runs synchronously until completion or failure. For human mode, pass `mode='human'`. It returns `awaiting_approval`; call `resume_newsletter_agent(run_id, {'action': 'approve'})` to continue, or use the UI.

## Project files

```text
backend/
  main.py          FastAPI routes and background execution
  agent.py         LangGraph steps and approval flow
  ai.py            Gemini requests and structured responses
  tools.py         News search, article reading, and formatting
  schemas.py       Input and AI response validation
  storage.py       Run history and progress records
  config.py        Settings and project paths
frontend/
  src/
    App.jsx                 Main page and saved issues
    GoalForm.jsx            Goal and mode inputs
    NewsletterPreview.jsx   Preview, sources, activity, and approval
    Progress.jsx            Workflow steps
    store.js                Redux state and API actions
    api.js                  Backend requests
    styles.css              Responsive page styles
tests/
  test_agent.py     Workflow, approval, source, and API tests
  test_ai.py        Invalid responses and provider error handling
output/
  checkpoints.sqlite
  <run-id>/
    run.json
    newsletter.html
    newsletter.md
    email.json
```

`run.json` and checkpoints store drafts and activity. The three delivery files are created only after a passing review and, in human mode, approval. The receipt records the subject and `sent: false`. No subscriber email addresses or email provider account are required.

## Development

Run the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, run the frontend:

```powershell
cd frontend
npm.cmd run dev
```

Vite proxies `/api` to the backend. After changing React code, run `npm.cmd run build` in `frontend` and restart the backend to serve the updated production build.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The 18 tests use controlled news and AI responses, so they do not consume API quota. They exercise the real LangGraph graph and SQLite checkpoints, including autonomous revision, human revision and approval, cancellation, rejected drafts, source filtering, HTML escaping, protected downloads, invalid AI responses, provider errors, busy-model backoff with fallback, and replacing unreadable sources.

## Limits

- Gemini and news search need an internet connection. Free API access has rate limits; a key alone does not guarantee remaining quota.
- Public news search and publishers can block requests. Excerpt-based summaries are labeled. If fewer than five suitable sources can be read, the run stops rather than inventing stories.
- AI review reduces errors but does not guarantee factual accuracy. Source links are included for checking.
- The seven-day window uses source publication timestamps, which are not independently verified. An article may discuss an older event; the agent should not present that event as newly occurring.
- On the free Render deployment, saved issues and approval pauses are cleared whenever the service redeploys or restarts, because the disk is not persistent. Locally they persist.
- This is a local, single-user assignment app. Run one backend process. It processes one newsletter at a time and has no login or production deployment configuration.
- A server stop during active generation marks that run interrupted at next startup. Start a new run. Drafts already waiting for human approval can still be resumed.
- Weekly describes the research window. The app does not schedule recurring runs or send real emails.

## API

- `GET /api/health`: configuration status, without revealing the key.
- `POST /api/runs`: start a newsletter with `goal` and `mode`.
- `GET /api/runs`: recent run history.
- `GET /api/runs/{id}`: progress and result.
- `POST /api/runs/{id}/decision`: `approve`, `revise` with `feedback`, or `cancel`.
- `GET /api/runs/{id}/files/{filename}`: download a completed issue file.

Interactive API documentation is available at http://127.0.0.1:8000/docs.
