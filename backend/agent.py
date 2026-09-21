import json
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.ai import ask_gemini
from backend.config import OUTPUT
from backend.schemas import DecisionInput, GoalInput, Newsletter, Plan, Review, Selection
from backend.storage import add_event, get_run, new_run, now, run_folder, update_run
from backend.tools import read_article, render_markdown, render_newsletter, search_news, validate_sources


class AgentState(TypedDict):
    run_id: str
    goal: str
    mode: str
    plan: dict
    sources: list[dict]
    newsletter: dict
    review: dict
    revisions: int
    feedback: str
    decision: str


def plan_step(state):
    run_id = state['run_id']
    add_event(run_id, 'Planning', 'Understanding your goal and preparing search queries.', 'Gemini planner')
    plan = ask_gemini(
        'Plan a weekly news newsletter. Create 3 broad news search queries, each only 2-4 words. '
        'Do not put dates, time ranges, past week, breakthroughs, or updates in queries. '
        'For AI agent news, good queries are: AI agents, agentic AI, autonomous AI agents. '
        'The topic must be a plain 2-4 word search term. Search already filters to the past 7 days. '
        'Describe the audience and a concise research approach. '
        'Do not promise scheduled delivery or real email sending.',
        {'goal': state['goal'], 'today': now()[:10]}, Plan
    )
    update_run(run_id, plan=plan)
    add_event(run_id, 'Planning', plan['approach'])
    return {'plan': plan}


def research_step(state):
    run_id = state['run_id']
    queries = state['plan']['queries']
    add_event(run_id, 'Researching', 'Searching: ' + ' · '.join(queries), 'News search')
    sources, warnings = search_news(queries)
    for warning in warnings:
        add_event(run_id, 'Researching', warning)
    if len(sources) < 5:
        add_event(run_id, 'Researching', 'Not enough recent articles. Trying a broader topic search.', 'News search')
        sources, warnings = search_news([state['plan']['topic'], state['goal'][:200]])
        for warning in warnings:
            add_event(run_id, 'Researching', warning)
    if len(sources) < 5:
        raise RuntimeError('Fewer than 5 dated articles were found in the past 7 days. Try a broader topic or try again later.')

    add_event(run_id, 'Researching', f'Found {len(sources)} recent articles. Selecting the strongest stories.', 'Gemini source selector')
    selection = ask_gemini(
        'Choose 7 distinct articles relevant to the newsletter goal, or 5-6 if fewer are suitable. Use only provided source IDs. '
        'Prefer credible publishers and diverse developments. Avoid multiple articles about the same event. '
        'Return a short selection reason.',
        {'goal': state['goal'], 'articles': sources}, Selection
    )
    ids = selection['source_ids']
    available = {source['id'] for source in sources}
    if len(set(ids)) != len(ids) or not set(ids).issubset(available):
        raise RuntimeError('The AI selected invalid or repeated sources. Please run the agent again.')
    selected = [next(source for source in sources if source['id'] == source_id) for source_id in ids]
    add_event(run_id, 'Researching', selection['reason'])
    readable = []
    for source in selected:
        add_event(run_id, 'Reading sources', source['title'], 'Article reader')
        source['content'] = read_article(source['url'])
        if len(source['content']) >= 300:
            source['evidence'] = 'Article text'
        else:
            source['content'] = ''
        if not source['content'] and len(source['excerpt']) < 250:
            add_event(run_id, 'Reading sources', 'Skipped a source with too little readable evidence: ' + source['title'])
            continue
        readable.append(source)
    selected = readable
    if len(selected) < 5:
        raise RuntimeError('Fewer than 5 selected sources had enough readable evidence. Please try again with a broader goal.')
    update_run(run_id, sources=selected)
    full_count = sum(source['evidence'] == 'Article text' for source in selected)
    add_event(run_id, 'Reading sources', f'Read {full_count} articles; {len(selected) - full_count} use labeled search excerpts.')
    return {'sources': selected}


