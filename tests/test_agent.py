import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend import agent, storage, tools
from backend.schemas import GoalInput


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'OUTPUT', tmp_path)
    monkeypatch.setattr(agent, 'OUTPUT', tmp_path)
    return tmp_path


@pytest.fixture
def fake_tools(workspace, monkeypatch):
    sources = [{
        'id': index,
        'title': f'Agent development {index}',
        'url': f'https://example.com/news/{index}',
        'publisher': 'Example News',
        'published_at': datetime.now(timezone.utc).isoformat(),
        'excerpt': f'A new agent feature {index} was announced for developers to test in their applications. ' * 4,
        'content': '',
        'evidence': 'Search excerpt'
    } for index in range(1, 6)]
    draft = {
        'subject': 'This week in AI agents',
        'introduction': 'Five useful developments in AI agents from this week.',
        'stories': [{
            'source_id': index,
            'headline': f'Agent feature {index} announced',
            'summary': f'Example News reports a new agent feature {index} for developers to test in their applications.',
            'why_it_matters': 'Developers could use this feature to explore new applications.'
        } for index in range(1, 6)],
        'closing': 'See you next week for more agent news.'
    }
    calls = {'writes': 0, 'reviews': 0, 'fail_first': False, 'always_fail': False}

    def fake_gemini(instruction, data, schema):
        if schema.__name__ == 'Plan':
            return {'topic': 'AI agents', 'audience': 'developers', 'queries': ['AI agents', 'agentic AI'], 'approach': 'Find recent agent news.'}
        if schema.__name__ == 'Selection':
            return {'source_ids': [1, 2, 3, 4, 5], 'reason': 'Five distinct developments.'}
        if schema.__name__ == 'Newsletter':
            calls['writes'] += 1
            result = copy.deepcopy(draft)
            if data['human_feedback']:
                result['subject'] = 'A shorter weekly agent update'
            return result
        calls['reviews'] += 1
        fail = calls['always_fail'] or calls['fail_first'] and calls['reviews'] == 1
        return {'passed': not fail, 'summary': 'Needs a shorter introduction.' if fail else 'Ready to publish.', 'issues': ['Shorten introduction.'] if fail else []}

    monkeypatch.setattr(agent, 'ask_gemini', fake_gemini)
    monkeypatch.setattr(agent, 'search_news', lambda queries: (copy.deepcopy(sources), []))
    monkeypatch.setattr(agent, 'read_article', lambda url: '')
    return calls, draft, sources


def test_autonomous_revises_and_saves(workspace, fake_tools):
    calls, draft, sources = fake_tools
    calls['fail_first'] = True
    result = agent.run_newsletter_agent('Create a weekly newsletter about AI agents.')
    assert result['status'] == 'completed'
    assert calls['writes'] == 2
    assert calls['reviews'] == 2
    assert len(result['newsletter']['stories']) == 5
    folder = workspace / result['id']
    assert (folder / 'newsletter.html').exists()
    assert (folder / 'newsletter.md').exists()
    assert '"sent": false' in (folder / 'email.json').read_text()
    assert any(event['tool'] == 'Article reader' for event in result['events'])


def test_human_pause_revision_and_resume(workspace, fake_tools):
    result = agent.run_newsletter_agent('Create a weekly newsletter about AI agents.', 'human')
    folder = workspace / result['id']
    assert result['status'] == 'awaiting_approval'
    assert not (folder / 'newsletter.html').exists()
    assert result['html']
    revised = agent.resume_newsletter_agent(result['id'], {'action': 'revise', 'feedback': 'Make the subject shorter.'})
    assert revised['status'] == 'awaiting_approval'
    assert revised['newsletter']['subject'] == 'A shorter weekly agent update'
    assert not (folder / 'newsletter.html').exists()
    approved = agent.resume_newsletter_agent(result['id'], {'action': 'approve'})
    assert approved['status'] == 'completed'
    assert (folder / 'newsletter.html').exists()
    with pytest.raises(ValueError):
        agent.resume_newsletter_agent(result['id'], {'action': 'approve'})


def test_human_cancel_does_not_save_delivery(workspace, fake_tools):
    result = agent.run_newsletter_agent('Create a weekly newsletter about AI agents.', 'human')
    result = agent.resume_newsletter_agent(result['id'], {'action': 'cancel'})
    assert result['status'] == 'cancelled'
    assert not (workspace / result['id'] / 'email.json').exists()


