from __future__ import division
import json
import requests
import datetime
from matchup import Matchup

def get_todays_odds():
    result = requests.get('http://io.oddsshark.com/ticker/mlb', headers={
        'Origin': 'http://www.oddsshark.com',
        'Referer': 'http://www.oddsshark.com/mlb/odds',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
    })
    games = []
    result_json = result.json()
    for matchup in result_json['matchups']:
        if matchup['type'] == 'matchup':
	    if matchup['home_odds'] and matchup['away_odds']:
                m = Matchup.create_from_odds(
                home_team={
                    'code': matchup['home_short_name'].upper(),
                    'name': matchup['home_name'].lower(),
                },
                away_team={
                    'code': matchup['away_short_name'].upper(),
                    'name': matchup['away_name'].lower(),
                },
                home_odds={
                    'money_line': int(matchup['home_odds']),
                    'minimum_confidence': _confidence(int(matchup['home_odds']))
                },
                away_odds={
                    'money_line': int(matchup['away_odds']),
                    'minimum_confidence': _confidence(int(matchup['away_odds']))
                },
                date=datetime.datetime.strptime(matchup['event_date'].split(' ')[0], "%Y-%m-%d")
                )
            if matchup['status'] == 'FINAL':
                home_score = int(matchup['home_score'])
                away_score = int(matchup['home_score'])
                m.result = {
                    'home_score': home_score,
                    'away_score': away_score,
                    'winner': 'home' if home_score > away_score else 'away'
                }
            games.append(m)
    return games


def _confidence(odds):
    if odds < 0:
        odds = -odds
        return odds / (100 + odds)
    else:
        return 100 / (100 + odds)
