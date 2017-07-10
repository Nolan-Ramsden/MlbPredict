import json
from matchup import Matchup
from emailer import send_email

with open('history/2017-05-02.json', 'r') as f:
    games = [Matchup.from_json(g) for g in json.load(f)]

with open('history/2017-season.json', 'r') as f:
    totals = json.load(f)

send_email(games, games, totals, {
    'email_template': './email_template.html',
    'email_to': 'nolan_ramsden@outlook.com',
    'email_from': 'nolanramsden7@gmail.com',
    'email_from': 'nolanramsden7@gmail.com',
    'email_password': 'XXXXXXXXXXXXXXX',
    'email_cc': ['nolan_ramsden@hotmail.com', 'rammer2@shaw.ca'],
})