def test_failed_review_never_saves(workspace, fake_tools):
    calls, draft, sources = fake_tools
    calls['always_fail'] = True
    result = agent.run_newsletter_agent('Create a weekly newsletter about AI agents.')
    assert result['status'] == 'failed'
    assert calls['writes'] == 3
    assert calls['reviews'] == 3
    assert not (workspace / result['id'] / 'newsletter.html').exists()


def test_short_research_stops_instead_of_inventing(workspace, fake_tools, monkeypatch):
    monkeypatch.setattr(agent, 'search_news', lambda queries: ([], ['Search unavailable']))
    result = agent.run_newsletter_agent('Create a weekly newsletter about AI agents.')
    assert result['status'] == 'failed'
    assert result['newsletter'] is None
    assert result['files'] == []


def test_news_filters_dates_and_duplicates(monkeypatch):
    now = datetime.now(timezone.utc)
    records = [
        {'title': 'Recent article', 'url': 'https://example.com/one', 'date': (now - timedelta(days=1)).isoformat()},
        {'title': 'Recent article', 'url': 'https://example.com/two', 'date': now.isoformat()},
        {'title': 'Old article', 'url': 'https://example.com/old', 'date': (now - timedelta(days=9)).isoformat()},
        {'title': 'Future article', 'url': 'https://example.com/future', 'date': (now + timedelta(days=2)).isoformat()},
        {'title': 'Unknown date', 'url': 'https://example.com/unknown', 'date': ''}
    ]

    class Search:
        def __init__(self, **kwargs):
            pass

        def news(self, *args, **kwargs):
            return records

    monkeypatch.setattr(tools, 'DDGS', Search)
    sources, warnings = tools.search_news(['AI agents', 'agentic AI'])
    assert len(sources) == 1
    assert sources[0]['title'] == 'Recent article'


def test_html_escapes_text_and_rejects_unknown_sources(fake_tools):
    calls, draft, sources = fake_tools
    draft['subject'] = '<script>alert(1)</script>'
    html = tools.render_newsletter(draft, sources, '2026-09-21')
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    draft['stories'][0]['source_id'] = 99
    with pytest.raises(ValueError):
        tools.render_newsletter(draft, sources, '2026-09-21')


def test_private_urls_are_blocked():
    assert not tools.public_url('http://127.0.0.1/secrets')
    assert not tools.public_url('http://169.254.169.254/latest')
    assert not tools.public_url('file:///etc/passwd')
    assert not tools.public_url('https://user:password@example.com')


def test_invalid_goals_are_rejected():
    with pytest.raises(ValueError):
        GoalInput(goal='          ')
    with pytest.raises(ValueError):
        GoalInput(goal='A good newsletter goal', mode='automatic')


def test_api_protects_approval_and_downloads(workspace, fake_tools, monkeypatch):
    from backend.main import app

    result = agent.run_newsletter_agent('Create a weekly newsletter about AI agents.', 'human')
    client = TestClient(app)
    run_id = result['id']
    assert client.get(f'/api/runs/{run_id}').status_code == 200
    assert client.get(f'/api/runs/{run_id}/files/newsletter.html').status_code == 404
    assert client.post(f'/api/runs/{run_id}/decision', json={'action': 'revise', 'feedback': '  '}).status_code == 422
    assert client.get('/api/runs/not-a-uuid').status_code == 422
    assert client.post('/api/runs', json={'goal': 'short'}).status_code == 422
    agent.resume_newsletter_agent(run_id, {'action': 'approve'})
    assert client.get(f'/api/runs/{run_id}/files/newsletter.html').status_code == 200
    assert client.get(f'/api/runs/{run_id}/files/run.json').status_code == 404
    assert client.post(f'/api/runs/{run_id}/decision', json={'action': 'approve'}).status_code == 409


def test_unreadable_picks_are_replaced_from_unused_results(workspace, fake_tools, monkeypatch):
    calls, draft, sources = fake_tools
    extra = copy.deepcopy(sources)
    for index, source in enumerate(extra, 6):
        source.update(id=index, title=f'Agent development {index}', url=f'https://example.com/news/{index}')
    everything = copy.deepcopy(sources) + extra
    for source in everything[:2]:
        source['excerpt'] = 'Too short.'
    monkeypatch.setattr(agent, 'search_news', lambda queries: (copy.deepcopy(everything), []))
    state = {'run_id': storage.new_run('Weekly AI agent news', 'autonomous')['id'], 'goal': 'Weekly AI agent news',
             'plan': {'queries': ['AI agents'], 'topic': 'AI agents'}}
    result = agent.research_step(state)
    assert [source['id'] for source in result['sources']] == [3, 4, 5, 6, 7]