def write_step(state):
    run_id = state['run_id']
    revising = bool(state.get('newsletter'))
    step = 'Revising' if revising else 'Writing'
    update_run(run_id, html='')
    add_event(run_id, step, 'Improving the draft using feedback.' if revising else 'Summarizing sources and writing your newsletter.', 'Gemini summarizer')
    newsletter = ask_gemini(
        'Write a concise weekly newsletter, a useful subject, introduction and closing. '
        'Write EXACTLY ONE story for EACH provided source, using its integer source_id exactly once. '
        'Never split a source into multiple stories. Focus each story on the main news in its source title. '
        'Use ONLY facts supported by the provided content or excerpt. For excerpt-only sources, stay brief '
        'and attribute claims to the publisher. Never fill missing details from memory. '
        'Keep each summary about 40-70 words, and explain why it matters in one sentence starting with May, Could, or This may. '
        'Summaries should only report the event, with attribution. Put all implications in why_it_matters. '
        'Never use hype such as revolutionary, unprecedented, critical, drastically, or transforming. '
        'The introduction should briefly list topics. The closing should simply thank readers, without broad factual claims. '
        'Different events in the same industry are distinct stories. Avoid repeated coverage of the same event. '
        'Apply reviewer issues and human feedback while preserving evidence. No HTML or Markdown in text fields.',
        {
            'goal': state['goal'],
            'plan': state['plan'],
            'sources': state['sources'],
            'previous_draft': state.get('newsletter'),
            'review': state.get('review'),
            'human_feedback': state.get('feedback', '')
        }, Newsletter
    )
    update_run(run_id, newsletter=newsletter)
    return {'newsletter': newsletter, 'revisions': state.get('revisions', 0) + int(revising)}


def review_step(state):
    run_id = state['run_id']
    add_event(run_id, 'Reviewing', 'Checking relevance, evidence, repetition, and readability.', 'Gemini critic')
    review = ask_gemini(
        'Act as a careful newsletter editor. Evaluate the draft against the sources and goal. '
        'Check factual support for names, dates, numbers and claims; relevance; '
        'duplicate events; correct source IDs; and readable writing. 5, 6, and 7 stories are ALL acceptable counts. '
        'Different events in the same industry are NOT duplicates. A draft mentioning an event found in its source is expected, '
        'not duplication. Only flag duplication when TWO draft stories cover the SAME specific event. '
        'Search excerpts are acceptable evidence '
        'only for facts explicitly present in them. Interpretations must be clearly phrased as possibilities. '
        'Do not demand full article access. Return passed=true only when no material issue remains. '
        'If revision is needed, list specific actionable issues, identifying the draft claim and contradictory or missing evidence. '
        'Do not demand extra stories, invented details, exact wording, or optional style changes. '
        'Use an empty issues list when there are no material errors. Give a brief editorial verdict, not private reasoning.',
        {'goal': state['goal'], 'sources': state['sources'], 'draft': state['newsletter']}, Review
    )
    try:
        validate_sources(state['newsletter'], state['sources'])
    except ValueError as error:
        review['issues'].append(str(error))
    if review['issues']:
        review['passed'] = False
    run = get_run(run_id)
    update_run(run_id, reviews=run['reviews'] + [review])
    add_event(run_id, 'Reviewing', review['summary'])
    return {'review': review}


def after_review(state):
    if state['review']['passed']:
        return 'prepare'
    if state['revisions'] < 2:
        return 'write'
    return 'failed_review'


def failed_review_step(state):
    raise RuntimeError('The draft did not pass review after two revisions. No delivery was saved. Review the issues and try a clearer goal.')


def prepare_step(state):
    run_id = state['run_id']
    add_event(run_id, 'Formatting', 'Building the newsletter preview with source links.', 'HTML generator')
    html = render_newsletter(state['newsletter'], state['sources'], now())
    update_run(run_id, html=html)
    if state['mode'] == 'human':
        add_event(run_id, 'Awaiting approval', 'Review the newsletter, then approve, request changes, or cancel.')
    return {}


def approval_step(state):
    if state['mode'] == 'autonomous':
        return {'decision': 'approve'}
    decision = interrupt({'message': 'Review the newsletter before simulated delivery.', 'run_id': state['run_id']})
    decision = DecisionInput.model_validate(decision)
    if decision.action == 'revise' and not decision.feedback.strip():
        raise ValueError('Please describe the changes you want.')
    add_event(state['run_id'], 'Human review', decision.feedback.strip() or decision.action.capitalize())
    return {'decision': decision.action, 'feedback': decision.feedback.strip(), 'revisions': 0}


