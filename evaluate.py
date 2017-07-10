import json
import decimal
import datetime
from matchup import Matchup, _calculate_profit

BET_AMOUNT = 2
DAYS_OFFSET = 0
DAYS_RECENT = 17
FILE_TEMPLATE = 'history/{}.json'


def load_matchups(file):
    with open(file, 'r') as f:
        return [Matchup.from_json(m) for m in json.load(f)]


def load_historical():
    today = datetime.date.today() + datetime.timedelta(days=-DAYS_OFFSET)
    back_step = datetime.timedelta(days=-1)
    matchups = []
    for i in range(1, DAYS_RECENT):
        hist = today + (i * back_step)
        file = FILE_TEMPLATE.format(hist.strftime('%Y-%m-%d'))
        matchups.extend(load_matchups(file))

    return matchups

def eval_at_cushion(matchups, cushion):
    cushion *= 0.01
    result = {
        'right': 0,
        'wrong': 0,
        'passed': 0,
        'won': 0,
        'lost': 0,
    }
    for matchup in matchups:
        if matchup.prediction is None or matchup.home_odds is None:
            result['passed'] += 1
        
        elif matchup.prediction['home_wins'] - matchup.home_odds['minimum_confidence'] > cushion and matchup.prediction['home_wins'] > .41:
            if matchup.result['winner'] == 'home':
                result['right'] += 1
                result['won'] += BET_AMOUNT * _calculate_profit(matchup.home_odds['money_line'])
            else:
                result['lost'] += BET_AMOUNT
                result['wrong'] += 1

        elif matchup.prediction['away_wins'] - matchup.away_odds['minimum_confidence'] > cushion and matchup.prediction['away_wins'] > .41:
            if matchup.result['winner'] == 'away':
                result['right'] += 1
                result['won'] += BET_AMOUNT * _calculate_profit(matchup.away_odds['money_line'])
            else:
                result['lost'] += BET_AMOUNT
                result['wrong'] += 1

        else:
            result['passed'] += 1

    return result

def eval_at_conf(matchups, conf):
    result = {
        'right': 0,
        'wrong': 0,
        'passed': 0,
        'won': 0,
        'lost': 0,
    }
    for matchup in matchups:
        if matchup.prediction is None or matchup.home_odds is None:
            result['passed'] += 1

        elif matchup.prediction['home_wins'] > conf:
            if matchup.result['winner'] == 'home':
                result['right'] += 1
                result['won'] += BET_AMOUNT * _calculate_profit(matchup.home_odds['money_line'])
            else:
                result['lost'] += BET_AMOUNT
                result['wrong'] += 1

        elif matchup.prediction['away_wins'] > conf:
            if matchup.result['winner'] == 'away':
                result['right'] += 1
                result['won'] += BET_AMOUNT * _calculate_profit(matchup.away_odds['money_line'])
            else:
                result['lost'] += BET_AMOUNT
                result['wrong'] += 1

        else:
            result['passed'] += 1

    return result

if __name__ == '__main__':
    matchups = load_historical()
    for i in [2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5]:
        result = eval_at_cushion(matchups, i)
        num_games = (result['right'] + result['wrong'])
        print 'CUSHION   : {}  CORRECT: %{} GAMES: {} PROFIT: {}'.format(
            i, int(round(decimal.Decimal(result['right']) / num_games, 2) * 100), num_games, result['won'] - result['lost']
        )
    for conf in [.50, .51, .52, .53, .54, .55, .56]:
        result = eval_at_conf(matchups, conf)
        num_games = (result['right'] + result['wrong'])
        print 'CONFIDENCE : {}  CORRECT: %{} GAMES: {} PROFIT: {}'.format(
            int(conf * 100), int(round(decimal.Decimal(result['right']) / (result['right'] + result['wrong']), 2) * 100), num_games, result['won'] - result['lost']
        )
    