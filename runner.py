import os
import json
import datetime
from matchup import Matchup
from emailer import send_email
from mlb_data_client import MlbDbClient
from odds_interface import get_todays_odds
from model_interface import load_model, predict_with_model


SETTINGS = {
    'history': './history',
    'result_file': '2017-season.json',
    'model_fields': './data/v3/fields.json',
    'model_file': './data/v3/gradient-recent.pkl',
    'data_url': 'http://mlb-db.azurewebsites.net',
    'date_format': '%Y-%m-%d',
    'email_to': ['nolan_ramsden@outlook.com'],
    'email_from': 'nolanramsden7@gmail.com',
    'email_cc': ['rammer2@shaw.ca'],
    'email_password': 'XXXXXXXXXXXXXXXXx',
    'action_cushion': 3.1,
    'action_confidence': 41,
    'email_template': './email_template.html',
}


def _create_storage_dir():
    if not os.path.exists(SETTINGS['history']):
        os.makedirs(SETTINGS['history'])


def _create_file_path(date):
    filename = '{}.json'.format(date.strftime(SETTINGS['date_format']))
    return os.path.join(SETTINGS['history'], filename)


def _save_matchups(date, matchups):
    file_path = _create_file_path(date)
    with open(file_path, 'w') as f:
        json_str = '[{}]'.format(','.join([m.to_json() for m in matchups]))
        f.write(json_str)


def _get_data_matchups():
    today = datetime.date.today()
    data_client = MlbDbClient(SETTINGS['data_url'], SETTINGS['model_fields'])
    data_client.crawl_to(today)
    return data_client.get_matchups(today)


def _combine_matchup_sets(data_matchups, odds_matchups, odds=True):
    for data_matchup in data_matchups:
        match_found = False
        for odds_matchup in odds_matchups:
            if Matchup.same_game(data_matchup, odds_matchup):
                data_matchup.merge(odds_matchup)
                match_found = True
        if match_found is False:
            if odds:
                data_matchup.no_odds()
            else:
                data_matchup.no_result()
    return data_matchups


def _add_predictions_to_matchups(matchups):
    model = load_model(SETTINGS['model_file'])
    for matchup in matchups:
        if matchup.data_row is not None:
            matchup.add_prediction(predict_with_model(model, matchup.data_row))
    return matchups


def _add_results_to_matchups(matchups):
    if len(matchups) <= 0:
        return matchups

    client = MlbDbClient(SETTINGS['data_url'])
    matchup_results = client.get_game_results(matchups[0].date)
    return _combine_matchup_sets(matchups, matchup_results, odds=False)


def _process_matchups(matchups):
    for matchup in matchups:
        matchup.all_data(SETTINGS['action_cushion'], SETTINGS['action_confidence'])
    return matchups


def _get_previous_matchups():
    today = datetime.date.today()
    for i in range(1, 10):
        filename = _create_file_path(today + datetime.timedelta(days=-i))
        if os.path.isfile(filename):
            print 'Found recent data: {}'.format(filename)
            with open(filename, 'r') as f:
                return [Matchup.from_json(jobj) for jobj in json.load(f)]
    print 'Found no recent data'
    return []


def _overwrite_previous_results(matchups):
    if len(matchups) > 0:
        _save_matchups(matchups[0].date, matchups)


def _include_in_results(resulted_matchups):
    running_results = {}
    try:
        with open(os.path.join(SETTINGS['history'], SETTINGS['result_file']), 'r') as r:
            running_results = json.load(r)
    except Exception:
        pass

    if resulted_matchups:
        results = {
            'correct': 0,
            'wrong': 0,
            'passed': 0,
            'bet': 0,
            'gain': 0,
            'loss': 0,
            'net': 0,
        }
        for matchup in resulted_matchups:
            match_results = matchup.get_result()
            for key in results:
                results[key] += match_results[key]

        results['net'] = results['gain'] - results['loss']
        date = resulted_matchups[0].date
        running_results[date.strftime(SETTINGS['date_format'])] = results
        with open(os.path.join(SETTINGS['history'], SETTINGS['result_file']), 'w') as r:
            json.dump(running_results, r, indent=2)

    return running_results


def run():
    print 'Running'
    _create_storage_dir()

    # gather data, odds and predictions
    print 'Gathering todays matchup data and odds'
    data_matchups = _get_data_matchups()
    odds_matchups = get_todays_odds()
    merged_matchups = _combine_matchup_sets(data_matchups, odds_matchups)
    predicted_matchups = _add_predictions_to_matchups(merged_matchups)
    ready_matchups = _process_matchups(predicted_matchups)
    print 'Saving todays matchups to json file'
    _save_matchups(datetime.date.today(), ready_matchups)

    # how did we do yesterday, add to results
    print 'Finding previous matchup data'
    previous_matchups = _get_previous_matchups()
    print 'Supplementing matchups with results'
    matchups_with_results = _add_results_to_matchups(previous_matchups)
    running_results = _include_in_results(matchups_with_results)
    print 'Overwriting matchups in previous json file'
    _overwrite_previous_results(matchups_with_results)

    # send an email to peeps who wanna know    
    print 'Sending result email'
    send_email(ready_matchups, matchups_with_results, running_results, SETTINGS)
