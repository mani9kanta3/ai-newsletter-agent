import argparse

from backend.agent import run_newsletter_agent

parser = argparse.ArgumentParser(description='Run the newsletter agent once.')
parser.add_argument('goal', nargs='?', default='Create a weekly newsletter on latest AI agent news and send it to our subscribers.')
args = parser.parse_args()

if __name__ == '__main__':
    result = run_newsletter_agent(args.goal)
    print('Status:', result['status'])
    if result['newsletter']:
        print('Subject:', result['newsletter']['subject'])
    if result['error']:
        print('Error:', result['error'])
        raise SystemExit(1)
    print('Saved in: output/' + result['id'])
