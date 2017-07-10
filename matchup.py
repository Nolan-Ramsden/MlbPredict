from __future__ import division
import json
import datetime
import numpy as np


class Matchup:

    def __init__(self, home_team, away_team, date):
        self.home_team = home_team
        self.away_team = away_team
        self.summary = None
        self.home_odds = None
        self.away_odds = None
        self.prediction = None
        self.data_row = None
        self.action = None
        self.result = None
        self.date = date
        self.errors = []


    @staticmethod
    def create_from_data_row(home_team, away_team, data_row, summary, date):
        matchup = Matchup(home_team, away_team, date)
        matchup.summary = summary
        if data_row is not None:
            matchup.data_row = np.array([data_row.split(',')])
        else:
            matchup.data_row = None
            matchup.errors.append('No data row returned for game')
        return matchup


    @staticmethod
    def create_from_odds(home_team, away_team, home_odds, away_odds, date):
        matchup = Matchup(home_team, away_team, date)
        matchup.home_odds = home_odds
        matchup.away_odds = away_odds
        return matchup


    @staticmethod
    def same_game(matchup1, matchup2):
        same_date = matchup1.date == matchup2.date
        home_1 = str(matchup1.home_team['name'])
        home_2 = str(matchup2.home_team['name'])
        away_1 = str(matchup1.away_team['name'])
        away_2 = str(matchup2.away_team['name'])
        home_same = (matchup1.home_team['code'] == matchup2.home_team['code']
                     or home_1 in home_2 or home_2 in home_1)
        away_same = (matchup1.away_team['code'] == matchup2.away_team['code']
                     or away_1 in away_2 or away_2 in away_1)
        return same_date and (home_same or away_same)


    def merge(self, matchup2):
        if self.summary is None:
            self.summary = matchup2.summary
        if self.action is None:
            self.action = matchup2.action
        if self.prediction is None:
            self.prediction = matchup2.prediction
        if self.data_row is None:
            self.data_row = matchup2.data_row
        if self.away_odds is None:
            self.away_odds = matchup2.away_odds
        if self.home_odds is None:
            self.home_odds = matchup2.home_odds
        if self.result is None:
            self.result = matchup2.result
        elif matchup2.result is not None:
            for key in matchup2.result:
                self.result[key] = matchup2.result[key]
        self.errors += matchup2.errors


    def no_odds(self):
        self.errors.append('No odds found for this game')


    def no_result(self):
        self.errors.append('No game result for this game')


    def get_result(self):
        results = {
            'correct': 0,
            'loss': 0,
            'wrong': 0,
            'passed': 0,
            'bet': 0,
            'gain': 0,
            'net': 0,
            'winner': None,
            'home_score': 0,
            'away_score': 0
        }
        if self.action is None:
            pass
        elif self.action['bet'] == 'pass':
            results['pass'] = 1
        elif self.result is not None and self.home_odds is not None and self.result.get('winner') is not None:
            results['bet'] = 1
            BET_AMOUNT = 2
            results['loss'] = BET_AMOUNT
            if self.result['winner'] == self.action['bet']:
                results['correct'] = 1
                if self.result['winner'] == 'home':
                    results['gain'] = _calculate_profit(self.home_odds['money_line']) * BET_AMOUNT
                elif self.result['winner'] == 'away':
                    results['gain'] = _calculate_profit(self.away_odds['money_line']) * BET_AMOUNT
            else:
                results['wrong'] = 1
            results['net'] = results['gain'] - results['loss']
        if self.result is None:
            self.result = {}
        for key, val in results.items():
            if key in self.result:
                if self.result[key] == 0 or self.result[key] is None:
                    self.result[key] = val
            else:
                self.result[key] = val

        return results


    def add_prediction(self, prediction):
        self.prediction = {
            'home_wins': prediction[0][1],
            'away_wins': prediction[0][0],
        }


    def all_data(self, action_cushion=1, min_confidence=40):
        MODE = 'CUSHION'
        if self.home_odds is None or self.away_odds is None or self.prediction is None:
            self.action = {
                'bet': 'pass',
                'cushion': None,
                'description': 'Not enough information to take action'
            }
            return

        if self.prediction['home_wins'] < 0.45:
            self.prediction['home_wins'] -= 0.015
            self.prediction['away_wins'] += 0.015
        elif self.prediction['home_wins'] < 0.41:
            self.prediction['home_wins'] -= 0.025
            self.prediction['away_wins'] += 0.025

        if self.prediction['away_wins'] < 0.45:
            self.prediction['away_wins'] -= 0.015
            self.prediction['home_wins'] += 0.015
        elif self.prediction['away_wins'] < 0.41:
            self.prediction['away_wins'] -= 0.025
            self.prediction['home_wins'] += 0.025


        home_cushion = self.prediction['home_wins'] - self.home_odds['minimum_confidence']
        home_cushion = int(home_cushion * 1000) / 10
        away_cushion = self.prediction['away_wins'] - self.away_odds['minimum_confidence']
        away_cushion = int(away_cushion * 1000) / 10

        if MODE == 'WINNER':
            if self.prediction['home_wins'] >= .5:
                self.action = {
                    'bet': 'home',
                    'cushion': home_cushion,
                    'description': 'Bet {} at {} ({}% cushion)'.format(
                        self.home_team['full'], self.home_odds['money_line'], home_cushion
                    )
                }
            elif self.prediction['away_wins'] >= .5:
                self.action = {
                    'bet': 'home',
                    'cushion': home_cushion,
                    'description': 'Bet {} at {} ({}% cushion)'.format(
                        self.home_team['full'], self.home_odds['money_line'], home_cushion
                    )
                }
            
            return


        if home_cushion > action_cushion and away_cushion > action_cushion:
            self.errors.append('Both games return bettable results, this is weird')
            self.action = {
                'bet': 'pass',
                'cushion': max([home_cushion, away_cushion]),
                'description': 'Both teams meet the minimum bet cushion'
            }
        elif home_cushion > action_cushion:
            if self.prediction['home_wins'] * 100 > min_confidence:
                self.action = {
                    'bet': 'home',
                    'cushion': home_cushion,
                    'description': 'Bet {} at {} ({}% cushion)'.format(
                        self.home_team['full'], self.home_odds['money_line'], home_cushion
                    )
                }
            else:
                self.action = {
                    'bet': 'pass',
                    'cushion': None,
                    'description': 'Positive value team must be at least {}% win confident'.format(min_confidence)
                }
        elif away_cushion > action_cushion:
            if self.prediction['away_wins'] * 100 > min_confidence:            
                self.action = {
                    'bet': 'away',
                    'cushion': away_cushion,
                    'description': 'Bet {} at {} ({}% cushion)'.format(
                        self.away_team['full'], self.away_odds['money_line'], away_cushion
                    )
                }
            else:
                self.action = {
                    'bet': 'pass',
                    'cushion': None,
                    'description': 'Positive value team must be at least {}% win confident'.format(min_confidence)
                }
        else:
            self.action = {
                'bet': 'pass',
                'cushion': max([home_cushion, away_cushion]),
                'description': 'Pass, neither team is profitable'
            }


    def to_json(self):
        return json.dumps({
            'summary': self.summary,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'home_odds': self.home_odds,
            'away_odds': self.away_odds,
            'date': self.date.strftime('%Y-%m-%d'),
            'prediction': self.prediction,
            'action': self.action,
            'errors': self.errors,
            'result': self.result,
        }, indent=2)


    @staticmethod
    def from_json(json_obj):
        m = Matchup(
            home_team=json_obj['home_team'],
            away_team=json_obj['away_team'],
            date=datetime.datetime.strptime(json_obj['date'], '%Y-%m-%d').date()
        )
        m.summary = json_obj['summary']
        m.action = json_obj['action']
        m.home_odds = json_obj['home_odds']
        m.away_odds = json_obj['away_odds']
        m.prediction = json_obj['prediction']
        m.result = json_obj['result']
        m.errors = [e for e in json_obj['errors'] if e != 'No game result for this game']
        return m


def _calculate_profit(money_line):
    if money_line > 0:
        return (money_line) / 100 + 1
    else:
        return (1 / (-money_line)) * 100 + 1