def after_approval(state):
    if state['decision'] == 'revise':
        return 'write'
    if state['decision'] == 'cancel':
        return 'cancel'
    return 'output'


def output_step(state):
    run_id = state['run_id']
    add_event(run_id, 'Saving', 'Saving HTML, Markdown, and a simulated email receipt.', 'File delivery')
    folder = run_folder(run_id)
    html = render_newsletter(state['newsletter'], state['sources'], now())
    markdown = render_markdown(state['newsletter'], state['sources'])
    receipt = {
        'subject': state['newsletter']['subject'],
        'recipient_group': 'Newsletter subscribers (simulation)',
        'sent': False,
        'status': 'Simulated delivery saved locally',
        'created_at': now(),
        'html_file': 'newsletter.html',
        'markdown_file': 'newsletter.md'
    }
    (folder / 'newsletter.html').write_text(html, encoding='utf-8')
    (folder / 'newsletter.md').write_text(markdown, encoding='utf-8')
    (folder / 'email.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    update_run(run_id, html=html, files=['newsletter.html', 'newsletter.md', 'email.json'])
    add_event(run_id, 'Completed', 'Newsletter saved. Delivery simulated; no email was sent.')
    update_run(run_id, status='completed')
    return {}


def cancel_step(state):
    add_event(state['run_id'], 'Cancelled', 'You cancelled this draft. No delivery files were saved.')
    update_run(state['run_id'], status='cancelled')
    return {}


def build_graph(checkpointer):
    graph = StateGraph(AgentState)
    graph.add_node('plan', plan_step)
    graph.add_node('research', research_step)
    graph.add_node('write', write_step)
    graph.add_node('review', review_step)
    graph.add_node('failed_review', failed_review_step)
    graph.add_node('prepare', prepare_step)
    graph.add_node('approval', approval_step)
    graph.add_node('output', output_step)
    graph.add_node('cancel', cancel_step)
    graph.add_edge(START, 'plan')
    graph.add_edge('plan', 'research')
    graph.add_edge('research', 'write')
    graph.add_edge('write', 'review')
    graph.add_conditional_edges('review', after_review, ['prepare', 'write', 'failed_review'])
    graph.add_edge('prepare', 'approval')
    graph.add_conditional_edges('approval', after_approval, ['write', 'cancel', 'output'])
    graph.add_edge('output', END)
    graph.add_edge('cancel', END)
    graph.add_edge('failed_review', END)
    return graph.compile(checkpointer=checkpointer)


def execute(run_id, graph_input):
    update_run(run_id, status='running', error='')
    try:
        with SqliteSaver.from_conn_string(str(OUTPUT / 'checkpoints.sqlite')) as checkpointer:
            graph = build_graph(checkpointer)
            result = graph.invoke(graph_input, {'configurable': {'thread_id': run_id}, 'recursion_limit': 40})
        if result.get('__interrupt__'):
            update_run(run_id, status='awaiting_approval')
    except RuntimeError as error:
        update_run(run_id, status='failed', error=str(error), step='Stopped')
        add_event(run_id, 'Stopped', str(error))
    except Exception:
        message = 'The agent could not finish this run. Please try again. Your previous completed newsletters are safe.'
        update_run(run_id, status='failed', error=message, step='Stopped')
        add_event(run_id, 'Stopped', message)
    return get_run(run_id)


def run_newsletter_agent(goal, mode='autonomous', run_id=None):
    request = GoalInput(goal=goal, mode=mode)
    if run_id is None:
        run = new_run(request.goal, request.mode)
        run_id = run['id']
    return execute(run_id, {
        'run_id': run_id, 'goal': request.goal, 'mode': request.mode,
        'revisions': 0, 'feedback': '', 'decision': ''
    })


def resume_newsletter_agent(run_id, decision):
    run = get_run(run_id)
    if run['status'] not in ('awaiting_approval', 'queued'):
        raise ValueError('This newsletter is not waiting for approval.')
    return execute(run_id, Command(resume=decision))
