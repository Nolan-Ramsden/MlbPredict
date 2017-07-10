import json
import time
import datetime
import requests
from matchup import Matchup


class MlbDbClient:


    def __init__(self, base_url, model_fields_file=None):
        self.base_url = base_url
        if model_fields_file:
            with open(model_fields_file, 'r') as f:
                self.fields = json.load(f)['csv']['fields']
        else:
            self.fields = None


    def get_game_results(self, date):
        result = requests.get(self.base_url + '/api/v1/winner?{}'.format(
            'date={}-{}-{}'.format(date.year, date.month, date.day),
        ))
        if result.status_code > 250:
            print 'Waiting another 5 minutes for scrape to complete'
            print_wait(5)
            result = requests.get(self.base_url + '/api/v1/winner?{}'.format(
                'date={}-{}-{}'.format(date.year, date.month, date.day),
            ))
        games = []
        for game in result.json():
            if game['GameStatus'] == 'COMPLETE':
                m = Matchup(home_team={
                    'code': '',
                    'name': game['HomeName'].lower()
                },away_team= {
                    'code': '',
                    'name': game['AwayName'].lower()
                },date = date)
                m.result = {
                    'home_score': game['HomeScore'],
                    'away_score': game['AwayScore'],
                    'winner': game['Winner'].lower(),
                }
                games.append(m)
        return games


    def get_matchups(self, date):
        print 'Fetching scoreboard for {0}'.format(date)
        request_body = {
            'StartDate': '{}-{}-{}'.format(date.year, date.month, date.day),
            'EndDate': '{}-{}-{}'.format(date.year, date.month, date.day),
            'FilePath': 'NotNeeded',
            'RequireTarget': False,
        }
        if self.fields is not None:
            request_body['Features'] = self.fields

        result = requests.post(self.base_url + '/api/v1/csv/single', json=request_body)
        if result.status_code != 200:
            print 'Request timed out, giving time to complete scrape before retry'
            print_wait(5)
            result = requests.post(self.base_url + '/api/v1/csv/single', json=request_body)

        res = result.json()
        print res
        return [Matchup.create_from_data_row(
            home_team={
              'code': g['Home']['Code'].upper(),
              'name': g['Home']['FullName'].lower(),
              'full': g['Home']['FullName'],
              'city': g['Home']['City']
            },
            away_team={
              'code': g['Away']['Code'].upper(),
              'name': g['Away']['FullName'].lower(),
              'full': g['Away']['FullName'],
              'city': g['Away']['City']
            },
            data_row=g['DataRow'],
            summary=g['Summary'],
            date=datetime.datetime.strptime(g['Date'].split(' ')[0], '%m/%d/%Y')
        ) for g in res]


    def crawl_to(self, date):
        prev_crawl = 3
        print 'Crawling scoreboard to {0} ({1} days prior)'.format(date, prev_crawl)
        start = date + datetime.timedelta(days=-prev_crawl)
        result = requests.get(self.base_url + '/api/v1/snapshots/crawl?{}&{}'.format(
            'startDate={}-{}-{}'.format(start.year, start.month, start.day),
            'endDate={}-{}-{}'.format(date.year, date.month, date.day)
        ))
        if result.status_code > 250:
            print 'Waiting another 10 minutes for scrape to complete'
            print_wait(10)


def print_wait(num_minutes):
    for i in range(num_minutes):
        print 'Waiting another {} seconds'.format((num_minutes - i) * 60)
        time.sleep(60)