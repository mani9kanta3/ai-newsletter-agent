import json
import threading
from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.config import OUTPUT

lock = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def run_folder(run_id):
    if str(UUID(run_id)) != run_id:
        raise ValueError('Invalid run ID')
    return OUTPUT / run_id


def get_run(run_id):
    with lock:
        path = run_folder(run_id) / 'run.json'
        if not path.exists():
            raise FileNotFoundError('Newsletter not found')
        return json.loads(path.read_text(encoding='utf-8'))


def save_run(run):
    with lock:
        folder = run_folder(run['id'])
        folder.mkdir(exist_ok=True)
        temporary = folder / 'run.tmp'
        temporary.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(folder / 'run.json')


def new_run(goal, mode):
    run = {
        'id': str(uuid4()),
        'goal': goal,
        'mode': mode,
        'status': 'queued',
        'created_at': now(),
        'updated_at': now(),
        'step': 'Waiting to start',
        'events': [],
        'sources': [],
        'newsletter': None,
        'reviews': [],
        'files': [],
        'error': ''
    }
    save_run(run)
    return run


def update_run(run_id, **changes):
    with lock:
        run = get_run(run_id)
        run.update(changes)
        run['updated_at'] = now()
        save_run(run)
        return run


def add_event(run_id, step, message, tool=''):
    with lock:
        run = get_run(run_id)
        run['events'].append({'step': step, 'message': message, 'tool': tool, 'time': now()})
        run['step'] = step
        run['updated_at'] = now()
        save_run(run)


def list_runs():
    runs = []
    with lock:
        for path in OUTPUT.glob('*/run.json'):
            run = json.loads(path.read_text(encoding='utf-8'))
            runs.append({key: run[key] for key in ('id', 'goal', 'mode', 'status', 'created_at', 'step')})
    return sorted(runs, key=lambda run: run['created_at'], reverse=True)

