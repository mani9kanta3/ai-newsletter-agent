from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.agent import resume_newsletter_agent, run_newsletter_agent
from backend.config import API_KEY, MODEL, ROOT
from backend.schemas import DecisionInput, GoalInput
from backend.storage import get_run, list_runs, lock, new_run, run_folder, update_run

executor = ThreadPoolExecutor(max_workers=1)


@asynccontextmanager
async def lifespan(app):
    for run in list_runs():
        if run['status'] in ('running', 'queued'):
            update_run(run['id'], status='failed', step='Interrupted', error='The server stopped during this run. Please start a new run.')
    yield
    executor.shutdown(wait=True)


app = FastAPI(title='Newsletter Agent', lifespan=lifespan)


def find_run(run_id):
    try:
        return get_run(str(run_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Newsletter not found') from None


def check_busy():
    if any(run['status'] in ('running', 'queued') for run in list_runs()):
        raise HTTPException(status_code=409, detail='An agent is already running. Let it finish first.')


@app.get('/api/health')
def health():
    return {'configured': bool(API_KEY), 'model': MODEL, 'delivery': 'simulated'}


@app.get('/api/runs')
def runs():
    return list_runs()


@app.post('/api/runs', status_code=202)
def create_run(request: GoalInput):
    if not API_KEY:
        raise HTTPException(status_code=503, detail='Add GOOGLE_API_KEY to .env and restart the server.')
    with lock:
        check_busy()
        run = new_run(request.goal, request.mode)
        executor.submit(run_newsletter_agent, request.goal, request.mode, run['id'])
    return run


@app.get('/api/runs/{run_id}')
def run_detail(run_id: UUID):
    return find_run(run_id)


@app.post('/api/runs/{run_id}/decision', status_code=202)
def decide(run_id: UUID, request: DecisionInput):
    with lock:
        run = find_run(run_id)
        if run['status'] != 'awaiting_approval':
            raise HTTPException(status_code=409, detail='This draft is not waiting for approval.')
        if request.action == 'revise' and not request.feedback.strip():
            raise HTTPException(status_code=422, detail='Describe the changes you want before requesting a revision.')
        check_busy()
        updated = update_run(str(run_id), status='queued', step='Applying your decision')
        executor.submit(resume_newsletter_agent, str(run_id), request.model_dump())
        return updated


@app.get('/api/runs/{run_id}/files/{filename}')
def download(run_id: UUID, filename: str):
    run = find_run(run_id)
    if run['status'] != 'completed' or filename not in run['files']:
        raise HTTPException(status_code=404, detail='This file is not available yet.')
    return FileResponse(run_folder(str(run_id)) / filename, filename=filename)


frontend = ROOT / 'frontend' / 'dist'
if frontend.exists():
    app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')
